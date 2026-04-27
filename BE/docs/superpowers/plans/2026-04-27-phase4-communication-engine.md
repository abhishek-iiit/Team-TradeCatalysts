# Phase 4: Communication Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email send/receive capabilities — intro email with brochure attachment, pricing email, follow-up scheduling via Django-Q2, and IMAP-based inbound reply detection.

**Architecture:** Django SMTP backend (already configured in settings) for outbound email; Python `imaplib` for Gmail IMAP inbound polling; Django-Q2 `async_task` + `Schedule` for async execution and T+4 day scheduling; deferred imports throughout to avoid circular dependencies.

**Tech Stack:** Django 5.2 + DRF 3.16.1, Django-Q2, imaplib, React 19 + Vite, TanStack Query v5, Tailwind v4

---

## File Structure

**Create:**
- `BE/communications/services/__init__.py` — empty package init
- `BE/communications/services/email_sender.py` — `GmailSMTPSender` class
- `BE/communications/services/gmail_poller.py` — `GmailIMAPPoller` class
- `BE/communications/tasks.py` — async_task shim + 4 task functions
- `BE/communications/tests/test_email_sender.py` — unit tests for sender
- `BE/communications/tests/test_tasks.py` — task integration tests
- `BE/leads/tests/test_send_actions.py` — API endpoint tests
- `FE/src/components/leads/SendEmailPanel.jsx` — email action buttons

**Modify:**
- `BE/config/settings/base.py` — add SENDER_COMPANY_NAME env var
- `BE/communications/apps.py` — add ready() to set up periodic poll schedule
- `BE/leads/views.py` — add send_intro, send_pricing, bulk_send_intro actions
- `FE/src/api/leads.js` — add sendIntroEmail, sendPricingEmail, bulkSendIntroEmail
- `FE/src/pages/LeadDetailPage.jsx` — add SendEmailPanel to header area
- `FE/src/pages/CampaignLeadsPage.jsx` — add bulk send button to selection bar

---

## Task 1: Settings — SENDER_COMPANY_NAME

**Files:**
- Modify: `BE/config/settings/base.py`

- [ ] **Step 1: Add setting after the EMAIL_* block**

Open `BE/config/settings/base.py`. After the line `CORS_ALLOW_CREDENTIALS = True`, add:

```python
SENDER_COMPANY_NAME = env('SENDER_COMPANY_NAME', default='Elchemy')
```

- [ ] **Step 2: Verify settings load**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local'); django.setup(); from django.conf import settings; print(settings.SENDER_COMPANY_NAME)"
```

Expected: `Elchemy`

- [ ] **Step 3: Commit**

```bash
git add config/settings/base.py
git commit -m "feat: add SENDER_COMPANY_NAME setting"
```

---

## Task 2: Email Sender Service

**Files:**
- Create: `BE/communications/services/__init__.py`
- Create: `BE/communications/services/email_sender.py`

- [ ] **Step 1: Create package init**

Create `BE/communications/services/__init__.py` with empty content.

- [ ] **Step 2: Write the failing test**

Create `BE/communications/tests/test_email_sender.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, call
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, ContactSource
from communications.models import EmailThread, EmailMessage
from communications.services.email_sender import GmailSMTPSender

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u2', email='u2@test.com', password='pass')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(name='Acetic Acid', hsn_code='2915', cas_number='64-19-7', created_by=campaign.created_by)


@pytest.fixture
def lead(campaign):
    return Lead.objects.create(campaign=campaign, company_name='Buyer Co', company_country='DE')


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Anna', last_name='Müller',
        email='anna@buyer.de', source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.mark.django_db
@patch('communications.services.email_sender.DjangoEmailMessage')
def test_send_intro_creates_thread_and_message(mock_cls, lead, contact, product):
    mock_msg = MagicMock()
    mock_cls.return_value = mock_msg

    sender = GmailSMTPSender()
    thread = sender.send_email(lead, contact, product, 'intro')

    assert isinstance(thread, EmailThread)
    assert thread.thread_type == 'intro'
    assert EmailMessage.objects.filter(thread=thread, direction='outbound').count() == 1
    mock_msg.send.assert_called_once_with(fail_silently=False)


@pytest.mark.django_db
@patch('communications.services.email_sender.DjangoEmailMessage')
def test_send_intro_no_attachment_without_brochure(mock_cls, lead, contact, product):
    mock_msg = MagicMock()
    mock_cls.return_value = mock_msg

    sender = GmailSMTPSender()
    sender.send_email(lead, contact, product, 'intro')

    mock_msg.attach.assert_not_called()


@pytest.mark.django_db
@patch('communications.services.email_sender.DjangoEmailMessage')
def test_send_pricing_creates_pricing_thread(mock_cls, lead, contact, product):
    mock_msg = MagicMock()
    mock_cls.return_value = mock_msg

    sender = GmailSMTPSender()
    thread = sender.send_email(lead, contact, product, 'pricing')

    assert thread.thread_type == 'pricing'
    assert EmailThread.objects.count() == 1


