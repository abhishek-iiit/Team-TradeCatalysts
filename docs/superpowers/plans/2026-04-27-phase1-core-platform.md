# Phase 1: Core Platform + Auth + DB Schema — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a fully running Django + React project locally with PostgreSQL, JWT auth, all 10 database models migrated, and a working login page.

**Architecture:** Django 5 DRF backend with 6 apps (accounts, campaigns, leads, communications, ai_assistant, deals) sharing a `common` TimestampedModel base. React 19 + Vite frontend with JWT auth context, Axios interceptor, and React Router routing. Django-Q2 uses PostgreSQL as its broker — no Redis needed.

**Tech Stack:** Django 5.2 · DRF 3.16 · djangorestframework-simplejwt · Django-Q2 · PostgreSQL 16 · pytest-django · React 19 · Vite 8 · React Router v6 · TanStack Query v5 · Tailwind CSS v4 · Axios

> **Note:** This is Phase 1 of 7. Phases 2–7 each have their own plan file. This plan ends with: Django running on :8000, React on :5173, all models migrated, login working end-to-end.

---

## File Map

### Backend (BE/)
```
BE/
  requirements.txt
  pytest.ini
  .env.example
  manage.py
  config/
    __init__.py
    settings/
      __init__.py
      base.py          ← shared settings
      local.py         ← local dev overrides
    urls.py            ← root URL conf
    wsgi.py
  common/
    __init__.py
    models.py          ← TimestampedModel (abstract base for all models)
  accounts/
    __init__.py
    models.py          ← Custom User (email as USERNAME_FIELD)
    serializers.py     ← UserSerializer
    views.py           ← login, logout, me endpoints
    urls.py
    admin.py
    tests/
      __init__.py
      test_models.py
      test_views.py
  campaigns/
    __init__.py
    models.py          ← Product, Campaign, CampaignStatus
    admin.py
    tests/
      __init__.py
      test_models.py
  leads/
    __init__.py
    models.py          ← Lead, LeadStage, Contact, ContactSource, LeadAction, ActionType
    admin.py
    tests/
      __init__.py
      test_models.py
  communications/
    __init__.py
    models.py          ← EmailThread, ThreadType, EmailMessage, MessageDirection
    admin.py
    tests/
      __init__.py
      test_models.py
  ai_assistant/
    __init__.py
    models.py          ← AIDraft, DraftStatus
    admin.py
    tests/
      __init__.py
      test_models.py
  deals/
    __init__.py
    models.py          ← Meeting, MeetingStatus, Deal, DealOutcome
    admin.py
    tests/
      __init__.py
      test_models.py
```

### Frontend (FE/src/)
```
FE/src/
  api/
    axios.js           ← Axios instance with JWT Bearer interceptor + refresh logic
    auth.js            ← login(), logout(), getMe() API calls
  contexts/
    AuthContext.jsx    ← AuthProvider, useAuth hook
  components/
    layout/
      Navbar.jsx       ← top nav with user display + logout
      PrivateRoute.jsx ← redirects to /login if no token
  pages/
    LoginPage.jsx      ← email + password form, calls login API
    DashboardPage.jsx  ← placeholder "Dashboard coming in Phase 3"
    CampaignLeadsPage.jsx   ← placeholder
    NewCampaignPage.jsx     ← placeholder
    LeadDetailPage.jsx      ← placeholder
    ProductsPage.jsx        ← placeholder
    AIDraftsPage.jsx        ← placeholder
  App.jsx              ← React Router routes
  main.jsx             ← wraps App in QueryClientProvider + AuthProvider
  index.css            ← Tailwind v4 import
```

---

## Task 1: Django project scaffold + requirements.txt

**Files:**
- Create: `BE/requirements.txt`
- Create: `BE/pytest.ini`
- Create: `BE/.env.example`
- Create: `BE/manage.py`
- Create: `BE/config/__init__.py`
- Create: `BE/config/wsgi.py`

- [ ] **Step 1: Create BE/requirements.txt**

```
Django==5.2
djangorestframework==3.16.1
djangorestframework-simplejwt==5.4.0
django-cors-headers==4.7.0
django-environ==0.12.0
dj-database-url==2.3.0
psycopg2-binary==2.9.10
django-q2==1.7.3
google-generativeai==0.8.4
pytest==8.3.5
pytest-django==4.10.0
factory-boy==3.3.3
```

- [ ] **Step 2: Create BE/pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 3: Create BE/.env.example**

