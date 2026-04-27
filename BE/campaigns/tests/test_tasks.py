import uuid
from unittest.mock import patch, MagicMock
import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from campaigns.tasks import enrich_leads_from_volza, enrich_contacts_from_lusha
from leads.models import Lead, Contact, LeadStage, ContactSource

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def campaign(user):
    product = Product.objects.create(name='Acetone', hsn_code='2914', cas_number='67-64-1', created_by=user)
    c = Campaign.objects.create(title='Test', country_filters=['IN'], num_transactions_yr=5, created_by=user)
    c.products.add(product)
    return c


@pytest.mark.django_db
def test_enrich_leads_creates_lead_and_contact(campaign):
    volza_result = [
        {
            "company_name": "Acme Chemicals",
            "country": "IN",
            "website": "https://acme.com",
            "contact_name": "Rajesh Kumar",
            "contact_designation": "Purchase Manager",
            "contact_email": "rajesh@acme.com",
            "num_transactions": 10,
            "purchase_history": [{"year": 2024, "qty": 500}],
            "pricing_trend": {"2024": 120.5},
        }
    ]
    with patch("campaigns.tasks.VölzaClient") as MockVolza:
        mock_instance = MagicMock()
        mock_instance.search_importers.return_value = volza_result
        MockVolza.return_value = mock_instance

        enrich_leads_from_volza(str(campaign.id))

    assert Lead.objects.filter(campaign=campaign).count() == 1
    lead = Lead.objects.get(campaign=campaign)
    assert lead.company_name == "Acme Chemicals"
    assert lead.stage == LeadStage.DISCOVERED
    assert Contact.objects.filter(lead=lead).count() == 1
    contact = Contact.objects.get(lead=lead)
    assert contact.email == "rajesh@acme.com"
    assert contact.source == ContactSource.VOLZA


@pytest.mark.django_db
def test_enrich_leads_creates_multiple_leads(campaign):
    volza_results = [
        {"company_name": f"Corp {i}", "country": "IN", "website": "",
         "contact_name": f"Person {i}", "contact_designation": "Manager",
         "contact_email": None, "num_transactions": 5,
         "purchase_history": [], "pricing_trend": {}}
        for i in range(3)
    ]
    with patch("campaigns.tasks.VölzaClient") as MockVolza, \
         patch("campaigns.tasks.async_task") as mock_async_task:
        mock_instance = MagicMock()
        mock_instance.search_importers.return_value = volza_results
        MockVolza.return_value = mock_instance

        enrich_leads_from_volza(str(campaign.id))

    assert Lead.objects.filter(campaign=campaign).count() == 3


@pytest.mark.django_db
def test_enrich_leads_skips_nonexistent_campaign():
    with patch("campaigns.tasks.VölzaClient"):
        enrich_leads_from_volza(str(uuid.uuid4()))  # fake UUID


@pytest.mark.django_db
def test_enrich_contacts_from_lusha_fills_contact(campaign):
    lead = Lead.objects.create(campaign=campaign, company_name='Ghost Corp', company_country='US')
    contact = Contact.objects.create(
        lead=lead, first_name='Jane', last_name='Doe',
        designation='CFO', source=ContactSource.VOLZA
    )
    assert contact.email is None

    with patch("campaigns.tasks.LushaClient") as MockLusha:
        mock_instance = MagicMock()
        mock_instance.find_contact.return_value = {
            "email": "jane@ghost.com",
            "phone": "+15551234567",
            "linkedin_url": "https://linkedin.com/in/jane",
            "raw": {"emails": [{"email": "jane@ghost.com"}]},
        }
        MockLusha.return_value = mock_instance

        enrich_contacts_from_lusha(str(contact.id))

    contact.refresh_from_db()
    assert contact.email == "jane@ghost.com"
    assert contact.phone == "+15551234567"
    assert contact.source == ContactSource.LUSHA
