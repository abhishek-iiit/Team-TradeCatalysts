# Phase 6: Meeting Scheduling + Calendar Invite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow sales reps to schedule meetings with leads — creates a `Meeting` record, sends an iCalendar (.ics) email invite to the contact, advances lead stage to `meeting_set`, and provides a meetings tab on the lead detail page.

**Architecture:** `CalendarInviteService` builds RFC 5545 iCal and sends via Django SMTP (no OAuth required); `schedule-meeting` action on `LeadViewSet` handles creation; `MeetingViewSet` handles status updates; FE adds a "Meetings" tab to `LeadDetailPage`.

**Tech Stack:** Django 5.2 + DRF, Python email stdlib, React 19 + TanStack Query v5, Tailwind v4

---

## File Structure

**Create:**
- `BE/deals/services/__init__.py`
- `BE/deals/services/calendar_invite.py` — `CalendarInviteService`
- `BE/deals/tests/test_views.py`
- `FE/src/api/meetings.js`
- `FE/src/components/leads/ScheduleMeetingForm.jsx`
- `FE/src/components/leads/MeetingsTab.jsx`

**Modify:**
- `BE/deals/serializers.py` — `MeetingSerializer`, `ScheduleMeetingSerializer`, `MeetingUpdateSerializer`
- `BE/deals/views.py` — `MeetingViewSet`
- `BE/deals/urls.py` — register `MeetingViewSet`
- `BE/config/urls.py` — include `deals.urls`
- `BE/leads/views.py` — add `schedule_meeting` + `meetings` actions; add `ActionType` to imports
- `FE/src/pages/LeadDetailPage.jsx` — add "Meetings" tab

---

## Task 1: Calendar Invite Service

**Files:**
- Create: `BE/deals/services/__init__.py`
- Create: `BE/deals/services/calendar_invite.py`

- [ ] **Step 1: Create empty `deals/services/__init__.py`**

- [ ] **Step 2: Create `deals/services/calendar_invite.py`**

```python
import uuid
from datetime import timedelta

from django.conf import settings


class CalendarInviteService:
    """Builds RFC 5545 iCalendar invites and emails them to contacts via SMTP."""

    def create_event(self, lead, contact, scheduled_at, meeting_link: str = '') -> str:
        """
        Generate an event UID, build an iCal payload, and send it to the contact.
        Always returns a UID (stored as calendar_event_id). Send failures are silent.

        Returns:
            str: UUID event identifier
        """
        event_uid = str(uuid.uuid4())

        if not contact.email:
            return event_uid

        ics_content = self._build_ics(event_uid, lead, contact, scheduled_at, meeting_link)
        try:
            self._send_invite(contact, lead, ics_content)
        except Exception:
            pass

        return event_uid

    def _build_ics(self, uid, lead, contact, scheduled_at, meeting_link) -> str:
        end_at = scheduled_at + timedelta(hours=1)
        fmt = '%Y%m%dT%H%M%SZ'
        description = f'Meeting regarding {lead.company_name}'
        if meeting_link:
            description += f'\\nMeeting Link: {meeting_link}'

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//SalesCatalyst//EN',
            'METHOD:REQUEST',
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'SUMMARY:Meeting with {lead.company_name}',
            f'DESCRIPTION:{description}',
            f'DTSTART:{scheduled_at.strftime(fmt)}',
            f'DTEND:{end_at.strftime(fmt)}',
            f'ORGANIZER:MAILTO:{settings.EMAIL_HOST_USER}',
            (
                f'ATTENDEE;CN={contact.first_name} {contact.last_name}'
                f':MAILTO:{contact.email}'
            ),
            'STATUS:CONFIRMED',
            'SEQUENCE:0',
            'END:VEVENT',
            'END:VCALENDAR',
        ]
        return '\r\n'.join(lines) + '\r\n'

    def _send_invite(self, contact, lead, ics_content: str) -> None:
        from django.core.mail import EmailMessage as DjangoEmailMessage

        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        msg = DjangoEmailMessage(
            subject=f'Meeting Invitation: {lead.company_name}',
            body=(
                f'Dear {contact.first_name},\n\n'
                f'You are invited to a meeting with {company} '
                f'regarding {lead.company_name}.\n\n'
                'Please find the calendar invitation attached.\n\n'
                f'Best regards,\n{settings.EMAIL_HOST_USER}'
            ),
            from_email=settings.EMAIL_HOST_USER,
            to=[contact.email],
        )
        msg.attach('invite.ics', ics_content.encode('utf-8'), 'text/calendar; method=REQUEST')
        msg.send(fail_silently=False)
```

