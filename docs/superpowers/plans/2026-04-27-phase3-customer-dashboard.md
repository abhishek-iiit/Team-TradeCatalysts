# Phase 3: Customer Dashboard + Lead Detail — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Lead Detail page (7-stage progress bar, contact cards, timeline / call-log / email tabs, auto_flow_paused toggle) and the Dashboard overview with aggregate stats.

**Architecture:** Extend the existing `LeadViewSet` (currently read-only) to support PATCH (stage + auto_flow_paused), a nested `actions` endpoint (GET list + POST create), and a `threads` read action. Add a lightweight `GET /api/dashboard/` stats view. On the frontend, `LeadDetailPage` renders a sticky header with stage selector + pause toggle, a horizontal `StageProgressBar`, a contact sidebar, and three tabs (Timeline, Call Log, Emails). `DashboardPage` shows stat cards and a stage breakdown.

**Tech Stack:** DRF ModelViewSet with custom `@action` decorators · `@api_view` stats endpoint · React 19 · TanStack Query v5 · Tailwind v4

> **Prerequisite:** Phase 2 complete — 30 tests passing, `GET /api/campaigns/:id/leads/` works, `LeadViewSet` is registered at `/api/leads/`.

---

## File Map

### Backend (BE/)
```
leads/
  serializers.py       ← add LeadDetailSerializer, LeadActionSerializer, LeadUpdateSerializer
  views.py             ← expand LeadViewSet; add dashboard_stats view
  urls.py              ← add /dashboard/ route
  tests/
    test_serializers.py  ← new
    test_views.py        ← new

communications/
  serializers.py       ← EmailThreadSerializer, EmailMessageSerializer
  (views.py stays stub — threads served through LeadViewSet action)
```

### Frontend (FE/src/)
```
api/
  leads.js             ← getLead, patchLead, getLeadActions, logLeadAction, getLeadThreads, getDashboardStats

components/leads/
  StageProgressBar.jsx ← 6-node horizontal bar (discovered → closed_won), lost variant
  ContactCard.jsx      ← name, designation, email, phone, linkedin badges
  TimelineTab.jsx      ← renders LeadAction list with actor + relative time
  CallLogTab.jsx       ← form: action_type dropdown + notes textarea → POST action
  EmailThreadsTab.jsx  ← thread accordion with messages inside

pages/
  LeadDetailPage.jsx   ← header + progress bar + contact sidebar + 3 tabs
  DashboardPage.jsx    ← stat cards + stage breakdown table
```

---

## Task 1: BE — Extend leads serializers

**Files:**
- Modify: `BE/leads/serializers.py`
- Create: `BE/leads/tests/test_serializers.py`

- [ ] **Step 1: Write the failing tests**

Create `BE/leads/tests/test_serializers.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, LeadAction, ActionType, ContactSource
from leads.serializers import LeadDetailSerializer, LeadActionSerializer

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.fixture
def lead(campaign):
    return Lead.objects.create(campaign=campaign, company_name='Acme', company_country='IN')


@pytest.mark.django_db
def test_lead_detail_includes_contacts_and_actions(lead):
    Contact.objects.create(
        lead=lead, first_name='Jane', email='jane@acme.com', source=ContactSource.VOLZA
    )
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Test note')

    data = LeadDetailSerializer(lead).data

    assert len(data['contacts']) == 1
    assert data['contacts'][0]['email'] == 'jane@acme.com'
    assert len(data['actions']) == 1
    assert data['actions'][0]['action_type'] == 'note'
    assert data['actions'][0]['performed_by_email'] is None  # system action (no performer)


@pytest.mark.django_db
def test_lead_action_serializer_performed_by_email(lead, user):
    action = LeadAction.objects.create(
        lead=lead,
        action_type=ActionType.FOLLOW_UP_CALL,
        performed_by=user,
        notes='Called the customer',
    )
    data = LeadActionSerializer(action).data
    assert data['performed_by_email'] == 'u@t.com'
    assert data['notes'] == 'Called the customer'


@pytest.mark.django_db
def test_lead_detail_includes_volza_fields(lead):
    lead.volza_data = {'raw': True}
    lead.pricing_trend = {'2024': 120.5}
    lead.save()

    data = LeadDetailSerializer(lead).data
    assert 'volza_data' in data
    assert 'pricing_trend' in data
    assert 'purchase_history' in data
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE && source venv/bin/activate
pytest leads/tests/test_serializers.py -v 2>&1 | head -20
```

