# Phase 5: AI Email Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Gemini 2.0 Flash AI draft generation to the email workflow — generate context-aware email drafts per lead thread, display them in a review queue, and let users approve (auto-send) or reject.

**Architecture:** `GeminiClient` wraps the google-generativeai SDK (falls back gracefully on API failure); `generate_ai_draft_task` (Django-Q2) creates `AIDraft(status=pending_review)`; `AIDraftViewSet` exposes list/approve/reject; approve calls `GmailSMTPSender.send_draft_reply` synchronously then marks `status=sent`.

**Tech Stack:** Django 5.2 + DRF, google-generativeai 0.8.4, Django-Q2, React 19 + TanStack Query v5, Tailwind v4

---

## File Structure

**Create:**
- `BE/ai_assistant/services/__init__.py`
- `BE/ai_assistant/services/gemini_client.py` — `GeminiClient` with fallback
- `BE/ai_assistant/tasks.py` — `async_task` shim + `generate_ai_draft_task`
- `BE/ai_assistant/serializers.py` — `AIDraftSerializer`
- `BE/ai_assistant/views.py` — `AIDraftViewSet` (list, approve, reject)
- `BE/ai_assistant/urls.py` — router for `AIDraftViewSet`
- `BE/ai_assistant/tests/test_tasks.py`
- `BE/ai_assistant/tests/test_views.py`
- `FE/src/api/aiDrafts.js`
- `FE/src/components/leads/GenerateDraftButton.jsx`

**Modify:**
- `BE/config/settings/base.py` — add `GEMINI_API_KEY`
- `BE/communications/services/email_sender.py` — add `send_draft_reply` method
- `BE/config/urls.py` — include `ai_assistant.urls`
- `BE/leads/views.py` — add `generate_draft` action to `LeadViewSet`
- `FE/src/api/leads.js` — add `generateDraft`
- `FE/src/pages/AIDraftsPage.jsx` — full implementation (replaces placeholder)
- `FE/src/pages/LeadDetailPage.jsx` — add `GenerateDraftButton`

---

## Task 1: Gemini Service + send_draft_reply + Settings

**Files:**
- Modify: `BE/config/settings/base.py`
- Create: `BE/ai_assistant/services/__init__.py`
- Create: `BE/ai_assistant/services/gemini_client.py`
- Modify: `BE/communications/services/email_sender.py`

- [ ] **Step 1: Add GEMINI_API_KEY to settings**

In `BE/config/settings/base.py`, add after `SENDER_COMPANY_NAME`:

```python
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
```

- [ ] **Step 2: Create `ai_assistant/services/__init__.py`** (empty file)

- [ ] **Step 3: Write the failing test for GeminiClient**

Create `BE/ai_assistant/tests/test_tasks.py` with just the import test first:

```python
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from communications.models import EmailThread
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='ai1', email='ai1@test.com', password='pass')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='AI Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Benzene', hsn_code='2902', cas_number='71-43-2',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(
        campaign=campaign, company_name='AI Buyer', company_country='JP',
        stage=LeadStage.INTRO_SENT,
    )
    campaign.products.add(product)
    return l


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Kenji', email='kenji@aibuyer.jp',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.fixture
def thread(lead, contact):
    return EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction | Benzene', thread_type='intro',
    )


@pytest.mark.django_db
@patch('ai_assistant.tasks.GeminiClient')
def test_generate_draft_creates_ai_draft_and_action(mock_client_cls, lead, thread):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.generate_draft.return_value = ('Dear Kenji, great follow-up...', 'Context: intro email')

    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task(str(lead.id), str(thread.id))

    assert AIDraft.objects.filter(lead=lead, status=DraftStatus.PENDING_REVIEW).count() == 1
    assert lead.actions.filter(action_type=ActionType.AI_DRAFT_GENERATED).count() == 1


@pytest.mark.django_db
def test_generate_draft_skips_missing_lead():
    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000001')


@pytest.mark.django_db
@patch('ai_assistant.tasks.GeminiClient')
def test_generate_draft_stores_draft_content(mock_client_cls, lead, thread):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.generate_draft.return_value = ('Specific draft content here.', 'Summary text')

    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task(str(lead.id), str(thread.id))

    draft = AIDraft.objects.get(lead=lead)
    assert draft.draft_content == 'Specific draft content here.'
    assert draft.context_summary == 'Summary text'
```

