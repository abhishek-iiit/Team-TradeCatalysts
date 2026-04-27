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
