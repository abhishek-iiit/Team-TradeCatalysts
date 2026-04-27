# Phase 2: Lead Discovery Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Internal team creates a campaign (product + country filters), the system queries Volza API for buyer companies, enriches missing contacts via LUSHA, and displays the discovered leads in a filterable table.

**Architecture:** Products and Campaigns as DRF ViewSets. Campaign creation triggers a Django-Q2 async task (`enrich_leads_from_volza`) that calls Volza, creates Lead + Contact records, then queues a second task (`enrich_contacts_from_lusha`) for contacts still missing email/phone. The FE polls campaign status every 5 seconds while enrichment runs. Volza and LUSHA integrations are isolated in service clients so they can be mocked in tests.

**Tech Stack:** DRF ModelViewSets · Django-Q2 async_task · django-environ · requests · React 19 · TanStack Query (polling) · Tailwind v4

> **Prerequisite:** Phase 1 must be complete — all models migrated, JWT auth working, `salescatalyst` DB exists.

---

## File Map

### Backend (BE/)
```
campaigns/
  serializers.py       ← ProductSerializer, CampaignSerializer, CampaignCreateSerializer
  views.py             ← ProductViewSet, CampaignViewSet
  urls.py              ← DRF router for products + campaigns
  tasks.py             ← enrich_leads_from_volza, enrich_contacts_from_lusha
  services/
    __init__.py
    volza.py           ← VölzaClient.search_importers()
    lusha.py           ← LushaClient.find_contact()
  tests/
    test_serializers.py
    test_views.py
    test_tasks.py

leads/
  serializers.py       ← LeadListSerializer, ContactSerializer
  views.py             ← LeadViewSet (read-only: list + detail)
  urls.py
  tests/
    test_views.py

config/
  urls.py              ← add campaigns + leads URL includes
```

### Frontend (FE/src/)
```
api/
  products.js          ← listProducts(), createProduct(), updateProduct(), deleteProduct()
  campaigns.js         ← listCampaigns(), createCampaign(), getCampaign(), getCampaignLeads(), exportMissingContacts()

pages/
  ProductsPage.jsx     ← product list + create/edit form + brochure PDF upload
  NewCampaignPage.jsx  ← product multi-select + country checklist + submit
  CampaignLeadsPage.jsx ← lead table with stage filter tabs + polling

components/
  campaigns/
    ProductMultiSelect.jsx  ← searchable multi-select dropdown
    CountryCheckbox.jsx     ← country list with search filter
  products/
    BrochureUpload.jsx      ← file input for PDF upload
  leads/
    LeadTable.jsx           ← table rows with checkbox, stage badge, contact info
    StageBadge.jsx          ← colored pill for each stage value
    EnrichmentBanner.jsx    ← shows "Enriching leads…" while Django-Q2 runs
```

---

## Task 1: Add `requests` to requirements + install

**Files:**
- Modify: `BE/requirements.txt`

- [ ] **Step 1: Add requests to requirements.txt**

Add this line to `BE/requirements.txt`:
```
requests==2.32.3
```

- [ ] **Step 2: Install it**

```bash
cd BE && source venv/bin/activate
pip install requests==2.32.3
```

Expected: `Successfully installed requests-2.32.3` (or "already satisfied")

---

## Task 2: Volza service client

**Files:**
- Create: `BE/campaigns/services/__init__.py`
- Create: `BE/campaigns/services/volza.py`

- [ ] **Step 1: Create BE/campaigns/services/__init__.py** (empty file)

- [ ] **Step 2: Write BE/campaigns/services/volza.py**

```python
import os
import requests
from typing import Optional


class VölzaClient:
    """
    Client for the Volza trade data API.
    Searches for companies that import a given product.

    Expected response shape from Volza (adapt if actual API differs):
    {
      "results": [
        {
          "company_name": "Acme Chemicals",
          "country": "IN",
          "website": "https://acme.com",
          "contact_name": "Rajesh Kumar",
          "contact_designation": "Purchase Manager",
          "contact_email": "rajesh@acme.com",
          "num_transactions": 24,
          "purchase_history": [...],
          "pricing_trend": {...}
        }
      ]
    }
    """

    BASE_URL = "https://api.volza.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VOLZA_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def search_importers(
        self,
        product_name: str,
        hsn_code: str = "",
        countries: list = None,
        min_transactions: int = 0,
    ) -> list[dict]:
        """
        Search Volza for companies that import the given product.
        Returns a list of importer dicts. Returns [] on any error.
        """
        params = {
            "product_name": product_name,
            "hsn_code": hsn_code,
            "min_transactions": min_transactions,
        }
        if countries:
            params["countries"] = ",".join(countries)

        try:
            response = self.session.get(
                f"{self.BASE_URL}/importers/search",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except requests.RequestException as exc:
            # Log and return empty — caller handles empty gracefully
            print(f"[VölzaClient] API error: {exc}")
            return []
```

