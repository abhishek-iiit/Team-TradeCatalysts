"""
Django-Q2 background tasks for lead enrichment.

Two tasks:
  1. enrich_leads_from_volza  — fetch buyer companies from Volza for all products
     in a campaign, then create Lead + Contact records.
  2. enrich_contacts_from_lusha — enrich a single Contact's email/phone via Lusha.
"""

from campaigns.services.volza import VölzaClient
from campaigns.services.lusha import LushaClient


def async_task(func_path: str, *args, **kwargs) -> None:  # noqa: F811
    """
    Thin shim that delegates to django_q.tasks.async_task.

    Defined at module level so tests can patch ``campaigns.tasks.async_task``
    without needing to patch the django_q import path directly.
    """
    from django_q.tasks import async_task as _async_task

    _async_task(func_path, *args, **kwargs)


def enrich_leads_from_volza(campaign_id: str) -> None:
    """
    Django-Q2 task: fetch buyer companies from Volza for every product in a
    campaign, create ``Lead`` + primary ``Contact`` records, and queue a Lusha
    enrichment task for any contact that has neither email nor phone.

    Args:
        campaign_id: String representation of the Campaign UUID.
    """
    from campaigns.models import Campaign
    from leads.models import Lead, Contact, ContactSource, LeadStage

    try:
        campaign = Campaign.objects.prefetch_related("products").get(id=campaign_id)
    except Campaign.DoesNotExist:
        return

    client = VölzaClient()

    for product in campaign.products.all():
        results = client.search_importers(
            product_name=product.name,
            hsn_code=product.hsn_code,
            countries=campaign.country_filters,
            min_transactions=campaign.num_transactions_yr,
        )

        for item in results:
            company_name = item.get("company_name", "")

            # Skip duplicates within this campaign
            if Lead.objects.filter(campaign=campaign, company_name=company_name).exists():
                continue

            # purchase_history from Volza can be a list; Lead.purchase_history is
            # a JSONField(default=dict) so we accept both list and dict values.
            purchase_history = item.get("purchase_history") or {}
            pricing_trend = item.get("pricing_trend") or {}

            lead = Lead.objects.create(
                campaign=campaign,
                company_name=company_name,
                company_country=item.get("country", ""),
                company_website=item.get("website", ""),
                stage=LeadStage.DISCOVERED,
                volza_data=item,
                purchase_history=purchase_history,
                pricing_trend=pricing_trend,
            )

            # Split full name into first / last parts
            contact_name = item.get("contact_name", "") or ""
            parts = contact_name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

            contact = Contact.objects.create(
                lead=lead,
                first_name=first_name,
                last_name=last_name,
                designation=item.get("contact_designation", ""),
                email=item.get("contact_email") or None,
                source=ContactSource.VOLZA,
                is_primary=True,
            )

            # Queue Lusha enrichment when no contact info is available
            if not contact.email and not contact.phone:
                async_task("campaigns.tasks.enrich_contacts_from_lusha", str(contact.id))


def enrich_contacts_from_lusha(contact_id: str) -> None:
    """
    Django-Q2 task: enrich a single Contact with email, phone, and LinkedIn
    URL via the Lusha API.

    Args:
        contact_id: String representation of the Contact UUID / PK.
    """
    from leads.models import Contact, ContactSource

    try:
        contact = Contact.objects.select_related("lead").get(id=contact_id)
    except Contact.DoesNotExist:
        return

    client = LushaClient()
    result = client.find_contact(
        first_name=contact.first_name,
        last_name=contact.last_name,
        company_name=contact.lead.company_name,
    )

    updated = False

    if result.get("email"):
        contact.email = result["email"]
        updated = True

    if result.get("phone"):
        contact.phone = result["phone"]
        updated = True

    if result.get("linkedin_url"):
        contact.linkedin_url = result["linkedin_url"]
        updated = True

    if result.get("raw"):
        contact.lusha_raw = result["raw"]
        updated = True

    if updated:
        contact.source = ContactSource.LUSHA
        contact.save()
