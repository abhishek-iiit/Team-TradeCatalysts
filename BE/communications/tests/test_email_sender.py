import pytest
from unittest.mock import patch, MagicMock
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


from communications.services.gmail_poller import GmailIMAPPoller


def test_poll_returns_empty_list_on_imap_failure():
    poller = GmailIMAPPoller()
    with patch('communications.services.gmail_poller.imaplib.IMAP4_SSL') as mock_imap:
        mock_imap.side_effect = Exception('Connection refused')
        result = poller.poll_new_replies()
    assert result == []


def test_poll_parses_in_reply_to_header():
    poller = GmailIMAPPoller()

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