---

## Task 3: LUSHA service client

**Files:**
- Create: `BE/campaigns/services/lusha.py`

- [ ] **Step 1: Write BE/campaigns/services/lusha.py**

```python
import os
import requests
from typing import Optional


class LushaClient:
    """
    Client for the LUSHA contact enrichment API.
    Finds email, phone, and LinkedIn URL for a named person at a company.

    Expected response shape from LUSHA:
    {
      "data": {
        "emails": [{"email": "john@corp.com"}],
        "phones": [{"number": "+1234567890"}],
        "linkedin_url": "https://linkedin.com/in/john"
      }
    }
    """

    BASE_URL = "https://api.lusha.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LUSHA_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "api_key": self.api_key,
            "Content-Type": "application/json",
        })

    def find_contact(
        self,
        first_name: str,
        last_name: str,
        company_name: str,
    ) -> dict:
        """
        Enrich a contact by name + company.
        Returns dict with keys: email, phone, linkedin_url, raw.
        Returns empty dict keys (None values) on failure.
        """
        empty = {"email": None, "phone": None, "linkedin_url": None, "raw": {}}
        if not first_name or not company_name:
            return empty

        try:
            response = self.session.get(
                f"{self.BASE_URL}/person",
                params={
                    "firstName": first_name,
                    "lastName": last_name,
                    "company": company_name,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            emails = data.get("emails", [])
            phones = data.get("phones", [])
            return {
                "email": emails[0]["email"] if emails else None,
                "phone": phones[0]["number"] if phones else None,
                "linkedin_url": data.get("linkedin_url"),
                "raw": data,
            }
        except requests.RequestException as exc:
            print(f"[LushaClient] API error: {exc}")
            return empty
```

---

## Task 4: Django-Q2 enrichment tasks

**Files:**
- Create: `BE/campaigns/tasks.py`
- Create: `BE/campaigns/tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

```python
# campaigns/tests/test_tasks.py
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
    with patch("campaigns.tasks.VölzaClient") as MockVolza:
        mock_instance = MagicMock()
        mock_instance.search_importers.return_value = volza_results
        MockVolza.return_value = mock_instance

        enrich_leads_from_volza(str(campaign.id))

    assert Lead.objects.filter(campaign=campaign).count() == 3


@pytest.mark.django_db
def test_enrich_leads_skips_nonexistent_campaign():
    # Should not raise, just return silently
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd BE && source venv/bin/activate
pytest campaigns/tests/test_tasks.py -v
```

Expected: FAIL — `campaigns.tasks` not found

- [ ] **Step 3: Write BE/campaigns/tasks.py**

```python
from campaigns.services.volza import VölzaClient
from campaigns.services.lusha import LushaClient


def enrich_leads_from_volza(campaign_id: str) -> None:
    """
    Django-Q2 task: fetch buyer companies from Volza for all products in a campaign,
    create Lead + Contact records, then queue LUSHA enrichment for contacts missing info.
    """
    from campaigns.models import Campaign, Product
    from leads.models import Lead, Contact, ContactSource, LeadStage
    from django_q.tasks import async_task

    try:
        campaign = Campaign.objects.prefetch_related('products').get(id=campaign_id)
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
            # Skip duplicates within this campaign
            if Lead.objects.filter(campaign=campaign, company_name=item["company_name"]).exists():
                continue

            lead = Lead.objects.create(
                campaign=campaign,
                company_name=item.get("company_name", ""),
                company_country=item.get("country", ""),
                company_website=item.get("website", ""),
                stage=LeadStage.DISCOVERED,
                volza_data=item,
                purchase_history=item.get("purchase_history", {}),
                pricing_trend=item.get("pricing_trend", {}),
            )

            contact_name = item.get("contact_name", "")
            first_name = contact_name.split()[0] if contact_name else ""
            last_name = " ".join(contact_name.split()[1:]) if contact_name else ""

            contact = Contact.objects.create(
                lead=lead,
                first_name=first_name,
                last_name=last_name,
                designation=item.get("contact_designation", ""),
                email=item.get("contact_email") or None,
                source=ContactSource.VOLZA,
                is_primary=True,
            )

            # If no email or phone — enrich via LUSHA
            if not contact.email and not contact.phone:
                async_task("campaigns.tasks.enrich_contacts_from_lusha", str(contact.id))