@pytest.mark.django_db
@patch('communications.services.email_sender.DjangoEmailMessage')
def test_message_id_stored_in_gmail_message_id(mock_cls, lead, contact, product):
    mock_msg = MagicMock()
    mock_cls.return_value = mock_msg

    sender = GmailSMTPSender()
    sender.send_email(lead, contact, product, 'intro')

    msg = EmailMessage.objects.get(direction='outbound')
    assert msg.gmail_message_id.startswith('<')
    assert '@salescatalyst>' in msg.gmail_message_id
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_email_sender.py -v 2>&1 | tail -15
```

Expected: `ImportError` or `ModuleNotFoundError` for `GmailSMTPSender`

- [ ] **Step 4: Write the email sender service**

Create `BE/communications/services/email_sender.py`:

```python
import uuid
from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage
from django.utils import timezone

from communications.models import EmailThread, EmailMessage, ThreadType, MessageDirection


_EMAIL_TEMPLATES = {
    'intro': {
        'subject': 'Introduction | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'I hope this email finds you well. We are {company}, a leading supplier of {product_name}.\n\n'
            'We noticed your company has been actively importing {product_name} and would love to '
            'explore how we can meet your requirements with our high-quality products.\n\n'
            '{brochure_note}'
            'We would welcome the opportunity to discuss your requirements further. '
            'Please feel free to reply to this email or reach out directly.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.INTRO,
    },
    'pricing': {
        'subject': 'Pricing Information | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'Thank you for your interest in {product_name}.\n\n'
            'We are pleased to share that we offer competitive pricing and flexible payment terms '
            'tailored to your purchase volume. Please let us know your quantity requirements so '
            'we can provide a detailed quotation.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.PRICING,
    },
    'followup': {
        'subject': 'Follow-Up | {product_name}',
        'body': (
            'Dear {contact_name},\n\n'
            'I wanted to follow up on our previous email regarding {product_name}.\n\n'
            'We understand you are busy, but we believe we can offer excellent value for your '
            'requirements. Please do not hesitate to reach out if you have any questions.\n\n'
            'Best regards,\n{sender_email}'
        ),
        'thread_type': ThreadType.FOLLOWUP,
    },
}


class GmailSMTPSender:
    """Sends outbound emails via Django SMTP and records them in EmailThread/EmailMessage."""

    def send_email(self, lead, contact, product, email_type: str) -> EmailThread:
        """
        Send an outbound email and persist the thread and message records.

        Args:
            lead: Lead instance
            contact: Contact instance (must have .email set)
            product: Product instance (brochure attached for 'intro' type if available)
            email_type: One of 'intro', 'pricing', 'followup'

        Returns:
            Created EmailThread instance
        """
        tmpl = _EMAIL_TEMPLATES[email_type]
        contact_name = f'{contact.first_name} {contact.last_name}'.strip() or contact.email
        company = getattr(settings, 'SENDER_COMPANY_NAME', 'Elchemy')
        sender_email = settings.EMAIL_HOST_USER

        has_brochure = email_type == 'intro' and bool(
            getattr(product, 'brochure_pdf', None) and product.brochure_pdf.name
        )
        brochure_note = 'Please find our product brochure attached for your reference.\n\n' if has_brochure else ''

        subject = tmpl['subject'].format(product_name=product.name)
        body = tmpl['body'].format(
            contact_name=contact_name,
            product_name=product.name,
            company=company,
            brochure_note=brochure_note,
            sender_email=sender_email,
        )

        message_id = f'<{uuid.uuid4()}@salescatalyst>'

        thread = EmailThread.objects.create(
            lead=lead,
            contact=contact,
            subject=subject,
            thread_type=tmpl['thread_type'],
            gmail_thread_id='',
        )

        django_email = DjangoEmailMessage(
            subject=subject,
            body=body,
            from_email=sender_email,
            to=[contact.email],
            headers={'Message-ID': message_id},
        )

        if has_brochure:
            try:
                with product.brochure_pdf.open('rb') as f:
                    django_email.attach(
                        product.brochure_pdf.name.split('/')[-1],
                        f.read(),
                        'application/pdf',
                    )
            except (OSError, ValueError):
                pass

        django_email.send(fail_silently=False)

        EmailMessage.objects.create(
            thread=thread,
            direction=MessageDirection.OUTBOUND,
            body_text=body,
            sent_at=timezone.now(),
            gmail_message_id=message_id,
        )

        return thread
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_email_sender.py -v 2>&1 | tail -10
```

Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add communications/services/__init__.py communications/services/email_sender.py communications/tests/test_email_sender.py
git commit -m "feat: add GmailSMTPSender service with intro/pricing/followup templates"
```

---

## Task 3: Gmail IMAP Poller Service

**Files:**
- Create: `BE/communications/services/gmail_poller.py`

- [ ] **Step 1: Write the failing test (add to test_email_sender.py)**

Append to `BE/communications/tests/test_email_sender.py`:

