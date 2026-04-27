import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign
from leads.models import Lead, Contact, LeadAction, LeadStage, ActionType, ContactSource

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.fixture
def lead(campaign):
    return Lead.objects.create(
        campaign=campaign, company_name='Acme Corp', company_country='IN'
    )


@pytest.mark.django_db
def test_lead_detail_returns_contacts_and_actions(auth_client, lead):
    Contact.objects.create(
        lead=lead, first_name='Jane', email='jane@acme.com', source=ContactSource.VOLZA
    )
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Note')
    response = auth_client.get(f'/api/leads/{lead.id}/')
    assert response.status_code == 200
    assert len(response.data['contacts']) == 1
    assert len(response.data['actions']) == 1
    assert 'volza_data' in response.data


@pytest.mark.django_db
def test_patch_lead_stage(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'stage': 'intro_sent'}, format='json'
    )
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.stage == LeadStage.INTRO_SENT


@pytest.mark.django_db
def test_patch_lead_auto_flow_paused(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'auto_flow_paused': True}, format='json'
    )
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.auto_flow_paused is True


@pytest.mark.django_db
def test_patch_invalid_stage_rejected(auth_client, lead):
    response = auth_client.patch(
        f'/api/leads/{lead.id}/', {'stage': 'nonexistent_stage'}, format='json'
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_lead_actions(auth_client, lead):
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Note 1')
    LeadAction.objects.create(lead=lead, action_type=ActionType.FOLLOW_UP_CALL, notes='Called')
    response = auth_client.get(f'/api/leads/{lead.id}/actions/')
    assert response.status_code == 200
    assert len(response.data) == 2


@pytest.mark.django_db
def test_post_lead_action_sets_performer(auth_client, lead, user):
    response = auth_client.post(
        f'/api/leads/{lead.id}/actions/',
        {'action_type': 'follow_up_call', 'notes': 'Called, buyer is interested'},
        format='json',
    )
    assert response.status_code == 201
    action = LeadAction.objects.get(lead=lead)
    assert action.performed_by == user
    assert action.notes == 'Called, buyer is interested'


@pytest.mark.django_db
def test_post_action_without_notes_succeeds(auth_client, lead):
    # notes is blank=True on model, so empty notes are allowed
    response = auth_client.post(
        f'/api/leads/{lead.id}/actions/',
        {'action_type': 'follow_up_call', 'notes': ''},
        format='json',
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_dashboard_stats_returns_counts(auth_client, lead):
    response = auth_client.get('/api/dashboard/')
    assert response.status_code == 200
    assert response.data['total_leads'] == 1
    assert response.data['leads_by_stage']['discovered'] == 1
    assert 'active_campaigns' in response.data
    assert 'missing_contact_count' in response.data


@pytest.mark.django_db
def test_leads_endpoint_not_writable_via_post(auth_client, campaign):
    response = auth_client.post('/api/leads/', {}, format='json')
    assert response.status_code == 405  # Method Not Allowed