Run to confirm failure:
```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest ai_assistant/tests/test_tasks.py -v 2>&1 | tail -8
```
Expected: `ImportError` for `ai_assistant.tasks`

- [ ] **Step 4: Create `ai_assistant/services/gemini_client.py`**

```python
from django.conf import settings


class GeminiClient:
    """Wraps Gemini 2.0 Flash for context-aware email draft generation."""

    MODEL = 'gemini-2.0-flash'

    def generate_draft(self, lead, thread) -> tuple[str, str]:
        """
        Generate an email draft for the given lead + thread context.

        Returns:
            (draft_content, context_summary)
        """
        prompt = self._build_prompt(lead, thread)
        draft_content = self._call_gemini(prompt)
        context_summary = (
            f'Lead: {lead.company_name} ({lead.company_country}), '
            f'Thread: {thread.subject}, Stage: {lead.stage}'
        )
        return draft_content, context_summary

    def _call_gemini(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(self.MODEL)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return (
                'Thank you for your interest. We would be happy to discuss how we can '
                'meet your requirements. Please let us know your specific needs and '
                'we will provide a detailed proposal.\n\n'
                f'Best regards,\n{getattr(settings, "EMAIL_HOST_USER", "")}'
            )

    def _build_prompt(self, lead, thread) -> str:
        messages = list(thread.messages.order_by('sent_at')[:10])
        messages_text = '\n\n'.join(
            f"[{'Received' if m.direction == 'inbound' else 'Sent'}]\n{m.body_text[:500]}"
            for m in messages
        ) or 'No messages yet.'

        company_name = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        contact_name = thread.contact.first_name

        return (
            f'You are a B2B chemical trading sales assistant for {company_name}.\n\n'
            f'LEAD: {lead.company_name} ({lead.company_country}), stage: {lead.stage}\n'
            f'THREAD: "{thread.subject}" ({thread.thread_type})\n'
            f'CONTACT: {thread.contact.first_name} {thread.contact.last_name}\n\n'
            f'CONVERSATION:\n{messages_text}\n\n'
            f'Write a professional 2-3 paragraph follow-up email body. '
            f'Address {contact_name} by name. Move the deal toward closing. '
            f'Output ONLY the email body text, no subject line.'
        )
```

- [ ] **Step 5: Add `send_draft_reply` method to `GmailSMTPSender`**

In `BE/communications/services/email_sender.py`, append this method inside the `GmailSMTPSender` class (after `send_email`):

```python
    def send_draft_reply(self, thread, contact, draft_content: str) -> None:
        """Send an approved AI draft as a reply in an existing thread."""
        message_id = f'<{uuid.uuid4()}@salescatalyst>'

        django_email = DjangoEmailMessage(
            subject=f'Re: {thread.subject}',
            body=draft_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[contact.email],
            headers={'Message-ID': message_id},
        )
        django_email.send(fail_silently=False)

        EmailMessage.objects.create(
            thread=thread,
            direction=MessageDirection.OUTBOUND,
            body_text=draft_content,
            sent_at=timezone.now(),
            gmail_message_id=message_id,
        )
```

- [ ] **Step 6: Run existing test suite to confirm no regressions**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `62 passed`

Do NOT commit.

---

## Task 2: AI Assistant Tasks

**Files:**
- Create: `BE/ai_assistant/tasks.py`

- [ ] **Step 1: Create `ai_assistant/tasks.py`**

