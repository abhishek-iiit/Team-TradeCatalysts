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
    Contact.objects.create(
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