```python
from unittest.mock import patch, MagicMock
from communications.services.gmail_poller import GmailIMAPPoller


def test_poll_returns_empty_list_on_imap_failure():
    poller = GmailIMAPPoller()
    with patch('communications.services.gmail_poller.imaplib.IMAP4_SSL') as mock_imap:
        mock_imap.side_effect = Exception('Connection refused')
        result = poller.poll_new_replies()
    assert result == []


def test_poll_parses_in_reply_to_header():
    poller = GmailIMAPPoller()

    import email as email_lib
    raw_email = (
        b'From: buyer@example.com\r\n'
        b'Subject: Re: Introduction | Acetic Acid\r\n'
        b'In-Reply-To: <abc123@salescatalyst>\r\n'
        b'Content-Type: text/plain\r\n'
        b'\r\n'
        b'Thanks for the intro!'
    )

    mock_mail = MagicMock()
    mock_mail.uid.side_effect = [
        ('OK', [b'1']),
        ('OK', [(b'1 (RFC822 {123}', raw_email)]),
    ]

    with patch('communications.services.gmail_poller.imaplib.IMAP4_SSL') as mock_imap_cls:
        mock_imap_cls.return_value = mock_mail
        result = poller.poll_new_replies()

    assert len(result) == 1
    assert result[0]['in_reply_to'] == '<abc123@salescatalyst>'
    assert result[0]['sender_email'] == 'buyer@example.com'
    assert 'Thanks for the intro!' in result[0]['body_text']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_email_sender.py::test_poll_returns_empty_list_on_imap_failure communications/tests/test_email_sender.py::test_poll_parses_in_reply_to_header -v 2>&1 | tail -10
```

Expected: `ImportError` for `GmailIMAPPoller`

- [ ] **Step 3: Write the IMAP poller**

Create `BE/communications/services/gmail_poller.py`:

```python
import imaplib
import email as email_lib
from email.header import decode_header as _decode_header

from django.conf import settings


def _decode(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return str(value)


class GmailIMAPPoller:
    """Polls Gmail INBOX via IMAP for unread replies from known contacts."""

    HOST = 'imap.gmail.com'
    PORT = 993

    def poll_new_replies(self) -> list[dict]:
        """
        Connect to Gmail IMAP SSL, fetch UNSEEN messages, return parsed results.

        Returns:
            List of dicts with keys: uid, sender_email, in_reply_to, subject, body_text.
            Returns [] on any connection or parsing failure.
        """
        results = []
        try:
            mail = imaplib.IMAP4_SSL(self.HOST, self.PORT)
            mail.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            mail.select('INBOX')

            _, uid_data = mail.uid('search', None, 'UNSEEN')
            uids = uid_data[0].split() if uid_data[0] else []

            for uid in uids:
                _, msg_data = mail.uid('fetch', uid, '(RFC822)')
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                sender = msg.get('From', '')
                if '<' in sender and '>' in sender:
                    sender = sender.split('<')[1].rstrip('>')
                sender = sender.lower().strip()

                in_reply_to = (msg.get('In-Reply-To') or '').strip()

                subject_parts = _decode_header(msg.get('Subject', ''))
                subject = ''.join(
                    _decode(part) if enc is None else part.decode(enc, errors='replace')
                    for part, enc in subject_parts
                )

                body_text = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body_text = _decode(part.get_payload(decode=True))
                            break
                else:
                    body_text = _decode(msg.get_payload(decode=True))

                results.append({
                    'uid': _decode(uid),
                    'sender_email': sender,
                    'in_reply_to': in_reply_to,
                    'subject': subject,
                    'body_text': body_text,
                })

            mail.logout()
        except Exception:
            pass

        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_email_sender.py -v 2>&1 | tail -10
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add communications/services/gmail_poller.py communications/tests/test_email_sender.py
git commit -m "feat: add GmailIMAPPoller service for inbound reply detection"
```

---

## Task 4: Communications Tasks

**Files:**
- Create: `BE/communications/tasks.py`
- Create: `BE/communications/tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `BE/communications/tests/test_tasks.py`:

```python
import pytest
import json
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadAction, LeadStage, ContactSource, ActionType
from communications.models import EmailThread, EmailMessage, MessageDirection

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='t1', email='t1@test.com', password='pass')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Acetic Acid', hsn_code='2915', cas_number='64-19-7',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(campaign=campaign, company_name='Buyer Co', company_country='DE')
    campaign.products.add(product)
    return l


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Anna', email='anna@buyer.de',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.mark.django_db
@patch('communications.tasks.GmailSMTPSender')
@patch('communications.tasks.schedule_once')
def test_send_intro_task_advances_stage_and_logs_action(mock_schedule, mock_sender_cls, lead, contact):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender
    mock_sender.send_email.return_value = MagicMock()

    from communications.tasks import send_intro_email_task
    send_intro_email_task(str(lead.id), str(contact.id))

    lead.refresh_from_db()
    assert lead.stage == LeadStage.INTRO_SENT
    assert lead.actions.filter(action_type=ActionType.INTRO_EMAIL).exists()
    mock_schedule.assert_called_once_with(
        'communications.tasks.send_pricing_email_task', str(lead.id), str(contact.id), days=4
    )