```python
"""
Django-Q2 background tasks for AI email draft generation.

Module-level async_task shim mirrors campaigns/tasks.py pattern for easy test patching.
"""

from ai_assistant.services.gemini_client import GeminiClient


def async_task(func_path: str, *args, **kwargs) -> None:
    from django_q.tasks import async_task as _async_task
    _async_task(func_path, *args, **kwargs)


def generate_ai_draft_task(lead_id: str, thread_id: str) -> None:
    """
    Django-Q2 task: call Gemini to generate an email draft, create AIDraft record,
    and log LeadAction(ai_draft_generated).

    Args:
        lead_id: String UUID of the Lead
        thread_id: String UUID of the EmailThread
    """
    from leads.models import Lead, LeadAction, ActionType
    from communications.models import EmailThread
    from ai_assistant.models import AIDraft, DraftStatus

    try:
        lead = (
            Lead.objects
            .select_related('campaign')
            .prefetch_related('campaign__products')
            .get(id=lead_id)
        )
        thread = (
            EmailThread.objects
            .select_related('contact')
            .prefetch_related('messages')
            .get(id=thread_id)
        )
    except (Lead.DoesNotExist, EmailThread.DoesNotExist):
        return

    client = GeminiClient()
    draft_content, context_summary = client.generate_draft(lead, thread)

    draft = AIDraft.objects.create(
        lead=lead,
        thread=thread,
        draft_content=draft_content,
        context_summary=context_summary,
        status=DraftStatus.PENDING_REVIEW,
    )

    LeadAction.objects.create(
        lead=lead,
        performed_by=None,
        action_type=ActionType.AI_DRAFT_GENERATED,
        notes=f'AI draft generated for thread: {thread.subject}',
        metadata={'draft_id': str(draft.id)},
    )
```

- [ ] **Step 2: Run the task tests**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest ai_assistant/tests/test_tasks.py -v 2>&1 | tail -10
```
Expected: `3 passed`

- [ ] **Step 3: Run full suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `65 passed`

Do NOT commit.

---

## Task 3: AIDraft API — Serializer, ViewSet, URLs

**Files:**
- Create: `BE/ai_assistant/serializers.py`
- Create: `BE/ai_assistant/views.py`
- Create: `BE/ai_assistant/urls.py`
- Create: `BE/ai_assistant/tests/test_views.py`
- Modify: `BE/config/urls.py`

- [ ] **Step 1: Write failing view tests**

Create `BE/ai_assistant/tests/test_views.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from communications.models import EmailThread
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='av1', email='av1@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='AI Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Benzene', hsn_code='2902', cas_number='71-43-2',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(
        campaign=campaign, company_name='AI Buyer', company_country='JP',
        stage=LeadStage.INTRO_SENT,
    )
    campaign.products.add(product)
    return l


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Kenji', email='kenji@aibuyer.jp',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.fixture
def thread(lead, contact):
    return EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction | Benzene', thread_type='intro',
    )


@pytest.fixture
def draft(lead, thread):
    return AIDraft.objects.create(
        lead=lead, thread=thread,
        draft_content='Test draft content.', context_summary='ctx',
    )