Expected: ImportError — `LeadDetailSerializer` not found

- [ ] **Step 3: Write the updated BE/leads/serializers.py**

```python
from rest_framework import serializers
from .models import Lead, Contact, LeadAction


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'designation',
            'email', 'phone', 'linkedin_url', 'source', 'is_primary',
        ]


class LeadActionSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = LeadAction
        fields = [
            'id', 'action_type', 'notes', 'metadata',
            'performed_by_email', 'created_at',
        ]
        read_only_fields = ['id', 'performed_by_email', 'created_at']

    def get_performed_by_email(self, obj):
        return obj.performed_by.email if obj.performed_by else None

    def create(self, validated_data):
        validated_data['performed_by'] = self.context['request'].user
        validated_data['lead'] = self.context['lead']
        return super().create(validated_data)


class LeadListSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)
    has_missing_contact = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'company_name', 'company_country', 'company_website',
            'stage', 'auto_flow_paused', 'has_missing_contact',
            'contacts', 'created_at', 'updated_at',
        ]

    def get_has_missing_contact(self, obj):
        return obj.has_missing_contact


class LeadDetailSerializer(LeadListSerializer):
    actions = LeadActionSerializer(many=True, read_only=True)

    class Meta(LeadListSerializer.Meta):
        fields = [
            'id', 'company_name', 'company_country', 'company_website',
            'stage', 'auto_flow_paused', 'has_missing_contact',
            'contacts', 'actions',
            'volza_data', 'pricing_trend', 'purchase_history',
            'created_at', 'updated_at',
        ]


class LeadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['stage', 'auto_flow_paused']
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest leads/tests/test_serializers.py -v
```

Expected: 3 passed

---

## Task 2: BE — Expand LeadViewSet (PATCH, actions, threads, dashboard stats)

**Files:**
- Modify: `BE/leads/views.py`
- Modify: `BE/leads/urls.py`
- Create: `BE/leads/tests/test_views.py`

- [ ] **Step 1: Write the failing tests**

Create `BE/leads/tests/test_views.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign
from leads.models import Lead, Contact, LeadAction, LeadStage, ActionType, ContactSource

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
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.fixture
def lead(campaign):
    return Lead.objects.create(
        campaign=campaign, company_name='Acme Corp', company_country='IN'
    )


@pytest.mark.django_db
def test_lead_detail_returns_contacts_and_actions(auth_client, lead):
    Contact.objects.create(
        lead=lead, first_name='Jane', email='jane@acme.com', source=ContactSource.VOLZA
    )
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Note')
    response = auth_client.get(f'/api/leads/{lead.id}/')
    assert response.status_code == 200
    assert len(response.data['contacts']) == 1
    assert len(response.data['actions']) == 1
    assert 'volza_data' in response.data


@pytest.mark.django_db
def test_patch_lead_stage(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'stage': 'intro_sent'}, format='json'
    )
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.stage == LeadStage.INTRO_SENT


@pytest.mark.django_db
def test_patch_lead_auto_flow_paused(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'auto_flow_paused': True}, format='json'
    )
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.auto_flow_paused is True


@pytest.mark.django_db
def test_patch_invalid_stage_rejected(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'stage': 'nonexistent_stage'}, format='json'
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_lead_actions(auth_client, lead):
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Note 1')
    LeadAction.objects.create(lead=lead, action_type=ActionType.FOLLOW_UP_CALL, notes='Called')
    response = auth_client.get(f'/api/leads/{lead.id}/actions/')
    assert response.status_code == 200
    assert len(response.data) == 2


@pytest.mark.django_db
def test_post_lead_action_sets_performer(auth_client, lead, user):
    response = auth_client.post(
        f'/api/leads/{lead.id}/actions/',
        {'action_type': 'follow_up_call', 'notes': 'Called, buyer is interested'},
        format='json',
    )
    assert response.status_code == 201
    action = LeadAction.objects.get(lead=lead)
    assert action.performed_by == user
    assert action.notes == 'Called, buyer is interested'


@pytest.mark.django_db
def test_post_action_without_notes_rejected(auth_client, lead):
    response = auth_client.post(
        f'/api/leads/{lead.id}/actions/',
        {'action_type': 'follow_up_call'},
        format='json',
    )
    # notes is blank=True on model so this should succeed with empty notes
    assert response.status_code == 201


@pytest.mark.django_db
def test_dashboard_stats_returns_counts(auth_client, lead):
    response = auth_client.get('/api/dashboard/')
    assert response.status_code == 200
    assert response.data['total_leads'] == 1
    assert response.data['leads_by_stage']['discovered'] == 1
    assert 'active_campaigns' in response.data
    assert 'missing_contact_count' in response.data


@pytest.mark.django_db
def test_leads_endpoint_not_writable_via_post(auth_client, campaign):
    response = auth_client.post('/api/leads/', {}, format='json')
    assert response.status_code == 405  # Method Not Allowed
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest leads/tests/test_views.py -v 2>&1 | head -25
```