```
SECRET_KEY=change-me-in-production
DEBUG=True
DATABASE_URL=postgresql://localhost:5432/salescatalyst

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

VOLZA_API_KEY=
LUSHA_API_KEY=
GEMINI_API_KEY=
GOOGLE_CALENDAR_CREDENTIALS_JSON=
GMAIL_OAUTH_CREDENTIALS_JSON=
```

- [ ] **Step 4: Install dependencies and scaffold Django project**

```bash
cd BE
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
django-admin startproject config .
```

This creates `manage.py` and `config/` with `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`.

- [ ] **Step 5: Move config/settings.py → config/settings/base.py**

```bash
mkdir config/settings
mv config/settings.py config/settings/base.py
touch config/settings/__init__.py
```

- [ ] **Step 6: Create app directories**

```bash
mkdir -p common accounts campaigns leads communications ai_assistant deals
for app in common accounts campaigns leads communications ai_assistant deals; do
  touch $app/__init__.py
  mkdir -p $app/tests
  touch $app/tests/__init__.py
done
```

- [ ] **Step 7: Create Django apps**

```bash
python manage.py startapp accounts accounts
python manage.py startapp campaigns campaigns
python manage.py startapp leads leads
python manage.py startapp communications communications
python manage.py startapp ai_assistant ai_assistant
python manage.py startapp deals deals
```

---

## Task 2: Settings configuration

**Files:**
- Create: `BE/config/settings/local.py`
- Modify: `BE/config/settings/base.py`

- [ ] **Step 1: Write BE/config/settings/base.py**

```python
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_q',
]

LOCAL_APPS = [
    'common',
    'accounts',
    'campaigns',
    'leads',
    'communications',
    'ai_assistant',
    'deals',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://localhost:5432/salescatalyst')
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

Q_CLUSTER = {
    'name': 'salescatalyst',
    'workers': 2,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q2',
    'orm': 'default',
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True
```

- [ ] **Step 2: Write BE/config/settings/local.py**

```python
from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True
```

- [ ] **Step 3: Copy .env.example to .env and fill in values**

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL (create DB first)
```

- [ ] **Step 4: Create the PostgreSQL database**

```bash
createdb salescatalyst
```

Expected: no error. Verify with `psql salescatalyst -c "\l"`.

---

## Task 3: TimestampedModel base

**Files:**
- Create: `BE/common/models.py`

- [ ] **Step 1: Write common/models.py**

```python
import uuid
from django.db import models


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

- [ ] **Step 2: Write test for TimestampedModel**

Create `BE/common/tests/__init__.py` and `BE/common/tests/test_models.py`:

```python
import uuid
import pytest
from campaigns.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_timestamped_model_has_uuid_pk():
    user = User.objects.create_user(
        username='tester', email='t@t.com', password='pass'
    )
    product = Product.objects.create(
        name='Test Product', hsn_code='1234', cas_number='5678', created_by=user
    )
    assert isinstance(product.id, uuid.UUID)
    assert product.created_at is not None
    assert product.updated_at is not None
```

- [ ] **Step 3: Run test (expect ImportError until Task 5 is done — come back here)**

```bash
cd BE && source venv/bin/activate
pytest common/tests/test_models.py -v
```

Expected after Task 5: PASS

---

## Task 4: Custom User model (accounts app)

**Files:**
- Create: `BE/accounts/models.py`
- Create: `BE/accounts/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# accounts/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_create_with_email():
    user = User.objects.create_user(
        username='john',
        email='john@example.com',
        password='securepass123'
    )
    assert user.email == 'john@example.com'
    assert user.check_password('securepass123')
    assert str(user) == 'john@example.com'


@pytest.mark.django_db
def test_user_email_is_unique(db):
    User.objects.create_user(username='a', email='same@example.com', password='pass')
    with pytest.raises(Exception):
        User.objects.create_user(username='b', email='same@example.com', password='pass')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest accounts/tests/test_models.py -v
```

Expected: FAIL — `accounts.User` not found

- [ ] **Step 3: Write accounts/models.py**

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest accounts/tests/test_models.py -v
```

Expected: 2 passed

---

## Task 5: Product + Campaign models (campaigns app)

**Files:**
- Create: `BE/campaigns/models.py`
- Create: `BE/campaigns/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# campaigns/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Product, Campaign, CampaignStatus

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='seller', email='seller@test.com', password='pass'
    )


@pytest.mark.django_db
def test_product_creation(user):
    product = Product.objects.create(
        name='Acetone',
        hsn_code='29141100',
        cas_number='67-64-1',
        created_by=user,
    )
    assert product.name == 'Acetone'
    assert product.brochure_pdf.name is None  # no brochure yet
    assert str(product) == 'Acetone'