@pytest.mark.django_db
def test_list_pending_drafts(auth_client, draft):
    resp = auth_client.get('/api/ai-drafts/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['id'] == str(draft.id)
    assert resp.data[0]['draft_content'] == 'Test draft content.'
    assert resp.data[0]['lead_company_name'] == 'AI Buyer'


@pytest.mark.django_db
def test_list_excludes_non_pending(auth_client, draft):
    draft.status = DraftStatus.SENT
    draft.save()
    resp = auth_client.get('/api/ai-drafts/')
    assert resp.status_code == 200
    assert len(resp.data) == 0


@pytest.mark.django_db
@patch('ai_assistant.views.GmailSMTPSender')
def test_approve_draft_sends_email_and_marks_sent(mock_sender_cls, auth_client, user, draft):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/approve/')

    assert resp.status_code == 200
    draft.refresh_from_db()
    assert draft.status == DraftStatus.SENT
    assert draft.reviewed_by == user
    mock_sender.send_draft_reply.assert_called_once_with(
        draft.thread, draft.thread.contact, draft.draft_content
    )
    assert draft.lead.actions.filter(action_type=ActionType.AI_DRAFT_APPROVED).exists()


@pytest.mark.django_db
def test_approve_non_pending_returns_400(auth_client, draft):
    draft.status = DraftStatus.SENT
    draft.save()
    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/approve/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_reject_draft_marks_rejected_and_logs_action(auth_client, user, draft):
    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/reject/')

    assert resp.status_code == 200
    draft.refresh_from_db()
    assert draft.status == DraftStatus.REJECTED
    assert draft.reviewed_by == user
    assert draft.lead.actions.filter(action_type=ActionType.AI_DRAFT_REJECTED).exists()
```

Run to confirm failure:
```bash
python -m pytest ai_assistant/tests/test_views.py -v 2>&1 | tail -10
```
Expected: `404` or `ImportError` (endpoints don't exist yet)

- [ ] **Step 2: Create `ai_assistant/serializers.py`**

```python
from rest_framework import serializers
from .models import AIDraft


class AIDraftSerializer(serializers.ModelSerializer):
    lead_id = serializers.UUIDField(source='lead.id', read_only=True)
    lead_company_name = serializers.CharField(source='lead.company_name', read_only=True)
    thread_subject = serializers.CharField(source='thread.subject', read_only=True)
    thread_type = serializers.CharField(source='thread.thread_type', read_only=True)
    reviewed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = AIDraft
        fields = [
            'id', 'status', 'draft_content', 'context_summary',
            'lead_id', 'lead_company_name',
            'thread_subject', 'thread_type',
            'reviewed_by_email', 'reviewed_at', 'created_at',
        ]

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None
```

- [ ] **Step 3: Create `ai_assistant/views.py`**

```python
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AIDraft, DraftStatus
from .serializers import AIDraftSerializer


class AIDraftViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIDraftSerializer
    http_method_names = ['get', 'post']

    def get_queryset(self):
        qs = AIDraft.objects.select_related(
            'lead', 'thread', 'thread__contact', 'reviewed_by'
        ).order_by('-created_at')
        if self.action == 'list':
            return qs.filter(status=DraftStatus.PENDING_REVIEW)
        return qs

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed('POST')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        from communications.services.email_sender import GmailSMTPSender
        from leads.models import LeadAction, ActionType

        draft = self.get_object()
        if draft.status != DraftStatus.PENDING_REVIEW:
            return Response(
                {'error': 'Only pending_review drafts can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sender = GmailSMTPSender()
        sender.send_draft_reply(draft.thread, draft.thread.contact, draft.draft_content)

        draft.status = DraftStatus.SENT
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

        LeadAction.objects.create(
            lead=draft.lead,
            performed_by=request.user,
            action_type=ActionType.AI_DRAFT_APPROVED,
            notes='AI draft approved and sent.',
            metadata={'draft_id': str(draft.id)},
        )

        return Response(AIDraftSerializer(draft).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        from leads.models import LeadAction, ActionType

        draft = self.get_object()
        if draft.status != DraftStatus.PENDING_REVIEW:
            return Response(
                {'error': 'Only pending_review drafts can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        draft.status = DraftStatus.REJECTED
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

        LeadAction.objects.create(
            lead=draft.lead,
            performed_by=request.user,
            action_type=ActionType.AI_DRAFT_REJECTED,
            notes='AI draft rejected.',
            metadata={'draft_id': str(draft.id)},
        )

        return Response(AIDraftSerializer(draft).data)
```

- [ ] **Step 4: Create `ai_assistant/urls.py`**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('ai-drafts', views.AIDraftViewSet, basename='ai-draft')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **Step 5: Register in `config/urls.py`**

Open `BE/config/urls.py`. The current `urlpatterns` block ends with the static files line. Add the ai_assistant include:

Find:
```python
    path('api/', include('leads.urls')),
```

Replace with:
```python
    path('api/', include('leads.urls')),
    path('api/', include('ai_assistant.urls')),
```

- [ ] **Step 6: Run view tests**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest ai_assistant/tests/test_views.py -v 2>&1 | tail -12
```
Expected: `5 passed`

- [ ] **Step 7: Run full suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `70 passed`

Do NOT commit.

---

## Task 4: generate-draft Endpoint on LeadViewSet

**Files:**
- Modify: `BE/leads/views.py`

- [ ] **Step 1: Write failing test**

Append to `BE/ai_assistant/tests/test_views.py` (after the existing tests):

```python
@pytest.mark.django_db
@patch('ai_assistant.tasks.async_task')
def test_generate_draft_endpoint_queues_task(mock_async, auth_client, lead, thread):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 202
    assert resp.data['status'] == 'generating'
    mock_async.assert_called_once_with(
        'ai_assistant.tasks.generate_ai_draft_task',
        str(lead.id),
        str(thread.id),
    )


@pytest.mark.django_db
def test_generate_draft_no_thread_returns_400(auth_client, lead):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_generate_draft_with_existing_pending_returns_400(auth_client, lead, thread, draft):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 400
```

Run to confirm failure:
```bash
python -m pytest ai_assistant/tests/test_views.py::test_generate_draft_endpoint_queues_task -v 2>&1 | tail -8
```
Expected: `404` (endpoint doesn't exist)

- [ ] **Step 2: Add `generate_draft` action to `LeadViewSet` in `leads/views.py`**

Inside the `LeadViewSet` class, after the `bulk_send_intro` action, add:

```python
    @action(detail=True, methods=['post'], url_path='generate-draft')
    def generate_draft(self, request, pk=None):
        from ai_assistant.tasks import async_task
        lead = self.get_object()

        thread = lead.threads.order_by('-created_at').first()
        if not thread:
            return Response(
                {'error': 'No email thread found for this lead. Send an intro email first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_draft = lead.ai_drafts.filter(status='pending_review').exists()
        if pending_draft:
            return Response(
                {'error': 'A pending draft already exists for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task(
            'ai_assistant.tasks.generate_ai_draft_task',
            str(lead.id),
            str(thread.id),
        )
        return Response({'status': 'generating'}, status=status.HTTP_202_ACCEPTED)
```

- [ ] **Step 3: Run all ai_assistant view tests**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest ai_assistant/tests/ -v 2>&1 | tail -15
```
Expected: `8 passed` (3 task tests + 5 original view tests + 3 new generate-draft tests = **11 total** — check actual count)

Wait — the original 5 view tests + 3 new generate-draft tests = 8 view tests + 3 task tests = **11 total** in ai_assistant/tests/.

- [ ] **Step 4: Run full suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `73 passed`

Do NOT commit.

---

## Task 5: Frontend — API, AIDraftsPage, GenerateDraftButton

**Files:**
- Create: `FE/src/api/aiDrafts.js`
- Modify: `FE/src/api/leads.js`
- Replace: `FE/src/pages/AIDraftsPage.jsx`
- Create: `FE/src/components/leads/GenerateDraftButton.jsx`
- Modify: `FE/src/pages/LeadDetailPage.jsx`

- [ ] **Step 1: Create `FE/src/api/aiDrafts.js`**

```js
import api from './axios'

export const listAIDrafts = () => api.get('/ai-drafts/').then((r) => r.data)
export const approveDraft = (id) => api.post(`/ai-drafts/${id}/approve/`).then((r) => r.data)
export const rejectDraft = (id) => api.post(`/ai-drafts/${id}/reject/`).then((r) => r.data)
```

- [ ] **Step 2: Add `generateDraft` to `FE/src/api/leads.js`**

Append at the end of `FE/src/api/leads.js`:

```js
export const generateDraft = (id) =>
  api.post(`/leads/${id}/generate-draft/`).then((r) => r.data)
```

- [ ] **Step 3: Verify build after API changes**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -4
```
Expected: `✓ built`

- [ ] **Step 4: Replace `FE/src/pages/AIDraftsPage.jsx`** with full implementation:

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listAIDrafts, approveDraft, rejectDraft } from '../api/aiDrafts'

const THREAD_TYPE_LABELS = {
  intro:       'Intro',
  pricing:     'Pricing',
  followup:    'Follow-Up',
  negotiation: 'Negotiation',
}

function DraftCard({ draft }) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(true)

  const approveMutation = useMutation({
    mutationFn: () => approveDraft(draft.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ai-drafts'] }),
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectDraft(draft.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ai-drafts'] }),
  })

  const isPending = approveMutation.isPending || rejectMutation.isPending

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900 text-sm">{draft.lead_company_name}</span>
          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
            {THREAD_TYPE_LABELS[draft.thread_type] || draft.thread_type}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 truncate max-w-48">{draft.thread_subject}</span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 text-xs w-5"
          >
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-5 py-4">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 rounded-lg p-4 border border-gray-100 max-h-72 overflow-y-auto">
            {draft.draft_content}
          </pre>

          {draft.context_summary && (
            <p className="text-xs text-gray-400 mt-2 italic">{draft.context_summary}</p>
          )}

          <div className="flex items-center gap-3 mt-4">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={isPending}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {approveMutation.isPending ? 'Sending…' : 'Approve & Send'}
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={isPending}
              className="bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 border border-red-200 text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {rejectMutation.isPending ? 'Rejecting…' : 'Reject'}
            </button>
          </div>

          {approveMutation.isError && (
            <p className="text-xs text-red-600 mt-2">Failed to send. Please try again.</p>
          )}
          {rejectMutation.isError && (
            <p className="text-xs text-red-600 mt-2">Rejection failed. Please try again.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function AIDraftsPage() {
  const { data: drafts = [], isLoading } = useQuery({
    queryKey: ['ai-drafts'],
    queryFn: listAIDrafts,
    refetchInterval: 15000,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI Draft Queue</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review and approve AI-generated emails before they are sent to leads.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-400 text-center py-12">Loading drafts…</p>
      ) : drafts.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl">
          <p className="text-gray-400 text-sm">No drafts pending review.</p>
          <p className="text-gray-300 text-xs mt-1">
            Open a lead in intro_sent or later stage and click "Generate AI Draft".
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create `FE/src/components/leads/GenerateDraftButton.jsx`**

```jsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { generateDraft } from '../../api/leads'

const ELIGIBLE_STAGES = new Set(['intro_sent', 'pricing_sent', 'pricing_followup', 'meeting_set'])

export default function GenerateDraftButton({ lead }) {
  const [done, setDone] = useState(false)
  const [error, setError] = useState(null)

  const mutation = useMutation({
    mutationFn: () => generateDraft(lead.id),
    onSuccess: () => {
      setDone(true)
      setError(null)
    },
    onError: (err) => {
      setError(err.response?.data?.error || 'Could not queue draft.')
    },
  })

  if (!ELIGIBLE_STAGES.has(lead.stage)) return null

  if (done) {
    return (
      <div className="text-xs text-purple-700 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 whitespace-nowrap">
        AI draft generating…
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
      >
        {mutation.isPending ? 'Queuing…' : 'Generate AI Draft'}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
```

- [ ] **Step 6: Wire `GenerateDraftButton` into `LeadDetailPage.jsx`**

In `FE/src/pages/LeadDetailPage.jsx`:

1. Add import after the `SendEmailPanel` import:
```jsx
import GenerateDraftButton from '../components/leads/GenerateDraftButton'
```

2. In the header flex container (which already has `<SendEmailPanel lead={lead} />`), add `<GenerateDraftButton lead={lead} />` before `<SendEmailPanel lead={lead} />`:

Find:
```jsx
        <div className="flex items-center gap-3">
          <SendEmailPanel lead={lead} />
```

Replace with:
```jsx
        <div className="flex items-center gap-3">
          <GenerateDraftButton lead={lead} />
          <SendEmailPanel lead={lead} />
```

- [ ] **Step 7: Final build verification**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -4
```
Expected: `✓ built` with no errors.

Do NOT commit.

---

## Self-Review

**Spec coverage:**
- ✅ Gemini 2.0 Flash draft generation — Task 1+2 (`GeminiClient.MODEL = 'gemini-2.0-flash'`, `generate_ai_draft_task`)
- ✅ AIDraft pending review queue — Task 3 (`GET /api/ai-drafts/` filters by `pending_review`)
- ✅ Approve → auto-send — Task 3 (`approve` action calls `send_draft_reply`, sets `status=sent`)
- ✅ Reject — Task 3 (`reject` action sets `status=rejected`)
- ✅ LeadAction logging for generated/approved/rejected — Tasks 2 + 3
- ✅ `generate-draft` API endpoint — Task 4 (validates thread exists + no pending draft)
- ✅ FE draft review queue — Task 5 (`AIDraftsPage` with accordion cards)
- ✅ FE approve/reject buttons — Task 5 (`DraftCard` with mutations)
- ✅ FE generate button on LeadDetailPage — Task 5 (`GenerateDraftButton`, eligible stages only)
- ✅ Graceful Gemini fallback — Task 1 (`_call_gemini` catches all exceptions)

**Placeholder scan:** None found.

**Type consistency:** `generate_ai_draft_task(lead_id, thread_id)` called identically in `LeadViewSet.generate_draft` (Task 4) and tested in `test_generate_draft_endpoint_queues_task` (Task 4).

---

**Next: Phase 6 — Meeting + Google Calendar integration**