@pytest.mark.django_db
@patch('communications.tasks.GmailSMTPSender')
@patch('communications.tasks.schedule_once')
def test_send_intro_task_skips_if_paused(mock_schedule, mock_sender_cls, lead, contact):
    lead.auto_flow_paused = True
    lead.save()

    from communications.tasks import send_intro_email_task
    send_intro_email_task(str(lead.id), str(contact.id))

    lead.refresh_from_db()
    assert lead.stage == LeadStage.DISCOVERED
    mock_sender_cls.return_value.send_email.assert_not_called()


@pytest.mark.django_db
def test_send_intro_task_skips_missing_lead():
    from communications.tasks import send_intro_email_task
    # Should not raise
    send_intro_email_task('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000001')


@pytest.mark.django_db
@patch('communications.tasks.GmailSMTPSender')
@patch('communications.tasks.schedule_once')
def test_send_pricing_task_advances_to_pricing_sent(mock_schedule, mock_sender_cls, lead, contact):
    lead.stage = LeadStage.INTRO_SENT
    lead.save()
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender
    mock_sender.send_email.return_value = MagicMock()

    from communications.tasks import send_pricing_email_task
    send_pricing_email_task(str(lead.id), str(contact.id))

    lead.refresh_from_db()
    assert lead.stage == LeadStage.PRICING_SENT
    assert lead.actions.filter(action_type=ActionType.PRICING_EMAIL).exists()
    mock_schedule.assert_called_once_with(
        'communications.tasks.send_pricing_followup_task', str(lead.id), str(contact.id), days=4
    )


@pytest.mark.django_db
@patch('communications.tasks.GmailSMTPSender')
@patch('communications.tasks.schedule_once')
def test_send_followup_task_advances_to_pricing_followup(mock_schedule, mock_sender_cls, lead, contact):
    lead.stage = LeadStage.PRICING_SENT
    lead.save()
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender
    mock_sender.send_email.return_value = MagicMock()

    from communications.tasks import send_pricing_followup_task
    send_pricing_followup_task(str(lead.id), str(contact.id))

    lead.refresh_from_db()
    assert lead.stage == LeadStage.PRICING_FOLLOWUP
    assert lead.actions.filter(action_type=ActionType.PRICING_FOLLOWUP_EMAIL).exists()


@pytest.mark.django_db
@patch('communications.tasks.GmailIMAPPoller')
def test_poll_gmail_inbox_creates_inbound_message(mock_poller_cls, lead, contact):
    # Create an existing outbound thread/message
    thread = EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction | Acetic Acid', thread_type='intro',
    )
    sent_msg = EmailMessage.objects.create(
        thread=thread,
        direction=MessageDirection.OUTBOUND,
        body_text='Hi Anna...',
        sent_at='2026-04-27T10:00:00Z',
        gmail_message_id='<abc123@salescatalyst>',
    )

    mock_poller = MagicMock()
    mock_poller_cls.return_value = mock_poller
    mock_poller.poll_new_replies.return_value = [{
        'uid': '1',
        'sender_email': 'anna@buyer.de',
        'in_reply_to': '<abc123@salescatalyst>',
        'subject': 'Re: Introduction | Acetic Acid',
        'body_text': 'Thanks for reaching out!',
    }]

    from communications.tasks import poll_gmail_inbox
    poll_gmail_inbox()

    assert EmailMessage.objects.filter(thread=thread, direction=MessageDirection.INBOUND).count() == 1
    inbound = EmailMessage.objects.get(thread=thread, direction=MessageDirection.INBOUND)
    assert inbound.body_text == 'Thanks for reaching out!'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_tasks.py -v 2>&1 | tail -15
```

Expected: `ImportError` for `communications.tasks`

- [ ] **Step 3: Write communications/tasks.py**

Create `BE/communications/tasks.py`:

```python
"""
Django-Q2 background tasks for email communication.

Tasks:
  send_intro_email_task      — send intro email, advance stage, schedule pricing
  send_pricing_email_task    — send pricing email, advance stage, schedule followup
  send_pricing_followup_task — send pricing follow-up email, advance stage
  poll_gmail_inbox           — IMAP poll for inbound replies, store as EmailMessage

Module-level async_task shim mirrors the pattern in campaigns/tasks.py so tests
can patch ``communications.tasks.async_task`` without patching django_q directly.
"""

import json

from communications.services.email_sender import GmailSMTPSender
from communications.services.gmail_poller import GmailIMAPPoller


def async_task(func_path: str, *args, **kwargs) -> None:
    from django_q.tasks import async_task as _async_task
    _async_task(func_path, *args, **kwargs)


def schedule_once(func_path: str, lead_id: str, contact_id: str, days: int) -> None:
    from django_q.models import Schedule
    from django.utils import timezone
    from datetime import timedelta
    Schedule.objects.create(
        func=func_path,
        args=json.dumps([lead_id, contact_id]),
        schedule_type=Schedule.ONCE,
        next_run=timezone.now() + timedelta(days=days),
        repeats=1,
    )