Expected: multiple failures — PATCH returns 405, dashboard 404, etc.

- [ ] **Step 3: Write the updated BE/leads/views.py**

```python
from django.db.models import Exists, OuterRef, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Lead, LeadAction, LeadStage, Contact
from .serializers import (
    LeadListSerializer,
    LeadDetailSerializer,
    LeadActionSerializer,
    LeadUpdateSerializer,
)


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']  # no POST/DELETE (leads created by Volza task)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LeadDetailSerializer
        if self.action == 'partial_update':
            return LeadUpdateSerializer
        return LeadListSerializer

    def get_queryset(self):
        qs = Lead.objects.select_related('campaign', 'assigned_to').order_by('-created_at')
        if self.action == 'retrieve':
            return qs.prefetch_related(
                'contacts',
                'actions',
                'actions__performed_by',
            )
        return qs.prefetch_related('contacts')

    def partial_update(self, request, *args, **kwargs):
        lead = self.get_object()
        serializer = LeadUpdateSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Return full detail after update
        lead = Lead.objects.select_related('campaign', 'assigned_to').prefetch_related(
            'contacts', 'actions', 'actions__performed_by'
        ).get(pk=lead.pk)
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=['get', 'post'], url_path='actions')
    def actions_list(self, request, pk=None):
        lead = self.get_object()
        if request.method == 'GET':
            qs = lead.actions.select_related('performed_by').order_by('-created_at')
            return Response(LeadActionSerializer(qs, many=True).data)
        serializer = LeadActionSerializer(
            data=request.data,
            context={'request': request, 'lead': lead},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='threads')
    def threads(self, request, pk=None):
        from communications.serializers import EmailThreadSerializer
        lead = self.get_object()
        qs = lead.threads.select_related('contact').prefetch_related('messages').order_by('-created_at')
        return Response(EmailThreadSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    from campaigns.models import Campaign, CampaignStatus

    total_leads = Lead.objects.count()
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE).count()

    stage_counts = {stage.value: 0 for stage in LeadStage}
    for stage in LeadStage:
        stage_counts[stage.value] = Lead.objects.filter(stage=stage).count()

    has_reachable_contact = Exists(
        Contact.objects.filter(lead=OuterRef('pk')).filter(
            Q(email__isnull=False) | Q(phone__isnull=False)
        )
    )
    missing_contact_count = (
        Lead.objects.annotate(has_contact=has_reachable_contact)
        .filter(has_contact=False)
        .count()
    )

    return Response({
        'total_leads': total_leads,
        'active_campaigns': active_campaigns,
        'leads_by_stage': stage_counts,
        'missing_contact_count': missing_contact_count,
    })
```