def enrich_contacts_from_lusha(contact_id: str) -> None:
    """
    Django-Q2 task: enrich a single Contact with email/phone via LUSHA API.
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest campaigns/tests/test_tasks.py -v
```

Expected: 5 passed

---

## Task 5: Products + Campaigns serializers, viewsets, URLs

**Files:**
- Create: `BE/campaigns/serializers.py`
- Create: `BE/campaigns/views.py`
- Create: `BE/campaigns/urls.py`
- Create: `BE/campaigns/tests/test_views.py`
- Modify: `BE/config/urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# campaigns/tests/test_views.py
import io
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Product, Campaign, CampaignStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def product(user):
    return Product.objects.create(
        name='Acetone', hsn_code='29141100', cas_number='67-64-1', created_by=user
    )


# ── Product tests ──

@pytest.mark.django_db
def test_list_products(auth_client, product):
    response = auth_client.get('/api/products/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['name'] == 'Acetone'


@pytest.mark.django_db
def test_create_product(auth_client):
    response = auth_client.post('/api/products/', {
        'name': 'Ethanol', 'hsn_code': '22071000', 'cas_number': '64-17-5'
    })
    assert response.status_code == 201
    assert Product.objects.filter(name='Ethanol').exists()


@pytest.mark.django_db
def test_delete_product(auth_client, product):
    response = auth_client.delete(f'/api/products/{product.id}/')
    assert response.status_code == 204
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_products_requires_auth(api_client):
    response = api_client.get('/api/products/')
    assert response.status_code == 401


# ── Campaign tests ──

@pytest.mark.django_db
def test_create_campaign_triggers_task(auth_client, product):
    from unittest.mock import patch
    with patch('campaigns.views.async_task') as mock_task:
        response = auth_client.post('/api/campaigns/', {
            'title': 'India Campaign',
            'product_ids': [str(product.id)],
            'country_filters': ['IN', 'US'],
            'num_transactions_yr': 10,
        }, format='json')
    assert response.status_code == 201
    assert mock_task.called
    assert Campaign.objects.filter(title='India Campaign').exists()


@pytest.mark.django_db
def test_list_campaigns_includes_lead_count(auth_client, user, product):
    from unittest.mock import patch
    from leads.models import Lead
    with patch('campaigns.views.async_task'):
        auth_client.post('/api/campaigns/', {
            'title': 'Test',
            'product_ids': [str(product.id)],
            'country_filters': ['IN'],
            'num_transactions_yr': 5,
        }, format='json')
    campaign = Campaign.objects.get(title='Test')
    Lead.objects.create(campaign=campaign, company_name='Corp A', company_country='IN')
    response = auth_client.get('/api/campaigns/')
    assert response.status_code == 200
    assert response.data[0]['lead_count'] == 1


@pytest.mark.django_db
def test_campaign_leads_endpoint(auth_client, user, product):
    from unittest.mock import patch
    from leads.models import Lead
    with patch('campaigns.views.async_task'):
        resp = auth_client.post('/api/campaigns/', {
            'title': 'Test',
            'product_ids': [str(product.id)],
            'country_filters': ['IN'],
            'num_transactions_yr': 5,
        }, format='json')
    campaign_id = resp.data['id']
    campaign = Campaign.objects.get(id=campaign_id)
    Lead.objects.create(campaign=campaign, company_name='Corp A', company_country='IN')
    Lead.objects.create(campaign=campaign, company_name='Corp B', company_country='US')
    response = auth_client.get(f'/api/campaigns/{campaign_id}/leads/')
    assert response.status_code == 200
    assert len(response.data) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest campaigns/tests/test_views.py -v
```

Expected: FAIL — URLs not configured

- [ ] **Step 3: Write BE/campaigns/serializers.py**

```python
from rest_framework import serializers
from .models import Product, Campaign


class ProductSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    has_brochure = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'hsn_code', 'cas_number', 'description',
            'technical_specs', 'brochure_pdf', 'has_brochure',
            'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by_email', 'has_brochure', 'created_at', 'updated_at']

    def get_has_brochure(self, obj):
        return bool(obj.brochure_pdf)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CampaignSerializer(serializers.ModelSerializer):
    product_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=True
    )
    products = ProductSerializer(many=True, read_only=True)
    lead_count = serializers.IntegerField(read_only=True, default=0)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id', 'title', 'product_ids', 'products', 'country_filters',
            'num_transactions_yr', 'status', 'lead_count',
            'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'lead_count', 'created_by_email', 'created_at', 'updated_at']

    def create(self, validated_data):
        product_ids = validated_data.pop('product_ids', [])
        validated_data['created_by'] = self.context['request'].user
        campaign = super().create(validated_data)
        campaign.products.set(product_ids)
        return campaign
```

- [ ] **Step 4: Write BE/campaigns/views.py**

```python
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_q.tasks import async_task

from leads.serializers import LeadListSerializer
from leads.models import Lead
from .models import Product, Campaign
from .serializers import ProductSerializer, CampaignSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Product.objects.select_related('created_by').order_by('-created_at')


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return (
            Campaign.objects
            .select_related('created_by')
            .prefetch_related('products')
            .annotate(lead_count=Count('leads'))
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        campaign = serializer.save()
        async_task('campaigns.tasks.enrich_leads_from_volza', str(campaign.id))

    @action(detail=True, methods=['get'], url_path='leads')
    def leads(self, request, pk=None):
        campaign = self.get_object()
        stage = request.query_params.get('stage')
        qs = Lead.objects.filter(campaign=campaign).select_related(
            'campaign', 'assigned_to'
        ).prefetch_related('contacts')
        if stage:
            qs = qs.filter(stage=stage)
        serializer = LeadListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='export-missing')
    def export_missing(self, request, pk=None):
        import csv
        import io
        from django.http import HttpResponse

        campaign = self.get_object()
        missing_leads = [
            lead for lead in campaign.leads.prefetch_related('contacts').all()
            if lead.has_missing_contact
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Company Name', 'Country', 'Website', 'Notes'])
        for lead in missing_leads:
            writer.writerow([
                lead.company_name,
                lead.company_country,
                lead.company_website,
                'No email or phone found',
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="missing-contacts-{campaign.id}.csv"'
        return response
```

- [ ] **Step 5: Write BE/campaigns/urls.py**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet, basename='product')
router.register('campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **Step 6: Write BE/leads/serializers.py**

```python
from rest_framework import serializers
from .models import Lead, Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'designation',
            'email', 'phone', 'linkedin_url', 'source', 'is_primary',
        ]


class LeadListSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)
    has_missing_contact = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'company_name', 'company_country', 'company_website',
            'stage', 'auto_flow_paused', 'has_missing_contact',
            'contacts', 'created_at', 'updated_at',
        ]
```

- [ ] **Step 7: Write BE/leads/views.py**

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Lead
from .serializers import LeadListSerializer


class LeadViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeadListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Lead.objects
            .select_related('campaign', 'assigned_to')
            .prefetch_related('contacts')
            .order_by('-created_at')
        )
```

- [ ] **Step 8: Write BE/leads/urls.py**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('leads', views.LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **Step 9: Update BE/config/urls.py to include new routes**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('campaigns.urls')),
    path('api/', include('leads.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 10: Run all tests**

```bash
cd BE && source venv/bin/activate
pytest -v
```

Expected: All 24+ tests pass (19 from Phase 1 + 5 task tests + campaign/lead view tests)

---

## Task 6: FE — API clients

**Files:**
- Create: `FE/src/api/products.js`
- Create: `FE/src/api/campaigns.js`

- [ ] **Step 1: Write FE/src/api/products.js**

```js
import api from './axios'

export const listProducts = () =>
  api.get('/products/').then((r) => r.data)

export const createProduct = (data) =>
  api.post('/products/', data).then((r) => r.data)

export const updateProduct = (id, data) =>
  api.patch(`/products/${id}/`, data).then((r) => r.data)

export const uploadBrochure = (id, file) => {
  const form = new FormData()
  form.append('brochure_pdf', file)
  return api.patch(`/products/${id}/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const deleteProduct = (id) =>
  api.delete(`/products/${id}/`).then((r) => r.data)
```

- [ ] **Step 2: Write FE/src/api/campaigns.js**

```js
import api from './axios'

export const listCampaigns = () =>
  api.get('/campaigns/').then((r) => r.data)

export const createCampaign = (data) =>
  api.post('/campaigns/', data).then((r) => r.data)

export const getCampaign = (id) =>
  api.get(`/campaigns/${id}/`).then((r) => r.data)

export const getCampaignLeads = (id, stage) =>
  api.get(`/campaigns/${id}/leads/`, { params: stage ? { stage } : {} }).then((r) => r.data)

export const exportMissingContacts = (id) =>
  api.post(`/campaigns/${id}/export-missing/`, {}, { responseType: 'blob' }).then((r) => {
    const url = window.URL.createObjectURL(new Blob([r.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `missing-contacts-${id}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
```

---

## Task 7: FE — StageBadge + LeadTable components

**Files:**
- Create: `FE/src/components/leads/StageBadge.jsx`
- Create: `FE/src/components/leads/LeadTable.jsx`
- Create: `FE/src/components/leads/EnrichmentBanner.jsx`

- [ ] **Step 1: Write FE/src/components/leads/StageBadge.jsx**

```jsx
const STAGE_CONFIG = {
  discovered:        { label: 'Discovered',        bg: 'bg-gray-100',   text: 'text-gray-700' },
  intro_sent:        { label: 'Intro Sent',         bg: 'bg-blue-100',   text: 'text-blue-700' },
  pricing_sent:      { label: 'Pricing Sent',       bg: 'bg-purple-100', text: 'text-purple-700' },
  pricing_followup:  { label: 'Pricing Follow-Up',  bg: 'bg-yellow-100', text: 'text-yellow-700' },
  meeting_set:       { label: 'Meeting Set',        bg: 'bg-indigo-100', text: 'text-indigo-700' },
  closed_won:        { label: 'Won',                bg: 'bg-green-100',  text: 'text-green-700' },
  closed_lost:       { label: 'Lost',               bg: 'bg-red-100',    text: 'text-red-700' },
}

export default function StageBadge({ stage }) {
  const config = STAGE_CONFIG[stage] || { label: stage, bg: 'bg-gray-100', text: 'text-gray-600' }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}
```

- [ ] **Step 2: Write FE/src/components/leads/EnrichmentBanner.jsx**

```jsx
export default function EnrichmentBanner({ leadCount }) {
  if (leadCount > 0) return null
  return (
    <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
      <svg className="animate-spin h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <p className="text-sm text-indigo-700 font-medium">
        Enriching leads from Volza and LUSHA… this may take a minute.
      </p>
    </div>
  )
}
```

- [ ] **Step 3: Write FE/src/components/leads/LeadTable.jsx**

```jsx
import StageBadge from './StageBadge'

export default function LeadTable({ leads, selected, onToggle, onToggleAll }) {
  const allSelected = leads.length > 0 && selected.size === leads.length

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 w-10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => onToggleAll()}
                className="rounded border-gray-300"
              />
            </th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Company</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Country</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Stage</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Primary Contact</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Email / Phone</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.map((lead) => {
            const primary = lead.contacts?.find((c) => c.is_primary) || lead.contacts?.[0]
            const missingContact = lead.has_missing_contact
            return (
              <tr
                key={lead.id}
                className={`hover:bg-gray-50 cursor-pointer ${selected.has(lead.id) ? 'bg-indigo-50' : ''}`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(lead.id)}
                    onChange={() => onToggle(lead.id)}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-4 py-3 font-medium text-gray-900">{lead.company_name}</td>
                <td className="px-4 py-3 text-gray-500">{lead.company_country}</td>
                <td className="px-4 py-3"><StageBadge stage={lead.stage} /></td>
                <td className="px-4 py-3 text-gray-700">
                  {primary ? `${primary.first_name} ${primary.last_name}`.trim() : '—'}
                  {primary?.designation && (
                    <span className="block text-xs text-gray-400">{primary.designation}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {missingContact ? (
                    <span className="inline-flex items-center text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                      Missing contact
                    </span>
                  ) : (
                    <span className="text-gray-600 text-xs">
                      {primary?.email || primary?.phone || '—'}
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {leads.length === 0 && (
        <p className="text-center text-gray-400 text-sm py-8">No leads yet.</p>
      )}
    </div>
  )
}
```

---

## Task 8: FE — ProductsPage

**Files:**
- Modify: `FE/src/pages/ProductsPage.jsx`

- [ ] **Step 1: Write FE/src/pages/ProductsPage.jsx**

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listProducts, createProduct, deleteProduct, uploadBrochure } from '../api/products'

export default function ProductsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', hsn_code: '', cas_number: '', description: '' })
  const [error, setError] = useState('')

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: listProducts,
  })

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      setShowForm(false)
      setForm({ name: '', hsn_code: '', cas_number: '', description: '' })
      setError('')
    },
    onError: (err) => setError(err.response?.data?.name?.[0] || 'Failed to create product'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }) => uploadBrochure(id, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })

  function handleSubmit(e) {
    e.preventDefault()
    createMutation.mutate(form)
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Product'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 mb-6 space-y-4">
          <h2 className="font-semibold text-gray-800">New Product</h2>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product Name *</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Acetone" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">HSN Code</label>
              <input value={form.hsn_code} onChange={(e) => setForm({ ...form, hsn_code: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="29141100" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CAS Number</label>
              <input value={form.cas_number} onChange={(e) => setForm({ ...form, cas_number: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="67-64-1" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <button type="submit" disabled={createMutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2 rounded-lg">
            {createMutation.isPending ? 'Saving…' : 'Save Product'}
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <div key={product.id} className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900">{product.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">HSN: {product.hsn_code} · CAS: {product.cas_number}</p>
              </div>
              <div className="flex items-center gap-4">
                {product.has_brochure ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Brochure ✓</span>
                ) : (
                  <label className="cursor-pointer text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium hover:bg-yellow-200">
                    Upload Brochure
                    <input type="file" accept=".pdf" className="hidden"
                      onChange={(e) => {
                        if (e.target.files[0]) uploadMutation.mutate({ id: product.id, file: e.target.files[0] })
                      }} />
                  </label>
                )}
                <button onClick={() => {
                  if (window.confirm(`Delete "${product.name}"?`)) deleteMutation.mutate(product.id)
                }} className="text-xs text-red-500 hover:text-red-700">Delete</button>
              </div>
            </div>
          ))}
          {products.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">No products yet. Add your first product above.</p>
          )}
        </div>
      )}
    </div>
  )
}
```

---

## Task 9: FE — NewCampaignPage

**Files:**
- Modify: `FE/src/pages/NewCampaignPage.jsx`

- [ ] **Step 1: Write FE/src/pages/NewCampaignPage.jsx**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listProducts } from '../api/products'
import { createCampaign } from '../api/campaigns'

const COUNTRIES = [
  { code: 'IN', name: 'India' }, { code: 'US', name: 'United States' },
  { code: 'CN', name: 'China' }, { code: 'DE', name: 'Germany' },
  { code: 'GB', name: 'United Kingdom' }, { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' }, { code: 'FR', name: 'France' },
  { code: 'IT', name: 'Italy' }, { code: 'NL', name: 'Netherlands' },
  { code: 'SG', name: 'Singapore' }, { code: 'AE', name: 'UAE' },
  { code: 'BR', name: 'Brazil' }, { code: 'CA', name: 'Canada' },
  { code: 'AU', name: 'Australia' }, { code: 'MX', name: 'Mexico' },
]

export default function NewCampaignPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [selectedProducts, setSelectedProducts] = useState([])
  const [selectedCountries, setSelectedCountries] = useState([])
  const [numTransactions, setNumTransactions] = useState('')
  const [countrySearch, setCountrySearch] = useState('')
  const [error, setError] = useState('')

  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: listProducts })

  const mutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: (data) => navigate(`/campaigns/${data.id}/leads`),
    onError: () => setError('Failed to create campaign. Please try again.'),
  })

  function toggleProduct(id) {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    )
  }

  function toggleCountry(code) {
    setSelectedCountries((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedProducts.length) return setError('Select at least one product.')
    if (!selectedCountries.length) return setError('Select at least one country.')
    setError('')
    mutation.mutate({
      title: title || `Campaign ${new Date().toLocaleDateString()}`,
      product_ids: selectedProducts,
      country_filters: selectedCountries,
      num_transactions_yr: parseInt(numTransactions) || 0,
    })
  }

  const filteredCountries = COUNTRIES.filter((c) =>
    c.name.toLowerCase().includes(countrySearch.toLowerCase())
  )

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">New Campaign</h1>
      <p className="text-sm text-gray-500 mb-6">Search for buyer leads by product and target countries.</p>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. India Acetone Q2 2026" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Products *</label>
            {products.length === 0 ? (
              <p className="text-sm text-yellow-600">No products found. <a href="/products" className="underline">Add one first.</a></p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {products.map((p) => (
                  <label key={p.id} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProducts.includes(p.id) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}>
                    <input type="checkbox" checked={selectedProducts.includes(p.id)} onChange={() => toggleProduct(p.id)}
                      className="rounded border-gray-300" />
                    <span className="text-sm font-medium text-gray-800">{p.name}</span>
                    <span className="text-xs text-gray-400 ml-auto">{p.hsn_code}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min. Transactions / Year</label>
            <input type="number" min="0" value={numTransactions} onChange={(e) => setNumTransactions(e.target.value)}
              className="w-40 border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="0" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Target Countries *</label>
          <input value={countrySearch} onChange={(e) => setCountrySearch(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3"
            placeholder="Search countries…" />
          <div className="grid grid-cols-3 gap-2 max-h-52 overflow-y-auto">
            {filteredCountries.map((c) => (
              <label key={c.code} className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors text-sm ${
                selectedCountries.includes(c.code) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
              }`}>
                <input type="checkbox" checked={selectedCountries.includes(c.code)} onChange={() => toggleCountry(c.code)}
                  className="rounded border-gray-300" />
                <span className="font-medium text-gray-700">{c.code}</span>
                <span className="text-gray-400 text-xs">{c.name}</span>
              </label>
            ))}
          </div>
          {selectedCountries.length > 0 && (
            <p className="text-xs text-indigo-600 mt-2">{selectedCountries.length} selected: {selectedCountries.join(', ')}</p>
          )}
        </div>

        <button type="submit" disabled={mutation.isPending}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold py-3 rounded-xl text-sm transition-colors">
          {mutation.isPending ? 'Starting search…' : '🔍 Search Leads'}
        </button>
      </form>
    </div>
  )
}
```

---

## Task 10: FE — CampaignLeadsPage

**Files:**
- Modify: `FE/src/pages/CampaignLeadsPage.jsx`

- [ ] **Step 1: Write FE/src/pages/CampaignLeadsPage.jsx**

```jsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getCampaign, getCampaignLeads, exportMissingContacts } from '../api/campaigns'
import LeadTable from '../components/leads/LeadTable'
import EnrichmentBanner from '../components/leads/EnrichmentBanner'

const STAGES = [
  { key: '', label: 'All' },
  { key: 'discovered', label: 'Discovered' },
  { key: 'intro_sent', label: 'Intro Sent' },
  { key: 'pricing_sent', label: 'Pricing Sent' },
  { key: 'meeting_set', label: 'Meeting Set' },
  { key: 'closed_won', label: 'Won' },
  { key: 'closed_lost', label: 'Lost' },
]

export default function CampaignLeadsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeStage, setActiveStage] = useState('')
  const [selected, setSelected] = useState(new Set())

  const { data: campaign } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => getCampaign(id),
    refetchInterval: (data) => (data?.lead_count === 0 ? 5000 : false),
  })

  const { data: leads = [], isLoading } = useQuery({
    queryKey: ['campaign-leads', id, activeStage],
    queryFn: () => getCampaignLeads(id, activeStage),
    refetchInterval: leads.length === 0 ? 5000 : false,
  })

  function toggleLead(leadId) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(leadId) ? next.delete(leadId) : next.add(leadId)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === leads.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(leads.map((l) => l.id)))
    }
  }

  const missingCount = leads.filter((l) => l.has_missing_contact).length

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <button onClick={() => navigate('/campaigns/new')} className="text-sm text-gray-400 hover:text-gray-600">← Campaigns</button>
      </div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{campaign?.title || 'Campaign Leads'}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{leads.length} leads found</p>
        </div>
        {missingCount > 0 && (
          <button
            onClick={() => exportMissingContacts(id)}
            className="text-sm bg-yellow-100 text-yellow-800 hover:bg-yellow-200 font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            Export {missingCount} Missing Contacts CSV
          </button>
        )}
      </div>

      <EnrichmentBanner leadCount={leads.length} />

      {/* Stage filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STAGES.map((s) => (
          <button
            key={s.key}
            onClick={() => { setActiveStage(s.key); setSelected(new Set()) }}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeStage === s.key
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
          <span className="text-sm font-medium text-indigo-700">{selected.size} selected</span>
          <button
            onClick={() => navigate(`/leads/${[...selected][0]}`)}
            className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-indigo-700"
          >
            View Lead →
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm text-center py-8">Loading leads…</p>
      ) : (
        <LeadTable
          leads={leads}
          selected={selected}
          onToggle={toggleLead}
          onToggleAll={toggleAll}
        />
      )}
    </div>
  )
}
```

---

## Task 11: FE — Update Navbar to include Campaigns list link

**Files:**
- Modify: `FE/src/components/layout/Navbar.jsx`

- [ ] **Step 1: Update Navbar with Campaigns list link**

Replace the `Campaigns` nav link to point to `/campaigns`:

```jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <nav className="bg-slate-900 h-13 flex items-center px-6 gap-6">
      <Link to="/dashboard" className="text-white font-bold text-base tracking-tight">
        Sales<span className="text-indigo-400">Catalyst</span>
      </Link>
      <Link to="/dashboard" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Dashboard</Link>
      <Link to="/campaigns" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Campaigns</Link>
      <Link to="/products" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Products</Link>
      <Link to="/ai-drafts" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">AI Drafts</Link>
      <div className="ml-auto flex items-center gap-3">
        <span className="text-slate-400 text-sm">{user?.email}</span>
        <button onClick={handleLogout} className="text-slate-400 hover:text-white text-sm transition-colors">
          Logout
        </button>
      </div>
    </nav>
  )
}
```

Also add a `/campaigns` route that shows a campaigns list page. Create `FE/src/pages/CampaignsListPage.jsx`:

```jsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listCampaigns } from '../api/campaigns'

export default function CampaignsListPage() {
  const navigate = useNavigate()
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: listCampaigns,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <button
          onClick={() => navigate('/campaigns/new')}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          + New Campaign
        </button>
      </div>
      {isLoading ? <p className="text-gray-400 text-sm">Loading…</p> : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <div key={c.id}
              onClick={() => navigate(`/campaigns/${c.id}/leads`)}
              className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between cursor-pointer hover:border-indigo-300 transition-colors"
            >
              <div>
                <p className="font-semibold text-gray-900">{c.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {c.products?.map((p) => p.name).join(', ')} · {c.country_filters?.join(', ')}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-indigo-600">{c.lead_count} leads</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  c.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}>{c.status}</span>
              </div>
            </div>
          ))}
          {campaigns.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">No campaigns yet. Create your first one.</p>
          )}
        </div>
      )}
    </div>
  )
}
```

Update `FE/src/App.jsx` to add the `/campaigns` route:

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/layout/PrivateRoute'
import Navbar from './components/layout/Navbar'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CampaignsListPage from './pages/CampaignsListPage'
import NewCampaignPage from './pages/NewCampaignPage'
import CampaignLeadsPage from './pages/CampaignLeadsPage'
import LeadDetailPage from './pages/LeadDetailPage'
import ProductsPage from './pages/ProductsPage'
import AIDraftsPage from './pages/AIDraftsPage'

function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main>
        <Routes>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="campaigns" element={<CampaignsListPage />} />
          <Route path="campaigns/new" element={<NewCampaignPage />} />
          <Route path="campaigns/:id/leads" element={<CampaignLeadsPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="ai-drafts" element={<AIDraftsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<PrivateRoute />}>
          <Route path="/*" element={<AppLayout />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

---

## Final Verification

```bash
# Backend — all tests pass
cd BE && source venv/bin/activate && pytest -v

# Backend — server starts
python manage.py runserver

# Frontend — compiles clean
cd FE && npm run build
```

**Phase 2 done when:**
- All backend tests pass (24+ total)
- `GET /api/products/` returns product list
- `POST /api/campaigns/` creates campaign and queues Django-Q2 task
- `GET /api/campaigns/:id/leads/` returns lead list
- FE builds without errors
- Products page: create product, upload brochure PDF, delete product
- New Campaign page: select products + countries → submit → navigates to leads page with "Enriching…" banner
- Campaigns list page shows all campaigns with lead counts

**Next:** Phase 3 plan covers the full Customer Dashboard (lead detail page, progress bar, email/call/timeline tabs, contact cards, auto_flow_paused toggle).
