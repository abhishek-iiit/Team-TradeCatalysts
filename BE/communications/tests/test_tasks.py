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
    thread = EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction | Acetic Acid', thread_type='intro',
    )
    EmailMessage.objects.create(
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