@pytest.mark.django_db
def test_campaign_creation(user):
    product = Product.objects.create(
        name='Acetone', hsn_code='29141100', cas_number='67-64-1', created_by=user
    )
    campaign = Campaign.objects.create(
        title='India Acetone Search',
        country_filters=['IN', 'US'],
        num_transactions_yr=10,
        created_by=user,
    )
    campaign.products.add(product)
    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.products.count() == 1
    assert str(campaign) == 'India Acetone Search'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest campaigns/tests/test_models.py -v
```

Expected: FAIL — `campaigns.models` not found

- [ ] **Step 3: Write campaigns/models.py**

```python
from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class CampaignStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'


class Product(TimestampedModel):
    name = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=50)
    cas_number = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    technical_specs = models.JSONField(default=dict)
    brochure_pdf = models.FileField(upload_to='brochures/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
    )

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Campaign(TimestampedModel):
    title = models.CharField(max_length=255)
    products = models.ManyToManyField(Product, related_name='campaigns', blank=True)
    country_filters = models.JSONField(default=list)
    num_transactions_yr = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns',
    )
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.ACTIVE,
    )

    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest campaigns/tests/test_models.py -v
```

Expected: 2 passed

---

## Task 6: Lead + Contact + LeadAction models (leads app)

**Files:**
- Create: `BE/leads/models.py`
- Create: `BE/leads/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# leads/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from leads.models import Lead, LeadStage, Contact, ContactSource, LeadAction, ActionType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.mark.django_db
def test_lead_defaults(campaign):
    lead = Lead.objects.create(
        campaign=campaign,
        company_name='Acme Corp',
        company_country='IN',
    )
    assert lead.stage == LeadStage.DISCOVERED
    assert lead.auto_flow_paused is False
    assert str(lead) == 'Acme Corp (discovered)'


@pytest.mark.django_db
def test_lead_has_missing_contact_when_no_contacts(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Ghost Inc', company_country='US'
    )
    assert lead.has_missing_contact is True


@pytest.mark.django_db
def test_lead_not_missing_contact_when_email_present(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Ghost Inc', company_country='US'
    )
    Contact.objects.create(
        lead=lead, first_name='Jane', last_name='Doe',
        email='jane@ghost.com', source=ContactSource.VOLZA
    )
    assert lead.has_missing_contact is False


@pytest.mark.django_db
def test_lead_action_system_action_has_no_performer(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Sys Inc', company_country='DE'
    )
    action = LeadAction.objects.create(
        lead=lead, action_type=ActionType.INTRO_EMAIL,
        notes='Sent automatically'
    )
    assert action.performed_by is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest leads/tests/test_models.py -v
```

Expected: FAIL — `leads.models` not found

- [ ] **Step 3: Write leads/models.py**

```python
from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class LeadStage(models.TextChoices):
    DISCOVERED = 'discovered', 'Discovered'
    INTRO_SENT = 'intro_sent', 'Intro Sent'
    PRICING_SENT = 'pricing_sent', 'Pricing Sent'
    PRICING_FOLLOWUP = 'pricing_followup', 'Pricing Followup'
    MEETING_SET = 'meeting_set', 'Meeting Set'
    CLOSED_WON = 'closed_won', 'Closed Won'
    CLOSED_LOST = 'closed_lost', 'Closed Lost'


class Lead(TimestampedModel):
    campaign = models.ForeignKey(
        'campaigns.Campaign', on_delete=models.CASCADE, related_name='leads'
    )
    company_name = models.CharField(max_length=255)
    company_country = models.CharField(max_length=10)
    company_website = models.CharField(max_length=255, blank=True)
    stage = models.CharField(
        max_length=30, choices=LeadStage.choices, default=LeadStage.DISCOVERED
    )
    auto_flow_paused = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_leads',
    )
    volza_data = models.JSONField(default=dict)
    pricing_trend = models.JSONField(default=dict)
    purchase_history = models.JSONField(default=dict)

    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company_name} ({self.stage})'

    @property
    def has_missing_contact(self):
        return not self.contacts.filter(
            models.Q(email__isnull=False) | models.Q(phone__isnull=False)
        ).exists()


class ContactSource(models.TextChoices):
    VOLZA = 'volza', 'Volza'
    LUSHA = 'lusha', 'Lusha'
    MANUAL = 'manual', 'Manual'


class Contact(TimestampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    source = models.CharField(
        max_length=20, choices=ContactSource.choices, default=ContactSource.VOLZA
    )
    is_primary = models.BooleanField(default=False)
    lusha_raw = models.JSONField(default=dict)

    class Meta:
        db_table = 'contacts'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} @ {self.lead.company_name}'


