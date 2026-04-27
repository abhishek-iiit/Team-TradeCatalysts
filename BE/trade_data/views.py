from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services.parser import parse_panjiva


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview(request):
    """Parse uploaded Panjiva file and return extracted lead rows (no DB write)."""
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        leads, detected_headers = parse_panjiva(file)
    except Exception as exc:
        return Response({'error': f'Parse error: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

    if not leads:
        norm_found = [h for h in detected_headers if h.strip()][:20]
        return Response(
            {
                'error': (
                    'No leads could be extracted. '
                    'Expected a BUYER column (Exim) or Consignee column (Panjiva). '
                    f'Columns detected: {norm_found}'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'count': len(leads),
        'preview': leads[:20],
        'rows': leads,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_leads(request):
    """Import parsed lead rows into a campaign (creates Lead + Contact records)."""
    from campaigns.models import Campaign
    from leads.models import Lead, Contact, LeadStage, ContactSource
    from django.db import transaction

    campaign_id = request.data.get('campaign_id')
    rows = request.data.get('rows', [])

    if not campaign_id:
        return Response({'error': 'campaign_id required'}, status=status.HTTP_400_BAD_REQUEST)
    if not rows:
        return Response({'error': 'No rows to import'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found'}, status=status.HTTP_404_NOT_FOUND)

    created = 0
    skipped = 0

    existing_names = set(
        Lead.objects.filter(campaign=campaign).values_list('company_name', flat=True)
    )

    # Emails already linked to any lead for this campaign's products
    existing_emails = set(
        Contact.objects.filter(
            email__isnull=False,
            lead__campaign__products__in=campaign.products.all(),
        ).values_list('email', flat=True)
    )

    with transaction.atomic():
        contacts_to_create = []

        for row in rows:
            company_name = (row.get('company_name') or '').strip()
            if not company_name:
                continue

            if company_name in existing_names:
                skipped += 1
                continue

            # Skip if any contact email from this row already exists for these products
            row_emails = [
                c.get('email', '').strip().lower()
                for c in (row.get('contacts') or [])
                if c.get('email', '').strip()
            ]
            if row_emails and any(e in existing_emails for e in row_emails):
                skipped += 1
                continue

            lead = Lead.objects.create(
                campaign=campaign,
                company_name=company_name,
                company_country=(row.get('company_country') or '').strip(),
                company_website=(row.get('company_website') or '').strip(),
                stage=LeadStage.DISCOVERED,
                purchase_history=row.get('purchase_history') or [],
            )
            existing_names.add(company_name)
            created += 1

            for c in (row.get('contacts') or []):
                email = c.get('email') or None
                phone = c.get('phone') or None
                if not email and not phone:
                    continue
                contacts_to_create.append(Contact(
                    lead=lead,
                    first_name=(c.get('first_name') or '').strip(),
                    last_name=(c.get('last_name') or '').strip(),
                    designation=(c.get('designation') or '').strip(),
                    email=email,
                    phone=phone,
                    source=ContactSource.MANUAL,
                    is_primary=True,
                ))
                # Track so later rows in the same batch are also deduped
                if email:
                    existing_emails.add(email.strip().lower())

        if contacts_to_create:
            Contact.objects.bulk_create(contacts_to_create, batch_size=200)

    return Response({'created': created, 'skipped': skipped})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def explore(request):
    """Search leads + Volza importers by product name/HS code."""
    from django.db.models import Q
    from leads.models import Lead
    from leads.serializers import LeadListSerializer
    from campaigns.services.volza import VölzaClient

    q = (request.GET.get('q') or '').strip()
    countries = request.GET.getlist('countries')

    leads_data = []
    volza_results = []

    if q:
        qs = (
            Lead.objects
            .select_related('campaign')
            .prefetch_related('contacts', 'campaign__products')
            .filter(
                Q(campaign__products__name__icontains=q) |
                Q(campaign__products__hsn_code__icontains=q)
            )
            .distinct()
            .order_by('-created_at')[:50]
        )
        leads_data = LeadListSerializer(qs, many=True).data

        client = VölzaClient()
        volza_results = client.search_importers(product_name=q, countries=countries)

    return Response({'leads': leads_data, 'volza': volza_results})