def send_intro_email_task(lead_id: str, contact_id: str) -> None:
    """Send intro email, create LeadAction, advance stage to intro_sent, schedule pricing."""
    from leads.models import Lead, Contact, LeadAction, ActionType, LeadStage

    try:
        lead = Lead.objects.select_related('campaign').prefetch_related('campaign__products').get(id=lead_id)
        contact = Contact.objects.get(id=contact_id)
    except (Lead.DoesNotExist, Contact.DoesNotExist):
        return

    if lead.auto_flow_paused:
        return

    product = (
        lead.campaign.products.filter(brochure_pdf__isnull=False).exclude(brochure_pdf='').first()
        or lead.campaign.products.first()
    )
    if not product:
        return

    sender = GmailSMTPSender()
    sender.send_email(lead, contact, product, 'intro')

    LeadAction.objects.create(
        lead=lead,
        performed_by=None,
        action_type=ActionType.INTRO_EMAIL,
        notes=f'Intro email sent to {contact.email}',
    )

    lead.stage = LeadStage.INTRO_SENT
    lead.save(update_fields=['stage', 'updated_at'])

    schedule_once('communications.tasks.send_pricing_email_task', lead_id, contact_id, days=4)


def send_pricing_email_task(lead_id: str, contact_id: str) -> None:
    """Send pricing email, create LeadAction, advance stage to pricing_sent, schedule followup."""
    from leads.models import Lead, Contact, LeadAction, ActionType, LeadStage

    try:
        lead = Lead.objects.select_related('campaign').prefetch_related('campaign__products').get(id=lead_id)
        contact = Contact.objects.get(id=contact_id)
    except (Lead.DoesNotExist, Contact.DoesNotExist):
        return

    if lead.auto_flow_paused:
        return

    product = lead.campaign.products.first()
    if not product:
        return

    sender = GmailSMTPSender()
    sender.send_email(lead, contact, product, 'pricing')

    LeadAction.objects.create(
        lead=lead,
        performed_by=None,
        action_type=ActionType.PRICING_EMAIL,
        notes=f'Pricing email sent to {contact.email}',
    )

    lead.stage = LeadStage.PRICING_SENT
    lead.save(update_fields=['stage', 'updated_at'])

    schedule_once('communications.tasks.send_pricing_followup_task', lead_id, contact_id, days=4)


def send_pricing_followup_task(lead_id: str, contact_id: str) -> None:
    """Send pricing follow-up email, create LeadAction, advance stage to pricing_followup."""
    from leads.models import Lead, Contact, LeadAction, ActionType, LeadStage

    try:
        lead = Lead.objects.select_related('campaign').prefetch_related('campaign__products').get(id=lead_id)
        contact = Contact.objects.get(id=contact_id)
    except (Lead.DoesNotExist, Contact.DoesNotExist):
        return

    if lead.auto_flow_paused:
        return

    product = lead.campaign.products.first()
    if not product:
        return

    sender = GmailSMTPSender()
    sender.send_email(lead, contact, product, 'followup')

    LeadAction.objects.create(
        lead=lead,
        performed_by=None,
        action_type=ActionType.PRICING_FOLLOWUP_EMAIL,
        notes=f'Pricing follow-up email sent to {contact.email}',
    )

    lead.stage = LeadStage.PRICING_FOLLOWUP
    lead.save(update_fields=['stage', 'updated_at'])