class ActionType(models.TextChoices):
    INTRO_EMAIL = 'intro_email', 'Intro Email'
    FOLLOW_UP_CALL = 'follow_up_call', 'Follow Up Call'
    PRICING_EMAIL = 'pricing_email', 'Pricing Email'
    PRICING_FOLLOWUP_EMAIL = 'pricing_followup_email', 'Pricing Follow-Up Email'
    MEETING_SCHEDULED = 'meeting_scheduled', 'Meeting Scheduled'
    NOTE = 'note', 'Note'
    AI_DRAFT_GENERATED = 'ai_draft_generated', 'AI Draft Generated'
    AI_DRAFT_APPROVED = 'ai_draft_approved', 'AI Draft Approved'
    AI_DRAFT_REJECTED = 'ai_draft_rejected', 'AI Draft Rejected'
    DEAL_CLOSED = 'deal_closed', 'Deal Closed'
    MANUAL_TAKEOVER = 'manual_takeover', 'Manual Takeover'


class LeadAction(TimestampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='actions')
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lead_actions',
    )
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = 'lead_actions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action_type} on {self.lead.company_name}'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest leads/tests/test_models.py -v
```

Expected: 4 passed

---

## Task 7: EmailThread + EmailMessage models (communications app)

**Files:**
- Create: `BE/communications/models.py`
- Create: `BE/communications/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# communications/tests/test_models.py
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource
from communications.models import EmailThread, EmailMessage, ThreadType, MessageDirection

User = get_user_model()


@pytest.fixture
def lead(db):
    user = User.objects.create_user(username='u', email='u@t.com', password='p')
    campaign = Campaign.objects.create(title='C', created_by=user)
    return Lead.objects.create(campaign=campaign, company_name='Acme', company_country='IN')


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Bob', email='bob@acme.com', source=ContactSource.VOLZA
    )


@pytest.mark.django_db
def test_email_thread_creation(lead, contact):
    thread = EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction - Our Products',
        thread_type=ThreadType.INTRO,
        gmail_thread_id='abc123',
    )
    assert str(thread) == 'intro: Introduction - Our Products'


@pytest.mark.django_db
def test_email_message_direction(lead, contact):
    thread = EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Intro', thread_type=ThreadType.INTRO,
    )
    msg = EmailMessage.objects.create(
        thread=thread,
        direction=MessageDirection.OUTBOUND,
        body_text='Hello from us',
        sent_at=timezone.now(),
    )
    assert msg.direction == 'outbound'
    assert msg.thread == thread
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest communications/tests/test_models.py -v
```

Expected: FAIL — `communications.models` not found

- [ ] **Step 3: Write communications/models.py**

```python
from django.db import models
from common.models import TimestampedModel


class ThreadType(models.TextChoices):
    INTRO = 'intro', 'Intro'
    PRICING = 'pricing', 'Pricing'
    FOLLOWUP = 'followup', 'Follow-Up'
    NEGOTIATION = 'negotiation', 'Negotiation'


class EmailThread(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='threads'
    )
    contact = models.ForeignKey(
        'leads.Contact', on_delete=models.CASCADE, related_name='threads'
    )
    subject = models.CharField(max_length=500)
    thread_type = models.CharField(max_length=20, choices=ThreadType.choices)
    gmail_thread_id = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'email_threads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.thread_type}: {self.subject}'


class MessageDirection(models.TextChoices):
    OUTBOUND = 'outbound', 'Outbound'
    INBOUND = 'inbound', 'Inbound'


class EmailMessage(TimestampedModel):
    thread = models.ForeignKey(
        EmailThread, on_delete=models.CASCADE, related_name='messages'
    )
    direction = models.CharField(max_length=10, choices=MessageDirection.choices)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    sent_at = models.DateTimeField()
    gmail_message_id = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'email_messages'
        ordering = ['sent_at']

    def __str__(self):
        return f'{self.direction} — {self.thread.subject}'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest communications/tests/test_models.py -v
```

Expected: 2 passed

---

## Task 8: AIDraft model (ai_assistant app)

**Files:**
- Create: `BE/ai_assistant/models.py`
- Create: `BE/ai_assistant/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# ai_assistant/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource
from communications.models import EmailThread, ThreadType
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def thread(db):
    user = User.objects.create_user(username='u', email='u@t.com', password='p')
    campaign = Campaign.objects.create(title='C', created_by=user)
    lead = Lead.objects.create(campaign=campaign, company_name='Corp', company_country='US')
    contact = Contact.objects.create(
        lead=lead, first_name='Ann', email='ann@corp.com', source=ContactSource.VOLZA
    )
    return EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Re: Intro', thread_type=ThreadType.NEGOTIATION,
    )


