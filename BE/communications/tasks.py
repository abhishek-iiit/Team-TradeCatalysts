"""
Django-Q2 background tasks for email communication.

Pipeline: Intro → Documents → Requirements → Pricing → Follow-Up → Meeting → Deal
Default trigger days: 3 → 3 → 2 → 3 → 2 → 5
"""

import json

from communications.services.email_sender import GmailSMTPSender
from communications.services.gmail_poller import GmailIMAPPoller
from communications.services.sms_sender import TwilioSMSSender

_DEFAULT_TRIGGER_DAYS = {
    'intro': 3,
    'documents': 3,
    'requirements': 2,
    'pricing': 3,
    'followup': 2,
    'meeting': 5,
}


def _get_stage_config(product, stage: str):
    """Return ProductStageConfig for product+stage, or None if not configured."""
    from campaigns.models import ProductStageConfig
    try:
        return ProductStageConfig.objects.get(product=product, stage=stage)
    except ProductStageConfig.DoesNotExist:
        return None


def _trigger_days(stage_config, stage: str) -> int:
    if stage_config and stage_config.trigger_days:
        return stage_config.trigger_days
    return _DEFAULT_TRIGGER_DAYS.get(stage, 4)


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


def _get_lead_and_contact(lead_id, contact_id):
    from leads.models import Lead, Contact
    try:
        lead = Lead.objects.select_related(
            'campaign', 'campaign__created_by'
        ).prefetch_related('campaign__products').get(id=lead_id)
        contact = Contact.objects.get(id=contact_id)
        return lead, contact
    except (Lead.DoesNotExist, Contact.DoesNotExist):
        return None, None


def _sender(lead) -> GmailSMTPSender:
    """Return a GmailSMTPSender configured for the campaign owner's email account."""
    user = getattr(lead.campaign, 'created_by', None)
    return GmailSMTPSender(user=user)


def _get_product(lead):
    return (
        lead.campaign.products.filter(brochure_pdf__isnull=False).exclude(brochure_pdf='').first()
        or lead.campaign.products.first()
    )


# ---------------------------------------------------------------------------
# Stage 1: Intro
# ---------------------------------------------------------------------------

def send_intro_email_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'intro')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'intro', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.INTRO_EMAIL,
            notes=f'Intro email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_intro_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.INTRO_SMS,
            notes=f'Intro SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.INTRO_SENT
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_documents_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'intro'))


# ---------------------------------------------------------------------------
# Stage 2: Documents
# ---------------------------------------------------------------------------

def send_documents_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'documents')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'documents', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.DOCUMENTS_EMAIL,
            notes=f'Documents email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_documents_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.DOCUMENTS_SMS,
            notes=f'Documents SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.DOCUMENTS_SENT
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_requirements_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'documents'))


# ---------------------------------------------------------------------------
# Stage 3: Ask Requirements
# ---------------------------------------------------------------------------

def send_requirements_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'requirements')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'requirements', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.REQUIREMENTS_EMAIL,
            notes=f'Requirements email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_requirements_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.REQUIREMENTS_SMS,
            notes=f'Requirements SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.REQUIREMENTS_ASKED
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_pricing_email_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'requirements'))


# ---------------------------------------------------------------------------
# Stage 4: Pricing
# ---------------------------------------------------------------------------

def send_pricing_email_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'pricing')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'pricing', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.PRICING_EMAIL,
            notes=f'Pricing email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_pricing_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.PRICING_SMS,
            notes=f'Pricing SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.PRICING_SENT
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_pricing_followup_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'pricing'))


# ---------------------------------------------------------------------------
# Stage 5: Follow-Up on Pricing (payment terms + lead time)
# ---------------------------------------------------------------------------

def send_pricing_followup_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'followup')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'followup', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.PRICING_FOLLOWUP_EMAIL,
            notes=f'Pricing follow-up email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_pricing_followup_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.PRICING_FOLLOWUP_SMS,
            notes=f'Pricing follow-up SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.PRICING_FOLLOWUP
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_meeting_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'followup'))


# ---------------------------------------------------------------------------
# Stage 6: Meeting
# ---------------------------------------------------------------------------

def send_meeting_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'meeting')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'meeting', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.MEETING_EMAIL,
            notes=f'Meeting email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_meeting_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.MEETING_SMS,
            notes=f'Meeting SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.MEETING_SENT
    lead.save(update_fields=['stage', 'updated_at'])
    schedule_once('communications.tasks.send_deal_task', lead_id, contact_id,
                  days=_trigger_days(stage_config, 'meeting'))


# ---------------------------------------------------------------------------
# Stage 7: Deal (0-1% margin + sample request) — terminal
# ---------------------------------------------------------------------------

def send_deal_task(lead_id: str, contact_id: str) -> None:
    from leads.models import LeadAction, ActionType, LeadStage

    lead, contact = _get_lead_and_contact(lead_id, contact_id)
    if not lead or lead.auto_flow_paused:
        return

    product = _get_product(lead)
    if not product:
        return

    stage_config = _get_stage_config(product, 'deal')

    if contact.email:
        _sender(lead).send_email(lead, contact, product, 'deal', stage_config=stage_config)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.DEAL_EMAIL,
            notes=f'Deal email sent to {contact.email}',
        )
    elif contact.phone:
        TwilioSMSSender().send_deal_sms(lead, contact, product)
        LeadAction.objects.create(
            lead=lead, performed_by=None,
            action_type=ActionType.DEAL_SMS,
            notes=f'Deal SMS sent to {contact.phone}',
        )
    else:
        return

    lead.stage = LeadStage.DEAL_SENT
    lead.save(update_fields=['stage', 'updated_at'])


# ---------------------------------------------------------------------------
# Gmail inbox poller
# ---------------------------------------------------------------------------

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