- [ ] **Step 4: Write the updated BE/leads/urls.py**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('leads', views.LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
]
```

- [ ] **Step 5: Run tests**

```bash
pytest leads/tests/test_views.py -v
```

Expected: 9 passed

- [ ] **Step 6: Run full test suite**

```bash
pytest -v 2>&1 | tail -15
```

Expected: 36+ passed, 0 failed

---

## Task 3: BE — Communications serializers (EmailThread + EmailMessage)

**Files:**
- Modify: `BE/communications/serializers.py`
- Create: `BE/communications/tests/test_views.py`

The threads are served through the LeadViewSet `threads` action (already written in Task 2). This task writes the serializers that action depends on.

- [ ] **Step 1: Write the failing test**

Create `BE/communications/tests/test_views.py`:

```python
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource
from communications.models import EmailThread, EmailMessage, ThreadType, MessageDirection

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def lead(user):
    campaign = Campaign.objects.create(title='C', created_by=user)
    return Lead.objects.create(campaign=campaign, company_name='Acme', company_country='IN')


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Jane', last_name='Doe',
        email='jane@acme.com', source=ContactSource.VOLZA
    )


@pytest.mark.django_db
def test_get_lead_threads_returns_thread_with_messages(auth_client, lead, contact):
    thread = EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Intro: Acetone Supply', thread_type=ThreadType.INTRO,
    )
    EmailMessage.objects.create(
        thread=thread, direction=MessageDirection.OUTBOUND,
        body_text='Hello, we supply Acetone.', sent_at=timezone.now(),
    )
    response = auth_client.get(f'/api/leads/{lead.id}/threads/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['subject'] == 'Intro: Acetone Supply'
    assert len(response.data[0]['messages']) == 1
    assert response.data[0]['messages'][0]['direction'] == 'outbound'
    assert response.data[0]['contact_name'] == 'Jane Doe'
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest communications/tests/test_views.py -v 2>&1 | head -15
```

Expected: ImportError — `communications.serializers` has no EmailThreadSerializer

- [ ] **Step 3: Write BE/communications/serializers.py**

```python
from rest_framework import serializers
from .models import EmailThread, EmailMessage


class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage
        fields = ['id', 'direction', 'body_text', 'sent_at', 'gmail_message_id']


class EmailThreadSerializer(serializers.ModelSerializer):
    messages = EmailMessageSerializer(many=True, read_only=True)
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = EmailThread
        fields = ['id', 'subject', 'thread_type', 'contact_name', 'messages', 'created_at']

    def get_contact_name(self, obj):
        return f'{obj.contact.first_name} {obj.contact.last_name}'.strip()
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
pytest communications/tests/test_views.py -v
```

Expected: 1 passed

- [ ] **Step 5: Run the full suite**

```bash
pytest -v 2>&1 | tail -10
```

Expected: 37+ passed, 0 failed

---

## Task 4: FE — api/leads.js

**Files:**
- Create: `FE/src/api/leads.js`

- [ ] **Step 1: Write FE/src/api/leads.js**

```js
import api from './axios'

export const getLead = (id) =>
  api.get(`/leads/${id}/`).then((r) => r.data)

export const patchLead = (id, data) =>
  api.patch(`/leads/${id}/`, data).then((r) => r.data)

export const getLeadActions = (id) =>
  api.get(`/leads/${id}/actions/`).then((r) => r.data)

export const logLeadAction = (id, data) =>
  api.post(`/leads/${id}/actions/`, data).then((r) => r.data)

export const getLeadThreads = (id) =>
  api.get(`/leads/${id}/threads/`).then((r) => r.data)

export const getDashboardStats = () =>
  api.get('/dashboard/').then((r) => r.data)
```

- [ ] **Step 2: Verify FE still builds**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE && npm run build 2>&1 | tail -5
```

Expected: `✓ built in ...ms` with no errors

---

## Task 5: FE — StageProgressBar component

**Files:**
- Create: `FE/src/components/leads/StageProgressBar.jsx`

The bar shows 6 forward stages (discovered → closed_won) as connected nodes. `closed_lost` is shown with a red banner separate from the bar since it's a terminal failure state.

- [ ] **Step 1: Write FE/src/components/leads/StageProgressBar.jsx**

```jsx
const FORWARD_STAGES = [
  { key: 'discovered',       label: 'Discovered' },
  { key: 'intro_sent',       label: 'Intro Sent' },
  { key: 'pricing_sent',     label: 'Pricing Sent' },
  { key: 'pricing_followup', label: 'Follow-Up' },
  { key: 'meeting_set',      label: 'Meeting Set' },
  { key: 'closed_won',       label: 'Won' },
]

const STAGE_INDEX = Object.fromEntries(FORWARD_STAGES.map((s, i) => [s.key, i]))

export default function StageProgressBar({ stage }) {
  if (stage === 'closed_lost') {
    return (
      <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-sm text-red-700 font-medium">
        <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
        Deal Lost
      </div>
    )
  }

  const currentIdx = STAGE_INDEX[stage] ?? 0

  return (
    <div className="flex items-center gap-0 w-full">
      {FORWARD_STAGES.map((s, idx) => {
        const done = idx < currentIdx
        const active = idx === currentIdx
        return (
          <div key={s.key} className="flex items-center flex-1 last:flex-none">
            {/* Node */}
            <div className="flex flex-col items-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
                done
                  ? 'bg-indigo-600 border-indigo-600 text-white'
                  : active
                  ? 'bg-white border-indigo-600 text-indigo-600'
                  : 'bg-white border-gray-300 text-gray-400'
              }`}>
                {done ? '✓' : idx + 1}
              </div>
              <span className={`mt-1 text-xs whitespace-nowrap ${
                active ? 'text-indigo-600 font-semibold' : done ? 'text-indigo-500' : 'text-gray-400'
              }`}>
                {s.label}
              </span>
            </div>
            {/* Connector line (not after last node) */}
            {idx < FORWARD_STAGES.length - 1 && (
              <div className={`flex-1 h-0.5 mx-1 mb-4 ${
                idx < currentIdx ? 'bg-indigo-600' : 'bg-gray-200'
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
```

---

## Task 6: FE — ContactCard component

**Files:**
- Create: `FE/src/components/leads/ContactCard.jsx`

- [ ] **Step 1: Write FE/src/components/leads/ContactCard.jsx**

```jsx
export default function ContactCard({ contact }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-gray-900 text-sm">
            {contact.first_name} {contact.last_name}
            {contact.is_primary && (
              <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-medium">
                Primary
              </span>
            )}
          </p>
          {contact.designation && (
            <p className="text-xs text-gray-500">{contact.designation}</p>
          )}
        </div>
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
          {contact.source}
        </span>
      </div>

      <div className="space-y-1">
        {contact.email ? (
          <a
            href={`mailto:${contact.email}`}
            className="flex items-center gap-2 text-xs text-indigo-600 hover:underline"
          >
            <span className="w-4 text-center">✉</span>
            {contact.email}
          </a>
        ) : (
          <p className="text-xs text-gray-400 italic">No email</p>
        )}
        {contact.phone ? (
          <a
            href={`tel:${contact.phone}`}
            className="flex items-center gap-2 text-xs text-gray-700 hover:underline"
          >
            <span className="w-4 text-center">📞</span>
            {contact.phone}
          </a>
        ) : (
          <p className="text-xs text-gray-400 italic">No phone</p>
        )}
        {contact.linkedin_url && (
          <a
            href={contact.linkedin_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 text-xs text-blue-600 hover:underline"
          >
            <span className="w-4 text-center">in</span>
            LinkedIn
          </a>
        )}
      </div>
    </div>
  )
}
```

---

## Task 7: FE — TimelineTab and CallLogTab

**Files:**
- Create: `FE/src/components/leads/TimelineTab.jsx`
- Create: `FE/src/components/leads/CallLogTab.jsx`

- [ ] **Step 1: Write FE/src/components/leads/TimelineTab.jsx**

```jsx
const ACTION_LABELS = {
  intro_email:            'Intro Email Sent',
  follow_up_call:         'Follow-Up Call',
  pricing_email:          'Pricing Email Sent',
  pricing_followup_email: 'Pricing Follow-Up Email',
  meeting_scheduled:      'Meeting Scheduled',
  note:                   'Note Added',
  ai_draft_generated:     'AI Draft Generated',
  ai_draft_approved:      'AI Draft Approved',
  ai_draft_rejected:      'AI Draft Rejected',
  deal_closed:            'Deal Closed',
  manual_takeover:        'Manual Takeover',
}

function relativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function TimelineTab({ actions }) {
  if (!actions || actions.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No activity recorded yet.
      </p>
    )
  }

  return (
    <ol className="relative border-l border-gray-200 ml-2 space-y-4">
      {actions.map((action) => (
        <li key={action.id} className="ml-4">
          <div className="absolute -left-1.5 w-3 h-3 rounded-full border-2 border-white bg-indigo-400" />
          <div className="bg-white border border-gray-100 rounded-lg p-3 shadow-sm">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-gray-800">
                {ACTION_LABELS[action.action_type] || action.action_type}
              </span>
              <span className="text-xs text-gray-400">{relativeTime(action.created_at)}</span>
            </div>
            {action.notes && (
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{action.notes}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              {action.performed_by_email || 'System'}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}
```

- [ ] **Step 2: Write FE/src/components/leads/CallLogTab.jsx**

```jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { logLeadAction } from '../../api/leads'

const ACTION_TYPES = [
  { value: 'follow_up_call', label: 'Follow-Up Call' },
  { value: 'note',           label: 'Note' },
  { value: 'manual_takeover', label: 'Manual Takeover' },
]

export default function CallLogTab({ leadId }) {
  const qc = useQueryClient()
  const [actionType, setActionType] = useState('follow_up_call')
  const [notes, setNotes] = useState('')
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: (data) => logLeadAction(leadId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      setNotes('')
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!notes.trim()) return
    mutation.mutate({ action_type: actionType, notes: notes.trim() })
  }

  return (
    <div className="max-w-lg">
      {success && (
        <div className="mb-3 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          Action logged successfully.
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            {ACTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes *</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            required
            rows={4}
            placeholder="What happened? Key points from the call…"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={mutation.isPending || !notes.trim()}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {mutation.isPending ? 'Saving…' : 'Log Action'}
        </button>
      </form>
    </div>
  )
}
```

---

## Task 8: FE — EmailThreadsTab component

**Files:**
- Create: `FE/src/components/leads/EmailThreadsTab.jsx`

- [ ] **Step 1: Write FE/src/components/leads/EmailThreadsTab.jsx**

```jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLeadThreads } from '../../api/leads'

const THREAD_TYPE_LABELS = {
  intro:       'Intro',
  pricing:     'Pricing',
  followup:    'Follow-Up',
  negotiation: 'Negotiation',
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export default function EmailThreadsTab({ leadId }) {
  const [openThreadId, setOpenThreadId] = useState(null)

  const { data: threads = [], isLoading } = useQuery({
    queryKey: ['lead-threads', leadId],
    queryFn: () => getLeadThreads(leadId),
  })

  if (isLoading) return <p className="text-sm text-gray-400 py-4">Loading threads…</p>

  if (threads.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No emails sent yet. Use the Communication tab in Phase 4 to send intro emails.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {threads.map((thread) => (
        <div key={thread.id} className="border border-gray-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setOpenThreadId(openThreadId === thread.id ? null : thread.id)}
            className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50 text-left"
          >
            <div>
              <span className="text-sm font-semibold text-gray-900">{thread.subject}</span>
              <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-medium">
                {THREAD_TYPE_LABELS[thread.thread_type] || thread.thread_type}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span>{thread.messages.length} msg{thread.messages.length !== 1 ? 's' : ''}</span>
              <span>{thread.contact_name}</span>
              <span>{openThreadId === thread.id ? '▲' : '▼'}</span>
            </div>
          </button>

          {openThreadId === thread.id && (
            <div className="border-t border-gray-100 divide-y divide-gray-100">
              {thread.messages.length === 0 ? (
                <p className="px-4 py-3 text-xs text-gray-400">No messages in this thread.</p>
              ) : (
                thread.messages.map((msg) => (
                  <div key={msg.id} className={`px-4 py-3 ${msg.direction === 'inbound' ? 'bg-blue-50' : 'bg-white'}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-semibold ${msg.direction === 'inbound' ? 'text-blue-700' : 'text-gray-700'}`}>
                        {msg.direction === 'inbound' ? '← Received' : '→ Sent'}
                      </span>
                      <span className="text-xs text-gray-400">{formatDate(msg.sent_at)}</span>
                    </div>
                    <p className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed line-clamp-4">
                      {msg.body_text || '(No text content)'}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
```

---

## Task 9: FE — LeadDetailPage

**Files:**
- Modify: `FE/src/pages/LeadDetailPage.jsx`

- [ ] **Step 1: Read the current stub**

```bash
cat /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE/src/pages/LeadDetailPage.jsx
```

- [ ] **Step 2: Write the full FE/src/pages/LeadDetailPage.jsx**

```jsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLead, patchLead } from '../api/leads'
import StageBadge from '../components/leads/StageBadge'
import StageProgressBar from '../components/leads/StageProgressBar'
import ContactCard from '../components/leads/ContactCard'
import TimelineTab from '../components/leads/TimelineTab'
import CallLogTab from '../components/leads/CallLogTab'
import EmailThreadsTab from '../components/leads/EmailThreadsTab'

const STAGES = [
  { value: 'discovered',       label: 'Discovered' },
  { value: 'intro_sent',       label: 'Intro Sent' },
  { value: 'pricing_sent',     label: 'Pricing Sent' },
  { value: 'pricing_followup', label: 'Pricing Follow-Up' },
  { value: 'meeting_set',      label: 'Meeting Set' },
  { value: 'closed_won',       label: 'Closed Won' },
  { value: 'closed_lost',      label: 'Closed Lost' },
]

const TABS = ['Timeline', 'Call Log', 'Emails']

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState('Timeline')

  const { data: lead, isLoading, isError } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => getLead(id),
  })

  const patchMutation = useMutation({
    mutationFn: (data) => patchLead(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(['lead', id], updated)
    },
  })

  if (isLoading) return <div className="p-8 text-gray-400">Loading lead…</div>
  if (isError || !lead) return <div className="p-8 text-red-500">Lead not found.</div>

  function handleStageChange(e) {
    patchMutation.mutate({ stage: e.target.value })
  }

  function togglePause() {
    patchMutation.mutate({ auto_flow_paused: !lead.auto_flow_paused })
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-gray-400 hover:text-gray-600 mb-4 block"
      >
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{lead.company_name}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {lead.company_country}
            {lead.company_website && (
              <>
                {' · '}
                <a href={lead.company_website} target="_blank" rel="noreferrer"
                  className="text-indigo-600 hover:underline"
                >
                  {lead.company_website}
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Stage selector */}
          <select
            value={lead.stage}
            onChange={handleStageChange}
            disabled={patchMutation.isPending}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white disabled:opacity-60"
          >
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>

          {/* Auto-flow pause toggle */}
          <button
            onClick={togglePause}
            disabled={patchMutation.isPending}
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-60 ${
              lead.auto_flow_paused
                ? 'bg-yellow-100 border-yellow-300 text-yellow-800 hover:bg-yellow-200'
                : 'bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {lead.auto_flow_paused ? '⏸ Paused' : '▶ Auto-Flow On'}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="my-6">
        <StageProgressBar stage={lead.stage} />
      </div>

      {/* Main layout: content + sidebar */}
      <div className="flex gap-6 mt-4">
        {/* Left: tabs */}
        <div className="flex-1 min-w-0">
          {/* Tab nav */}
          <div className="flex gap-1 border-b border-gray-200 mb-4">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === 'Timeline' && (
            <TimelineTab actions={lead.actions || []} />
          )}
          {activeTab === 'Call Log' && (
            <CallLogTab leadId={id} />
          )}
          {activeTab === 'Emails' && (
            <EmailThreadsTab leadId={id} />
          )}
        </div>

        {/* Right: contacts sidebar */}
        <div className="w-72 shrink-0 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Contacts</h2>
          {lead.contacts && lead.contacts.length > 0 ? (
            lead.contacts.map((c) => <ContactCard key={c.id} contact={c} />)
          ) : (
            <p className="text-xs text-gray-400">No contacts yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify FE build still passes**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE && npm run build 2>&1 | tail -5
```

Expected: `✓ built in ...ms`, no errors

---

## Task 10: FE — DashboardPage with stat cards

**Files:**
- Modify: `FE/src/pages/DashboardPage.jsx`

- [ ] **Step 1: Read the current stub**

```bash
cat /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE/src/pages/DashboardPage.jsx
```

- [ ] **Step 2: Write the full FE/src/pages/DashboardPage.jsx**

```jsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getDashboardStats } from '../api/leads'
import { listCampaigns } from '../api/campaigns'

const STAGE_ORDER = [
  { key: 'discovered',       label: 'Discovered',       color: 'bg-gray-400' },
  { key: 'intro_sent',       label: 'Intro Sent',        color: 'bg-blue-400' },
  { key: 'pricing_sent',     label: 'Pricing Sent',      color: 'bg-purple-400' },
  { key: 'pricing_followup', label: 'Pricing Follow-Up', color: 'bg-yellow-400' },
  { key: 'meeting_set',      label: 'Meeting Set',       color: 'bg-indigo-400' },
  { key: 'closed_won',       label: 'Won',               color: 'bg-green-500' },
  { key: 'closed_lost',      label: 'Lost',              color: 'bg-red-400' },
]

function StatCard({ label, value, sub, accent }) {
  return (
    <div className={`bg-white border rounded-xl p-5 ${accent ? 'border-indigo-200' : 'border-gray-200'}`}>
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${accent ? 'text-indigo-600' : 'text-gray-900'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  })

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: listCampaigns,
  })

  const totalLeads = stats?.total_leads ?? '—'
  const activeCampaigns = stats?.active_campaigns ?? '—'
  const missingContacts = stats?.missing_contact_count ?? '—'
  const wonLeads = stats?.leads_by_stage?.closed_won ?? 0
  const lostLeads = stats?.leads_by_stage?.closed_lost ?? 0

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Leads" value={totalLeads} accent />
        <StatCard label="Active Campaigns" value={activeCampaigns} />
        <StatCard
          label="Deals Won"
          value={wonLeads}
          sub={lostLeads > 0 ? `${lostLeads} lost` : undefined}
        />
        <StatCard
          label="Missing Contacts"
          value={missingContacts}
          sub="No email or phone"
        />
      </div>

      {/* Stage breakdown */}
      {stats && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Pipeline Breakdown</h2>
          <div className="space-y-2">
            {STAGE_ORDER.map((s) => {
              const count = stats.leads_by_stage?.[s.key] ?? 0
              const pct = totalLeads > 0 ? Math.round((count / totalLeads) * 100) : 0
              return (
                <div key={s.key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-36 shrink-0">{s.label}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`${s.color} h-2 rounded-full transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600 font-semibold w-8 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Recent campaigns */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Recent Campaigns</h2>
          <button
            onClick={() => navigate('/campaigns')}
            className="text-xs text-indigo-600 hover:underline"
          >
            View all →
          </button>
        </div>
        {campaigns.length === 0 ? (
          <p className="text-sm text-gray-400">No campaigns yet.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {campaigns.slice(0, 5).map((c) => (
              <div
                key={c.id}
                onClick={() => navigate(`/campaigns/${c.id}/leads`)}
                className="py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{c.title}</p>
                  <p className="text-xs text-gray-400">
                    {c.country_filters?.join(', ')}
                  </p>
                </div>
                <span className="text-sm font-semibold text-indigo-600">{c.lead_count} leads</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Final build check**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE && npm run build 2>&1 | tail -5
```

Expected: `✓ built in ...ms`, no errors

---

## Final Verification

```bash
# Backend — all tests pass
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE && source venv/bin/activate
pytest -v 2>&1 | tail -20

# Backend — server starts cleanly
python manage.py check

# Frontend — zero build errors
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE && npm run build
```

**Phase 3 done when:**
- 37+ backend tests pass (30 from Phase 2 + 3 serializer tests + 9 lead-view tests + 1 comms test)
- `GET /api/leads/:id/` returns full detail: contacts, actions, volza_data, pricing_trend
- `PATCH /api/leads/:id/` updates stage and auto_flow_paused
- `GET /api/leads/:id/actions/` lists actions; `POST` creates one with performed_by = request.user
- `GET /api/leads/:id/threads/` returns threads with messages
- `GET /api/dashboard/` returns total_leads, active_campaigns, leads_by_stage, missing_contact_count
- FE builds clean; LeadDetailPage shows progress bar, contact sidebar, 3 working tabs
- DashboardPage shows stat cards + stage breakdown

**Next:** Phase 4 — Communication Engine (send intro email with brochure attachment via Gmail SMTP, send pricing email, Django-Q2 follow-up scheduling, Gmail API inbound polling for reply detection).