@pytest.mark.django_db
def test_ai_draft_defaults_to_pending(thread):
    draft = AIDraft.objects.create(
        lead=thread.lead,
        thread=thread,
        draft_content='Dear Ann, thank you for your response...',
        context_summary='Customer asked for 10% discount.',
    )
    assert draft.status == DraftStatus.PENDING_REVIEW
    assert draft.reviewed_by is None
    assert 'Corp' in str(draft)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest ai_assistant/tests/test_models.py -v
```

Expected: FAIL

- [ ] **Step 3: Write ai_assistant/models.py**

```python
from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class DraftStatus(models.TextChoices):
    PENDING_REVIEW = 'pending_review', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    SENT = 'sent', 'Sent'


class AIDraft(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='ai_drafts'
    )
    thread = models.ForeignKey(
        'communications.EmailThread', on_delete=models.CASCADE, related_name='ai_drafts'
    )
    draft_content = models.TextField()
    context_summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=DraftStatus.choices, default=DraftStatus.PENDING_REVIEW
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_drafts',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_drafts'
        ordering = ['-created_at']

    def __str__(self):
        return f'Draft for {self.lead.company_name} ({self.status})'
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest ai_assistant/tests/test_models.py -v
```

Expected: 1 passed

---

## Task 9: Meeting + Deal models (deals app)

**Files:**
- Create: `BE/deals/models.py`
- Create: `BE/deals/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# deals/tests/test_models.py
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource, LeadStage
from deals.models import Meeting, MeetingStatus, Deal, DealOutcome

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(username='u', email='u@t.com', password='p')
    campaign = Campaign.objects.create(title='C', created_by=user)
    lead = Lead.objects.create(campaign=campaign, company_name='BigCo', company_country='IN')
    contact = Contact.objects.create(
        lead=lead, first_name='CEO', email='ceo@bigco.com', source=ContactSource.VOLZA
    )
    return user, lead, contact


@pytest.mark.django_db
def test_meeting_defaults_to_proposed(setup):
    user, lead, contact = setup
    meeting = Meeting.objects.create(
        lead=lead, contact=contact, scheduled_by=user,
        scheduled_at=timezone.now(),
    )
    assert meeting.status == MeetingStatus.PROPOSED


@pytest.mark.django_db
def test_deal_is_one_to_one_with_lead(setup):
    user, lead, contact = setup
    deal = Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON,
        closed_by=user, closed_at=timezone.now(),
        remarks='Great partnership',
    )
    assert deal.outcome == 'won'
    assert lead.deal == deal


@pytest.mark.django_db
def test_deal_cannot_be_created_twice_for_same_lead(setup):
    user, lead, contact = setup
    Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON,
        closed_by=user, closed_at=timezone.now(),
    )
    with pytest.raises(Exception):
        Deal.objects.create(
            lead=lead, outcome=DealOutcome.LOST,
            closed_by=user, closed_at=timezone.now(),
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest deals/tests/test_models.py -v
```

Expected: FAIL

- [ ] **Step 3: Write deals/models.py**

```python
from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class MeetingStatus(models.TextChoices):
    PROPOSED = 'proposed', 'Proposed'
    CONFIRMED = 'confirmed', 'Confirmed'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Meeting(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='meetings'
    )
    contact = models.ForeignKey(
        'leads.Contact', on_delete=models.CASCADE, related_name='meetings'
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_meetings',
    )
    calendar_event_id = models.CharField(max_length=200, blank=True)
    scheduled_at = models.DateTimeField()
    meeting_link = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=MeetingStatus.choices, default=MeetingStatus.PROPOSED
    )

    class Meta:
        db_table = 'meetings'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f'Meeting with {self.lead.company_name} at {self.scheduled_at}'


class DealOutcome(models.TextChoices):
    WON = 'won', 'Won'
    LOST = 'lost', 'Lost'


class Deal(TimestampedModel):
    lead = models.OneToOneField(
        'leads.Lead', on_delete=models.CASCADE, related_name='deal'
    )
    outcome = models.CharField(max_length=10, choices=DealOutcome.choices)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='closed_deals',
    )
    closed_at = models.DateTimeField()
    remarks = models.TextField(blank=True)
    deal_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'deals'
        ordering = ['-closed_at']

    def __str__(self):
        return f'Deal {self.outcome} — {self.lead.company_name}'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest deals/tests/test_models.py -v