def poll_gmail_inbox() -> None:
    """Poll Gmail IMAP for inbound replies; store as inbound EmailMessage records."""
    from communications.models import EmailMessage, MessageDirection
    from django.utils import timezone

    poller = GmailIMAPPoller()
    replies = poller.poll_new_replies()

    for reply in replies:
        in_reply_to = reply.get('in_reply_to', '')
        if not in_reply_to:
            continue

        try:
            sent_msg = EmailMessage.objects.select_related('thread').get(
                gmail_message_id=in_reply_to,
                direction=MessageDirection.OUTBOUND,
            )
        except EmailMessage.DoesNotExist:
            continue

        already_stored = EmailMessage.objects.filter(
            thread=sent_msg.thread,
            direction=MessageDirection.INBOUND,
            body_text=reply['body_text'],
        ).exists()
        if already_stored:
            continue

        EmailMessage.objects.create(
            thread=sent_msg.thread,
            direction=MessageDirection.INBOUND,
            body_text=reply['body_text'],
            sent_at=timezone.now(),
            gmail_message_id='',
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest communications/tests/test_tasks.py -v 2>&1 | tail -15
```

Expected: `7 passed`

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
python -m pytest --tb=short -q 2>&1 | tail -10
```

Expected: all previously passing tests still pass + 7 new.

- [ ] **Step 6: Commit**

```bash
git add communications/tasks.py communications/tests/test_tasks.py
git commit -m "feat: add communications tasks for send intro/pricing/followup and IMAP poll"
```

---

## Task 5: AppConfig — Periodic Poll Schedule

**Files:**
- Modify: `BE/communications/apps.py`

- [ ] **Step 1: Replace apps.py content**

Replace the full content of `BE/communications/apps.py` with:

```python
from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communications'

    def ready(self):
        self._setup_gmail_poll_schedule()

    def _setup_gmail_poll_schedule(self):
        try:
            from django_q.models import Schedule
            if not Schedule.objects.filter(func='communications.tasks.poll_gmail_inbox').exists():
                Schedule.objects.create(
                    func='communications.tasks.poll_gmail_inbox',
                    minutes=15,
                    schedule_type=Schedule.MINUTES,
                    repeats=-1,
                )
        except Exception:
            pass
```

- [ ] **Step 2: Verify Django starts without error**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python manage.py check 2>&1
```

Expected: `System check identified no issues`

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add communications/apps.py
git commit -m "feat: auto-register Gmail IMAP poll as periodic django-q schedule on startup"
```

---

## Task 6: Lead API Send Endpoints

**Files:**
- Modify: `BE/leads/views.py`
- Create: `BE/leads/tests/test_send_actions.py`

- [ ] **Step 1: Write failing tests**

Create `BE/leads/tests/test_send_actions.py`:

```python
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='sa1', email='sa1@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Send Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Ethanol', hsn_code='2207', cas_number='64-17-5',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(campaign=campaign, company_name='Euro Buyer', company_country='PL')
    campaign.products.add(product)
    return l


@pytest.fixture
def contact_with_email(lead):
    return Contact.objects.create(
        lead=lead, first_name='Piotr', email='piotr@eurobuyer.pl',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.mark.django_db
@patch('communications.tasks.async_task')
def test_send_intro_queues_task(mock_async, auth_client, lead, contact_with_email):
    resp = auth_client.post(f'/api/leads/{lead.id}/send-intro/')
    assert resp.status_code == 202
    assert resp.data['status'] == 'queued'
    mock_async.assert_called_once_with(
        'communications.tasks.send_intro_email_task',
        str(lead.id),
        str(contact_with_email.id),
    )


@pytest.mark.django_db
def test_send_intro_wrong_stage_returns_400(auth_client, lead, contact_with_email):
    lead.stage = LeadStage.INTRO_SENT
    lead.save()
    resp = auth_client.post(f'/api/leads/{lead.id}/send-intro/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_send_intro_no_email_contact_returns_400(auth_client, lead):
    Contact.objects.create(
        lead=lead, first_name='Noemail', source=ContactSource.VOLZA, is_primary=True,
    )
    resp = auth_client.post(f'/api/leads/{lead.id}/send-intro/')
    assert resp.status_code == 400


@pytest.mark.django_db
@patch('communications.tasks.async_task')
def test_send_pricing_queues_task(mock_async, auth_client, lead, contact_with_email):
    lead.stage = LeadStage.INTRO_SENT
    lead.save()
    resp = auth_client.post(f'/api/leads/{lead.id}/send-pricing/')
    assert resp.status_code == 202
    mock_async.assert_called_once_with(
        'communications.tasks.send_pricing_email_task',
        str(lead.id),
        str(contact_with_email.id),
    )


@pytest.mark.django_db
def test_send_pricing_wrong_stage_returns_400(auth_client, lead, contact_with_email):
    resp = auth_client.post(f'/api/leads/{lead.id}/send-pricing/')
    assert resp.status_code == 400


@pytest.mark.django_db
@patch('communications.tasks.async_task')
def test_bulk_send_intro_queues_eligible_leads(mock_async, auth_client, lead, contact_with_email):
    lead2 = Lead.objects.create(campaign=lead.campaign, company_name='PL Buyer 2', company_country='PL')
    contact2 = Contact.objects.create(
        lead=lead2, first_name='Marek', email='marek@plbuyer.pl',
        source=ContactSource.VOLZA, is_primary=True,
    )
    lead_no_email = Lead.objects.create(campaign=lead.campaign, company_name='No Email', company_country='PL')
    Contact.objects.create(lead=lead_no_email, first_name='X', source=ContactSource.VOLZA)

    resp = auth_client.post(
        '/api/leads/bulk-send-intro/',
        {'lead_ids': [str(lead.id), str(lead2.id), str(lead_no_email.id)]},
        format='json',
    )
    assert resp.status_code == 202
    assert resp.data['queued'] == 2
    assert mock_async.call_count == 2


@pytest.mark.django_db
def test_bulk_send_intro_empty_list_returns_400(auth_client):
    resp = auth_client.post('/api/leads/bulk-send-intro/', {'lead_ids': []}, format='json')
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest leads/tests/test_send_actions.py -v 2>&1 | tail -15
```

Expected: `405 Method Not Allowed` or `404` (endpoints don't exist yet)

- [ ] **Step 3: Add send actions to LeadViewSet**

Open `BE/leads/views.py`. After the `threads` action method (before the closing of the class), add:

```python
    @action(detail=True, methods=['post'], url_path='send-intro')
    def send_intro(self, request, pk=None):
        from communications.tasks import async_task
        lead = self.get_object()

        if lead.stage != LeadStage.DISCOVERED:
            return Response(
                {'error': f'Lead must be in discovered stage, current: {lead.stage}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact = (
            lead.contacts
            .filter(email__isnull=False)
            .exclude(email='')
            .order_by('-is_primary')
            .first()
        )
        if not contact:
            return Response(
                {'error': 'No contact with email found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task('communications.tasks.send_intro_email_task', str(lead.id), str(contact.id))
        return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='send-pricing')
    def send_pricing(self, request, pk=None):
        from communications.tasks import async_task
        lead = self.get_object()

        if lead.stage != LeadStage.INTRO_SENT:
            return Response(
                {'error': f'Lead must be in intro_sent stage, current: {lead.stage}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact = (
            lead.contacts
            .filter(email__isnull=False)
            .exclude(email='')
            .order_by('-is_primary')
            .first()
        )
        if not contact:
            return Response(
                {'error': 'No contact with email found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task('communications.tasks.send_pricing_email_task', str(lead.id), str(contact.id))
        return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='bulk-send-intro')
    def bulk_send_intro(self, request):
        from communications.tasks import async_task
        lead_ids = request.data.get('lead_ids', [])
        if not lead_ids:
            return Response({'error': 'lead_ids required'}, status=status.HTTP_400_BAD_REQUEST)

        queued = 0
        for lead_id in lead_ids:
            try:
                lead = Lead.objects.prefetch_related('contacts').get(id=lead_id)
            except Lead.DoesNotExist:
                continue

            if lead.stage != LeadStage.DISCOVERED:
                continue

            contact = (
                lead.contacts
                .filter(email__isnull=False)
                .exclude(email='')
                .order_by('-is_primary')
                .first()
            )
            if not contact:
                continue

            async_task('communications.tasks.send_intro_email_task', str(lead.id), str(contact.id))
            queued += 1

        return Response({'queued': queued}, status=status.HTTP_202_ACCEPTED)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/BE
python -m pytest leads/tests/test_send_actions.py -v 2>&1 | tail -15
```

Expected: `7 passed`

- [ ] **Step 5: Run full suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add leads/views.py leads/tests/test_send_actions.py
git commit -m "feat: add send-intro, send-pricing, and bulk-send-intro API endpoints on LeadViewSet"
```

---

## Task 7: FE — API Functions + SendEmailPanel Component

**Files:**
- Modify: `FE/src/api/leads.js`
- Create: `FE/src/components/leads/SendEmailPanel.jsx`

- [ ] **Step 1: Add API functions to leads.js**

Open `FE/src/api/leads.js`. At the end of the file, append:

```js
export const sendIntroEmail = (id) =>
  api.post(`/leads/${id}/send-intro/`).then((r) => r.data)

export const sendPricingEmail = (id) =>
  api.post(`/leads/${id}/send-pricing/`).then((r) => r.data)

export const bulkSendIntroEmail = (leadIds) =>
  api.post('/leads/bulk-send-intro/', { lead_ids: leadIds }).then((r) => r.data)
```

- [ ] **Step 2: Verify build is clean after API change**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -5
```

Expected: `✓ built` with no errors.

- [ ] **Step 3: Write SendEmailPanel component**

Create `FE/src/components/leads/SendEmailPanel.jsx`:

```jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { sendIntroEmail, sendPricingEmail } from '../../api/leads'

export default function SendEmailPanel({ lead }) {
  const qc = useQueryClient()
  const [queued, setQueued] = useState(false)

  const primaryContact =
    lead.contacts?.find((c) => c.is_primary && c.email) ||
    lead.contacts?.find((c) => c.email)

  const introMutation = useMutation({
    mutationFn: () => sendIntroEmail(lead.id),
    onSuccess: () => {
      setQueued(true)
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
    },
  })

  const pricingMutation = useMutation({
    mutationFn: () => sendPricingEmail(lead.id),
    onSuccess: () => {
      setQueued(true)
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
    },
  })

  const canSendIntro = lead.stage === 'discovered'
  const canSendPricing = lead.stage === 'intro_sent'

  if (!primaryContact || (!canSendIntro && !canSendPricing)) return null

  if (queued) {
    return (
      <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 whitespace-nowrap">
        Email queued → {primaryContact.email}
      </div>
    )
  }

  const mutation = canSendIntro ? introMutation : pricingMutation
  const label = canSendIntro ? 'Send Intro Email' : 'Send Pricing Email'

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || lead.auto_flow_paused}
        className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
      >
        {mutation.isPending ? 'Queuing…' : label}
      </button>
      {lead.auto_flow_paused && (
        <p className="text-xs text-yellow-700">Auto-flow paused</p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Verify build is clean**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -5
```

Expected: `✓ built` with no errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
git add src/api/leads.js src/components/leads/SendEmailPanel.jsx
git commit -m "feat: add sendIntroEmail/sendPricingEmail API and SendEmailPanel component"
```

---

## Task 8: FE — Wire SendEmailPanel into LeadDetailPage

**Files:**
- Modify: `FE/src/pages/LeadDetailPage.jsx`

- [ ] **Step 1: Add import and render SendEmailPanel**

In `FE/src/pages/LeadDetailPage.jsx`:

1. Add import at top (after existing imports):

```jsx
import SendEmailPanel from '../components/leads/SendEmailPanel'
```

2. Inside the header div (the `flex items-start justify-between mb-2` div), the right side has a `flex items-center gap-3` div with the stage select and pause toggle. Add `<SendEmailPanel lead={lead} />` **before** the stage select:

Find the block:
```jsx
        <div className="flex items-center gap-3">
          <select
```

Replace with:
```jsx
        <div className="flex items-center gap-3">
          <SendEmailPanel lead={lead} />
          <select
```

- [ ] **Step 2: Verify build is clean**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -5
```

Expected: `✓ built` with no errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/LeadDetailPage.jsx
git commit -m "feat: add SendEmailPanel to LeadDetailPage header"
```

---

## Task 9: FE — Bulk Send in CampaignLeadsPage

**Files:**
- Modify: `FE/src/pages/CampaignLeadsPage.jsx`

- [ ] **Step 1: Add bulk send mutation and handler to CampaignLeadsPage**

In `FE/src/pages/CampaignLeadsPage.jsx`:

1. Add import at top (after existing imports):

```jsx
import { useMutation } from '@tanstack/react-query'
import { bulkSendIntroEmail } from '../api/leads'
```

2. Inside `CampaignLeadsPage`, after the `selected` state declaration, add:

```jsx
  const [bulkResult, setBulkResult] = useState(null)

  const bulkMutation = useMutation({
    mutationFn: () => bulkSendIntroEmail([...selected]),
    onSuccess: (data) => {
      setBulkResult(data)
      setSelected(new Set())
      setTimeout(() => setBulkResult(null), 4000)
    },
  })
```

3. Find the existing selection action bar:

```jsx
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
          <span className="text-sm font-medium text-indigo-700">{selected.size} selected</span>
          <button
            onClick={() => navigate(`/leads/${[...selected][0]}`)}
            className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-indigo-700"
          >
            View Lead
          </button>
        </div>
      )}
