"""
Django-Q2 background tasks for email communication.

Module-level async_task shim and schedule_once helper mirror the pattern in
campaigns/tasks.py so tests can patch these without patching django_q directly.
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