```

Expected: 3 passed

---

## Task 10: Run all migrations

**Files:**
- Generated: `BE/accounts/migrations/0001_initial.py`
- Generated: `BE/campaigns/migrations/0001_initial.py`
- Generated: `BE/leads/migrations/0001_initial.py`
- Generated: `BE/communications/migrations/0001_initial.py`
- Generated: `BE/ai_assistant/migrations/0001_initial.py`
- Generated: `BE/deals/migrations/0001_initial.py`

- [ ] **Step 1: Generate migrations for all apps**

```bash
cd BE && source venv/bin/activate
python manage.py makemigrations accounts campaigns leads communications ai_assistant deals
```

Expected output: Created 6 migration files (one per app). No errors.

- [ ] **Step 2: Apply all migrations**

```bash
python manage.py migrate
```

Expected output: All migrations applied without error. Last line: `Running deferred SQL... OK`

- [ ] **Step 3: Verify all tables exist in PostgreSQL**

```bash
python manage.py dbshell
\dt
\q
```

Expected: See tables: `users`, `products`, `campaigns`, `leads`, `contacts`, `lead_actions`, `email_threads`, `email_messages`, `ai_drafts`, `meetings`, `deals`, plus Django internals.

- [ ] **Step 4: Run full test suite — all should pass**

```bash
pytest -v
```

Expected: All model tests pass (accounts, campaigns, leads, communications, ai_assistant, deals). Also run the TimestampedModel test from Task 3 now.

---

## Task 11: JWT Auth endpoints (accounts app)

**Files:**
- Create: `BE/accounts/serializers.py`
- Create: `BE/accounts/views.py`
- Create: `BE/accounts/urls.py`
- Modify: `BE/config/urls.py`
- Create: `BE/accounts/tests/test_views.py`

- [ ] **Step 1: Write the failing tests**

```python
# accounts/tests/test_views.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='john', email='john@example.com', password='securepass123'
    )


@pytest.mark.django_db
def test_login_returns_tokens(api_client, user):
    response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'securepass123',
    })
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert response.data['user']['email'] == 'john@example.com'


@pytest.mark.django_db
def test_login_wrong_password_returns_401(api_client, user):
    response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'wrongpassword',
    })
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get('/api/auth/me/')
    assert response.status_code == 200
    assert response.data['email'] == 'john@example.com'


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get('/api/auth/me/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, user):
    # Get tokens via login
    login_response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'securepass123',
    })
    refresh_token = login_response.data['refresh']
    access_token = login_response.data['access']

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    response = api_client.post('/api/auth/logout/', {'refresh': refresh_token})
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest accounts/tests/test_views.py -v
```

Expected: FAIL — 404 (URLs not configured yet)

- [ ] **Step 3: Write accounts/serializers.py**

```python
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_staff']
        read_only_fields = fields
```

- [ ] **Step 4: Write accounts/views.py**

```python
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    user = authenticate(request, username=email, password=password)
    if not user:
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'Logged out successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)
```

- [ ] **Step 5: Write accounts/urls.py**

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('login/', views.login_view, name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', views.logout_view, name='auth-logout'),
    path('me/', views.me_view, name='auth-me'),
]
```

- [ ] **Step 6: Write config/urls.py**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest accounts/tests/test_views.py -v
```

Expected: 5 passed

---

## Task 12: Admin registration for all models

**Files:**
- Create: `BE/accounts/admin.py`
- Create: `BE/campaigns/admin.py`
- Create: `BE/leads/admin.py`
- Create: `BE/communications/admin.py`
- Create: `BE/ai_assistant/admin.py`
- Create: `BE/deals/admin.py`

- [ ] **Step 1: Write accounts/admin.py**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'username']
    ordering = ['email']
    fieldsets = BaseUserAdmin.fieldsets
```

- [ ] **Step 2: Write campaigns/admin.py**

```python
from django.contrib import admin
from .models import Product, Campaign


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'hsn_code', 'cas_number', 'created_by', 'created_at']
    search_fields = ['name', 'hsn_code', 'cas_number']
    list_filter = ['created_at']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    filter_horizontal = ['products']
```

- [ ] **Step 3: Write leads/admin.py**

```python
from django.contrib import admin
from .models import Lead, Contact, LeadAction


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_country', 'stage', 'auto_flow_paused', 'assigned_to', 'created_at']
    list_filter = ['stage', 'auto_flow_paused', 'company_country']
    search_fields = ['company_name']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'source', 'is_primary']
    list_filter = ['source', 'is_primary']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(LeadAction)
class LeadActionAdmin(admin.ModelAdmin):
    list_display = ['lead', 'action_type', 'performed_by', 'created_at']
    list_filter = ['action_type', 'created_at']
```