```

Replace with:

```jsx
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
          <span className="text-sm font-medium text-indigo-700">{selected.size} selected</span>
          <button
            onClick={() => navigate(`/leads/${[...selected][0]}`)}
            className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-indigo-700"
          >
            View Lead
          </button>
          <button
            onClick={() => bulkMutation.mutate()}
            disabled={bulkMutation.isPending}
            className="text-sm bg-emerald-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50"
          >
            {bulkMutation.isPending ? 'Sending…' : 'Send Intro Email'}
          </button>
          {bulkResult && (
            <span className="text-xs text-green-700 font-medium">{bulkResult.queued} emails queued</span>
          )}
        </div>
      )}
```

4. Also add `useState` to the existing import (it's already there for `selected`). Add `bulkResult` state.

The full updated `useState` area at the top of the component should be:

```jsx
  const [activeStage, setActiveStage] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [bulkResult, setBulkResult] = useState(null)
```

- [ ] **Step 2: Verify build is clean**

```bash
cd /Users/abhishekjaiswal/Desktop/majorProjects/Team-TradeCatalysts/FE
npm run build 2>&1 | tail -5
```

Expected: `✓ built` with no errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/CampaignLeadsPage.jsx
git commit -m "feat: add bulk Send Intro Email action to CampaignLeadsPage selection bar"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `POST /api/leads/:id/send-intro/` — Task 6 (validates stage=discovered, contact with email, queues task)
- ✅ `POST /api/leads/:id/send-pricing/` — Task 6 (validates stage=intro_sent)
- ✅ `POST /api/leads/bulk-send-intro/` — Task 6 (bulk, skips ineligible)
- ✅ Brochure PDF attachment — Task 2 (GmailSMTPSender attaches for intro type)
- ✅ EmailThread + EmailMessage creation — Task 2 (GmailSMTPSender.send_email)
- ✅ LeadAction logging — Task 4 (tasks create LeadAction with correct ActionType)
- ✅ Stage advancement — Task 4 (lead.save(update_fields=['stage', 'updated_at']))
- ✅ T+4 day scheduling — Task 4 (schedule_once with days=4)
- ✅ auto_flow_paused guard — Task 4 (early return if paused)
- ✅ IMAP inbound polling — Task 3 + 4 (GmailIMAPPoller + poll_gmail_inbox task)
- ✅ Periodic schedule setup — Task 5 (AppConfig.ready, 15-minute Schedule)
- ✅ FE Send Intro/Pricing buttons — Tasks 7 + 8 (SendEmailPanel on LeadDetailPage)
- ✅ FE bulk send — Task 9 (CampaignLeadsPage selection bar)

**Placeholder scan:** None found.

**Type consistency:** `schedule_once(func_path, lead_id, contact_id, days)` used identically in tasks.py and mocked in tests. `async_task` shim signature matches campaigns/tasks.py pattern.

---

**Next: Phase 5 — AI Email Assistant (Gemini 2.0 Flash draft generation, AIDraft pending review queue, approve/reject UI)**
