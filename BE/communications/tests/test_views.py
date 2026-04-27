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