- [ ] **Step 4: Write communications/admin.py**

```python
from django.contrib import admin
from .models import EmailThread, EmailMessage


@admin.register(EmailThread)
class EmailThreadAdmin(admin.ModelAdmin):
    list_display = ['subject', 'thread_type', 'lead', 'contact', 'created_at']
    list_filter = ['thread_type']


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ['thread', 'direction', 'sent_at']
    list_filter = ['direction']
```

- [ ] **Step 5: Write ai_assistant/admin.py**

```python
from django.contrib import admin
from .models import AIDraft


@admin.register(AIDraft)
class AIDraftAdmin(admin.ModelAdmin):
    list_display = ['lead', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status']
```

- [ ] **Step 6: Write deals/admin.py**

```python
from django.contrib import admin
from .models import Meeting, Deal


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['lead', 'contact', 'scheduled_at', 'status']
    list_filter = ['status']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['lead', 'outcome', 'closed_by', 'closed_at', 'deal_value']
    list_filter = ['outcome']
```

- [ ] **Step 7: Create superuser and verify admin works**

```bash
python manage.py createsuperuser
# email: admin@salescatalyst.com  password: admin123
python manage.py runserver
# Open http://localhost:8000/admin/ — verify all models appear
```

---

## Task 13: Full test suite pass

- [ ] **Step 1: Run all backend tests**

```bash
cd BE && source venv/bin/activate
pytest -v --tb=short
```

Expected: All tests pass. Minimum passing tests: 17 (across all app test files).

- [ ] **Step 2: Start the Django dev server and verify it runs**

```bash
python manage.py runserver
```

Expected: `Starting development server at http://127.0.0.1:8000/` with no errors.

- [ ] **Step 3: Verify login endpoint works with curl**

```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@salescatalyst.com","password":"admin123"}' | python -m json.tool
```

Expected: JSON response with `access`, `refresh`, and `user` keys.

---

## Task 14: FE — Install packages + Tailwind v4 setup

**Files:**
- Modify: `FE/package.json`
- Modify: `FE/vite.config.js`
- Modify: `FE/src/index.css`

- [ ] **Step 1: Install frontend dependencies**

```bash
cd FE
npm install react-router-dom@6 @tanstack/react-query@5 axios
npm install -D tailwindcss@4 @tailwindcss/vite
```

- [ ] **Step 2: Update FE/vite.config.js to add Tailwind plugin**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Replace FE/src/index.css with Tailwind v4 import**

```css
@import "tailwindcss";
```

- [ ] **Step 4: Verify dev server starts without errors**

```bash
npm run dev
```

Expected: `Local: http://localhost:5173/` — page loads (still shows default Vite content).

---

## Task 15: FE — Axios instance + Auth API

**Files:**
- Create: `FE/src/api/axios.js`
- Create: `FE/src/api/auth.js`

- [ ] **Step 1: Write FE/src/api/axios.js**

```js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401, try refreshing once then redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        const { data } = await axios.post('/api/auth/refresh/', { refresh })
        localStorage.setItem('access_token', data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return api(originalRequest)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 2: Write FE/src/api/auth.js**

```js
import api from './axios'

export async function login(email, password) {
  const { data } = await api.post('/auth/login/', { email, password })
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  return data.user
}