- [ ] **Step 3: Verify Django check still passes**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python manage.py check 2>&1 | tail -3
```
Expected: `System check identified no issues`

- [ ] **Step 4: Run full suite to confirm no regressions**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `73 passed`

Do NOT commit.

---

## Task 2: Meeting API — Serializers, ViewSet, URLs, LeadViewSet Actions

**Files:**
- Modify: `BE/deals/serializers.py`
- Modify: `BE/deals/views.py`
- Modify: `BE/deals/urls.py`
- Modify: `BE/config/urls.py`
- Modify: `BE/leads/views.py`

- [ ] **Step 1: Write failing tests first**

Create `BE/deals/tests/test_views.py`:

```python
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from deals.models import Meeting, MeetingStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='m1', email='m1@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Meet Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Propylene', hsn_code='2901', cas_number='115-07-1',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(
        campaign=campaign, company_name='JP Corp', company_country='JP',
        stage=LeadStage.INTRO_SENT,
    )
    campaign.products.add(product)
    return l


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Hiroshi', email='hiroshi@jpcorp.jp',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.mark.django_db
@patch('deals.services.calendar_invite.CalendarInviteService.create_event')
def test_schedule_meeting_creates_meeting_and_advances_stage(mock_create_event, auth_client, lead, contact):
    mock_create_event.return_value = 'cal-uid-123'

    resp = auth_client.post(f'/api/leads/{lead.id}/schedule-meeting/', {
        'scheduled_at': '2026-05-15T10:00:00Z',
        'contact_id': str(contact.id),
        'meeting_link': 'https://meet.google.com/abc-xyz',
        'notes': 'Initial discussion',
    }, format='json')

    assert resp.status_code == 201
    assert Meeting.objects.filter(lead=lead).count() == 1
    meeting = Meeting.objects.get(lead=lead)
    assert meeting.calendar_event_id == 'cal-uid-123'
    assert meeting.status == MeetingStatus.PROPOSED
    lead.refresh_from_db()
    assert lead.stage == LeadStage.MEETING_SET
    assert lead.actions.filter(action_type=ActionType.MEETING_SCHEDULED).exists()


@pytest.mark.django_db
def test_schedule_meeting_invalid_contact_returns_400(auth_client, lead):
    resp = auth_client.post(f'/api/leads/{lead.id}/schedule-meeting/', {
        'scheduled_at': '2026-05-15T10:00:00Z',
        'contact_id': '00000000-0000-0000-0000-000000000000',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_schedule_meeting_missing_scheduled_at_returns_400(auth_client, lead, contact):
    resp = auth_client.post(f'/api/leads/{lead.id}/schedule-meeting/', {
        'contact_id': str(contact.id),
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_lead_meetings(auth_client, user, lead, contact):
    Meeting.objects.create(
        lead=lead, contact=contact, scheduled_by=user,
        scheduled_at='2026-05-15T10:00:00Z',
    )
    resp = auth_client.get(f'/api/leads/{lead.id}/meetings/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['contact_name'] == 'Hiroshi'
    assert resp.data[0]['lead_company_name'] == 'JP Corp'


@pytest.mark.django_db
def test_update_meeting_status_to_confirmed(auth_client, user, lead, contact):
    meeting = Meeting.objects.create(
        lead=lead, contact=contact, scheduled_by=user,
        scheduled_at='2026-05-15T10:00:00Z',
    )
    resp = auth_client.patch(
        f'/api/meetings/{meeting.id}/',
        {'status': 'confirmed'},
        format='json',
    )
    assert resp.status_code == 200
    meeting.refresh_from_db()
    assert meeting.status == MeetingStatus.CONFIRMED
```

Run to confirm failure:
```bash
python -m pytest deals/tests/test_views.py -v 2>&1 | tail -12
```
Expected: 404 (endpoints don't exist)

- [ ] **Step 2: Write `deals/serializers.py`**

```python
from rest_framework import serializers
from .models import Meeting


class MeetingSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    lead_company_name = serializers.CharField(source='lead.company_name', read_only=True)
    scheduled_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'status', 'scheduled_at', 'meeting_link', 'notes',
            'calendar_event_id', 'contact_name', 'lead_company_name',
            'scheduled_by_email', 'created_at',
        ]

    def get_contact_name(self, obj):
        return f'{obj.contact.first_name} {obj.contact.last_name}'.strip()

    def get_scheduled_by_email(self, obj):
        return obj.scheduled_by.email if obj.scheduled_by else None


class ScheduleMeetingSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    contact_id = serializers.UUIDField()
    meeting_link = serializers.CharField(max_length=500, required=False, default='')
    notes = serializers.CharField(required=False, default='')


class MeetingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['status', 'meeting_link', 'notes']
```

- [ ] **Step 3: Write `deals/views.py`**

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Meeting
from .serializers import MeetingSerializer, MeetingUpdateSerializer


class MeetingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        return Meeting.objects.select_related(
            'lead', 'contact', 'scheduled_by'
        ).order_by('scheduled_at')

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return MeetingUpdateSerializer
        return MeetingSerializer

    def partial_update(self, request, *args, **kwargs):
        meeting = self.get_object()
        serializer = MeetingUpdateSerializer(meeting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeetingSerializer(meeting).data)
```

- [ ] **Step 4: Write `deals/urls.py`**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('meetings', views.MeetingViewSet, basename='meeting')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **Step 5: Register in `config/urls.py`**

Read `config/urls.py`. Find:
```python
    path('api/', include('ai_assistant.urls')),
```
Add after it:
```python
    path('api/', include('deals.urls')),
```

- [ ] **Step 6: Add `schedule_meeting` and `meetings` actions to `LeadViewSet`**

Read `leads/views.py`. 

First, update the model import line from:
```python
from .models import Lead, LeadAction, LeadStage, Contact
```
to:
```python
from .models import Lead, LeadAction, LeadStage, Contact, ActionType
```

Then add the two new actions inside `LeadViewSet`, after the `generate_draft` action (before the blank line + `@api_view` for `dashboard_stats`):

```python
    @action(detail=True, methods=['post'], url_path='schedule-meeting')
    def schedule_meeting(self, request, pk=None):
        from deals.services.calendar_invite import CalendarInviteService
        from deals.models import Meeting
        from deals.serializers import ScheduleMeetingSerializer, MeetingSerializer

        lead = self.get_object()
        serializer = ScheduleMeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            contact = lead.contacts.get(id=data['contact_id'])
        except Contact.DoesNotExist:
            return Response(
                {'error': 'Contact not found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calendar_service = CalendarInviteService()
        event_id = calendar_service.create_event(
            lead=lead,
            contact=contact,
            scheduled_at=data['scheduled_at'],
            meeting_link=data.get('meeting_link', ''),
        )

        meeting = Meeting.objects.create(
            lead=lead,
            contact=contact,
            scheduled_by=request.user,
            calendar_event_id=event_id,
            scheduled_at=data['scheduled_at'],
            meeting_link=data.get('meeting_link', ''),
            notes=data.get('notes', ''),
        )

        LeadAction.objects.create(
            lead=lead,
            performed_by=request.user,
            action_type=ActionType.MEETING_SCHEDULED,
            notes=f'Meeting scheduled for {data["scheduled_at"].strftime("%Y-%m-%d %H:%M UTC")}',
            metadata={'meeting_id': str(meeting.id)},
        )

        lead.stage = LeadStage.MEETING_SET
        lead.save(update_fields=['stage', 'updated_at'])

        return Response(MeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='meetings')
    def meetings(self, request, pk=None):
        from deals.models import Meeting
        from deals.serializers import MeetingSerializer

        lead = self.get_object()
        qs = lead.meetings.select_related('contact', 'scheduled_by').order_by('scheduled_at')
        return Response(MeetingSerializer(qs, many=True).data)
```

- [ ] **Step 7: Run failing tests — should now pass**

```bash
python -m pytest deals/tests/test_views.py -v 2>&1 | tail -15
```
Expected: `5 passed`

- [ ] **Step 8: Run full suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Expected: `78 passed`

Do NOT commit.

---

## Task 3: Frontend — Meetings API + Components + LeadDetailPage tab

**Files:**
- Create: `FE/src/api/meetings.js`
- Create: `FE/src/components/leads/ScheduleMeetingForm.jsx`
- Create: `FE/src/components/leads/MeetingsTab.jsx`
- Modify: `FE/src/pages/LeadDetailPage.jsx`

- [ ] **Step 1: Create `FE/src/api/meetings.js`**

```js
import api from './axios'

export const scheduleMeeting = (leadId, data) =>
  api.post(`/leads/${leadId}/schedule-meeting/`, data).then((r) => r.data)

export const listLeadMeetings = (leadId) =>
  api.get(`/leads/${leadId}/meetings/`).then((r) => r.data)

export const updateMeeting = (meetingId, data) =>
  api.patch(`/meetings/${meetingId}/`, data).then((r) => r.data)
```

- [ ] **Step 2: Create `FE/src/components/leads/ScheduleMeetingForm.jsx`**

```jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scheduleMeeting } from '../../api/meetings'

export default function ScheduleMeetingForm({ lead, onScheduled }) {
  const qc = useQueryClient()
  const [scheduledAt, setScheduledAt] = useState('')
  const [contactId, setContactId] = useState('')
  const [meetingLink, setMeetingLink] = useState('')
  const [notes, setNotes] = useState('')

  const eligibleContacts = lead.contacts?.filter((c) => c.email) || []
  const defaultContactId = eligibleContacts.find((c) => c.is_primary)?.id
    || eligibleContacts[0]?.id
    || ''

  const mutation = useMutation({
    mutationFn: (data) => scheduleMeeting(lead.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
      qc.invalidateQueries({ queryKey: ['lead-meetings', lead.id] })
      onScheduled?.()
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    mutation.mutate({
      scheduled_at: new Date(scheduledAt).toISOString(),
      contact_id: contactId || defaultContactId,
      meeting_link: meetingLink,
      notes,
    })
  }

  if (eligibleContacts.length === 0) {
    return (
      <p className="text-xs text-gray-400">
        No contacts with email — add a contact to schedule a meeting.
      </p>
    )
  }

  if (mutation.isSuccess) {
    return (
      <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
        Meeting scheduled. A calendar invite has been sent to the contact.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Date & Time *</label>
        <input
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Contact *</label>
        <select
          value={contactId || defaultContactId}
          onChange={(e) => setContactId(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        >
          {eligibleContacts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.first_name} {c.last_name} — {c.email}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Meeting Link</label>
        <input
          type="url"
          value={meetingLink}
          onChange={(e) => setMeetingLink(e.target.value)}
          placeholder="https://meet.google.com/..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Agenda, topics to cover…"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
        />
      </div>
      <button
        type="submit"
        disabled={mutation.isPending || !scheduledAt}
        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
      >
        {mutation.isPending ? 'Scheduling…' : 'Schedule Meeting'}
      </button>
      {mutation.isError && (
        <p className="text-xs text-red-600">
          {mutation.error?.response?.data?.error || 'Failed to schedule. Please try again.'}
        </p>
      )}
    </form>
  )
}
```

- [ ] **Step 3: Create `FE/src/components/leads/MeetingsTab.jsx`**

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listLeadMeetings, updateMeeting } from '../../api/meetings'
import ScheduleMeetingForm from './ScheduleMeetingForm'

const STATUS_STYLES = {
  proposed:  'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

function formatMeetingDate(isoString) {
  return new Date(isoString).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function MeetingCard({ meeting, leadId }) {
  const qc = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: (newStatus) => updateMeeting(meeting.id, { status: newStatus }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lead-meetings', leadId] }),
  })

  const badgeClass = STATUS_STYLES[meeting.status] || 'bg-gray-100 text-gray-600'
  const statusLabel = meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-sm font-semibold text-gray-900">
            {formatMeetingDate(meeting.scheduled_at)}
          </span>
          <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-medium ${badgeClass}`}>
            {statusLabel}
          </span>
        </div>
        <span className="text-xs text-gray-400">{meeting.contact_name}</span>
      </div>

      {meeting.meeting_link && (
        <a
          href={meeting.meeting_link}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-indigo-600 hover:underline block mb-2 truncate"
        >
          {meeting.meeting_link}
        </a>
      )}

      {meeting.notes && (
        <p className="text-xs text-gray-500 mb-3 whitespace-pre-wrap">{meeting.notes}</p>
      )}

      <div className="flex gap-2">
        {meeting.status === 'proposed' && (
          <>
            <button
              onClick={() => updateMutation.mutate('confirmed')}
              disabled={updateMutation.isPending}
              className="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
            >
              Confirm
            </button>
            <button
              onClick={() => updateMutation.mutate('cancelled')}
              disabled={updateMutation.isPending}
              className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
            >
              Cancel
            </button>
          </>
        )}
        {meeting.status === 'confirmed' && (
          <button
            onClick={() => updateMutation.mutate('completed')}
            disabled={updateMutation.isPending}
            className="text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
          >
            Mark Completed
          </button>
        )}
      </div>
    </div>
  )
}

export default function MeetingsTab({ lead }) {
  const [showForm, setShowForm] = useState(false)

  const { data: meetings = [], isLoading } = useQuery({
    queryKey: ['lead-meetings', lead.id],
    queryFn: () => listLeadMeetings(lead.id),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">
          {meetings.length} meeting{meetings.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ Schedule Meeting'}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <ScheduleMeetingForm lead={lead} onScheduled={() => setShowForm(false)} />
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400 text-center py-4">Loading meetings…</p>
      ) : meetings.length === 0 && !showForm ? (
        <p className="text-sm text-gray-400 text-center py-8">
          No meetings scheduled yet.
        </p>
      ) : (
        <div className="space-y-3">
          {meetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} leadId={lead.id} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Update `LeadDetailPage.jsx`**

Read `LeadDetailPage.jsx`. Make three targeted changes:

**4a.** Add import after the existing component imports (before the `const STAGES` line):
```jsx
import MeetingsTab from '../components/leads/MeetingsTab'
```

**4b.** Change the `TABS` constant from:
```jsx
const TABS = ['Timeline', 'Call Log', 'Emails']
```
to:
```jsx
const TABS = ['Timeline', 'Call Log', 'Emails', 'Meetings']
```

**4c.** Add the Meetings tab rendering case after the Emails block. Find:
```jsx
          {activeTab === 'Emails' && (
            <EmailThreadsTab leadId={id} />
          )}
```
Add after it:
```jsx
          {activeTab === 'Meetings' && (
            <MeetingsTab lead={lead} />
          )}
```

- [ ] **Step 5: Final build verification**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -5
```
Expected: `✓ built` with no errors.

Do NOT commit.

---

## Self-Review

**Spec coverage:**
- ✅ Schedule meeting API — Task 2 (`POST /api/leads/:id/schedule-meeting/` on `LeadViewSet`)
- ✅ iCalendar invite sent to contact — Task 1 (`CalendarInviteService._send_invite` with .ics attachment)
- ✅ `calendar_event_id` stored — Task 2 (`meeting.calendar_event_id = event_id`)
- ✅ Stage advanced to `meeting_set` — Task 2 (`lead.stage = LeadStage.MEETING_SET`)
- ✅ LeadAction(meeting_scheduled) logged — Task 2
- ✅ List meetings for a lead — Task 2 (`GET /api/leads/:id/meetings/`)
- ✅ Update meeting status — Task 2 (`PATCH /api/meetings/:id/`)
- ✅ Graceful send failure — Task 1 (try/except in `create_event`, always returns UID)
- ✅ FE scheduling form — Task 3 (`ScheduleMeetingForm` with datetime, contact, link, notes)
- ✅ FE meetings list with status updates — Task 3 (`MeetingsTab` + `MeetingCard`)
- ✅ FE "Meetings" tab on LeadDetailPage — Task 3

**Placeholder scan:** None.

**Type consistency:** `CalendarInviteService.create_event(lead, contact, scheduled_at, meeting_link)` called identically in `schedule_meeting` action (Task 2) and patched in tests as `deals.services.calendar_invite.CalendarInviteService.create_event`.

---

**Next: Phase 7 — Deal Closure + Flow Visualization**