export async function logout() {
  const refresh = localStorage.getItem('refresh_token')
  try {
    await api.post('/auth/logout/', { refresh })
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
}

export async function getMe() {
  const { data } = await api.get('/auth/me/')
  return data
}
```

---

## Task 16: FE — AuthContext

**Files:**
- Create: `FE/src/contexts/AuthContext.jsx`

- [ ] **Step 1: Write FE/src/contexts/AuthContext.jsx**

```jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getMe, login as apiLogin, logout as apiLogout } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const userData = await apiLogin(email, password)
    setUser(userData)
    return userData
  }, [])

  const logout = useCallback(async () => {
    await apiLogout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
```

---

## Task 17: FE — Login page

**Files:**
- Create: `FE/src/pages/LoginPage.jsx`

- [ ] **Step 1: Write FE/src/pages/LoginPage.jsx**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid email or password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">SalesCatalyst</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to your account</p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold rounded-lg px-4 py-2 text-sm transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

---

## Task 18: FE — App routing + PrivateRoute + placeholder pages

**Files:**
- Create: `FE/src/components/layout/PrivateRoute.jsx`
- Create: `FE/src/components/layout/Navbar.jsx`
- Create: `FE/src/pages/DashboardPage.jsx`
- Create: `FE/src/pages/NewCampaignPage.jsx`
- Create: `FE/src/pages/CampaignLeadsPage.jsx`
- Create: `FE/src/pages/LeadDetailPage.jsx`
- Create: `FE/src/pages/ProductsPage.jsx`
- Create: `FE/src/pages/AIDraftsPage.jsx`
- Modify: `FE/src/App.jsx`
- Modify: `FE/src/main.jsx`

- [ ] **Step 1: Write FE/src/components/layout/PrivateRoute.jsx**

```jsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function PrivateRoute() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    )
  }
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}
```

- [ ] **Step 2: Write FE/src/components/layout/Navbar.jsx**

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
      <Link to="/campaigns/new" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Campaigns</Link>
      <Link to="/products" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Products</Link>
      <Link to="/ai-drafts" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">AI Drafts</Link>
      <div className="ml-auto flex items-center gap-3">
        <span className="text-slate-400 text-sm">{user?.email}</span>
        <button
          onClick={handleLogout}
          className="text-slate-400 hover:text-white text-sm transition-colors"
        >
          Logout
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 3: Write placeholder pages (all 6)**

`FE/src/pages/DashboardPage.jsx`:
```jsx
export default function DashboardPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Dashboard</h1><p className="text-gray-500 mt-2">Coming in Phase 3.</p></div>
}
```

`FE/src/pages/NewCampaignPage.jsx`:
```jsx
export default function NewCampaignPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">New Campaign</h1><p className="text-gray-500 mt-2">Coming in Phase 2.</p></div>
}
```

`FE/src/pages/CampaignLeadsPage.jsx`:
```jsx
export default function CampaignLeadsPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Campaign Leads</h1><p className="text-gray-500 mt-2">Coming in Phase 3.</p></div>
}
```

`FE/src/pages/LeadDetailPage.jsx`:
```jsx
export default function LeadDetailPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Lead Detail</h1><p className="text-gray-500 mt-2">Coming in Phase 3.</p></div>
}
```

`FE/src/pages/ProductsPage.jsx`:
```jsx
export default function ProductsPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Products</h1><p className="text-gray-500 mt-2">Coming in Phase 2.</p></div>
}
```

`FE/src/pages/AIDraftsPage.jsx`:
```jsx
export default function AIDraftsPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">AI Draft Queue</h1><p className="text-gray-500 mt-2">Coming in Phase 5.</p></div>
}
```

- [ ] **Step 4: Write FE/src/App.jsx**

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/layout/PrivateRoute'
import Navbar from './components/layout/Navbar'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
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

- [ ] **Step 5: Write FE/src/main.jsx**

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
)
```

- [ ] **Step 6: End-to-end smoke test**

With Django running on :8000 and Vite on :5173:

1. Open `http://localhost:5173`
2. Should redirect to `/login` (PrivateRoute working)
3. Enter `admin@salescatalyst.com` / `admin123`
4. Should redirect to `/dashboard` showing "Dashboard — Coming in Phase 3"
5. Navbar shows email + all links
6. Click Logout → redirects back to `/login`

Expected: All 6 steps pass without console errors.

---

## Self-Review Checklist (run before handing off)

- [x] **Spec coverage:** TimestampedModel ✓, all 10 models ✓, JWT auth ✓, CORS ✓, login page ✓, routing ✓, PrivateRoute ✓, admin ✓
- [x] **No placeholders:** All steps have complete code or explicit commands with expected output
- [x] **Type consistency:** `AUTH_USER_MODEL = 'accounts.User'` set in base.py → all FK references use `settings.AUTH_USER_MODEL` consistently. `TimestampedModel` imported from `common.models` in all app models.
- [x] **Test coverage:** Every model has a test file. Auth views have full test coverage. All tests run with `pytest -v`.

---

## Phase 1 Complete — Verification

Run this final check to confirm everything is working:

```bash
# Terminal 1 — Backend
cd BE && source venv/bin/activate && python manage.py runserver

# Terminal 2 — Background worker (optional at this phase)
cd BE && source venv/bin/activate && python manage.py qcluster

# Terminal 3 — Frontend
cd FE && npm run dev

# Terminal 4 — Tests
cd BE && source venv/bin/activate && pytest -v
```

**Phase 1 done when:**
- All backend tests pass
- `http://localhost:8000/admin/` shows all 10 model types
- `http://localhost:5173/login` renders the login form
- Login with admin credentials → lands on Dashboard page
- Logout redirects back to login

**Next:** Phase 2 plan (`2026-04-27-phase2-lead-discovery.md`) covers the campaign search form, Volza API integration, LUSHA enrichment, and the products CRUD with brochure upload.
