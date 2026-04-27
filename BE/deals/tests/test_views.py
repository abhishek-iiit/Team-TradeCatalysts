import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from deals.models import Meeting, MeetingStatus, Deal, DealOutcome

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


# ── Deal Closure Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_close_deal_won(auth_client, lead):
    lead.stage = LeadStage.MEETING_SET
    lead.save(update_fields=['stage'])

    resp = auth_client.post(f'/api/leads/{lead.id}/close/', {
        'outcome': 'won',
        'remarks': 'Great deal!',
        'deal_value': '150000.00',
    }, format='json')

    assert resp.status_code == 201
    assert resp.data['outcome'] == 'won'
    assert resp.data['lead_company_name'] == 'JP Corp'
    lead.refresh_from_db()
    assert lead.stage == LeadStage.CLOSED_WON
    assert lead.actions.filter(action_type=ActionType.DEAL_CLOSED).exists()
    assert Deal.objects.filter(lead=lead, outcome=DealOutcome.WON).count() == 1


@pytest.mark.django_db
def test_close_deal_lost(auth_client, lead):
    lead.stage = LeadStage.PRICING_SENT
    lead.save(update_fields=['stage'])

    resp = auth_client.post(f'/api/leads/{lead.id}/close/', {
        'outcome': 'lost',
        'remarks': 'Price too high',
    }, format='json')

    assert resp.status_code == 201
    assert resp.data['outcome'] == 'lost'
    lead.refresh_from_db()
    assert lead.stage == LeadStage.CLOSED_LOST


@pytest.mark.django_db
def test_close_deal_invalid_outcome_returns_400(auth_client, lead):
    resp = auth_client.post(f'/api/leads/{lead.id}/close/', {
        'outcome': 'maybe',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_close_deal_already_closed_returns_400(auth_client, user, lead):
    lead.stage = LeadStage.CLOSED_WON
    lead.save(update_fields=['stage'])
    Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON, closed_by=user,
        closed_at='2026-04-01T00:00:00Z',
    )

    resp = auth_client.post(f'/api/leads/{lead.id}/close/', {
        'outcome': 'won',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_flow_endpoint_returns_stages_and_timeline(auth_client, lead):
    resp = auth_client.get(f'/api/leads/{lead.id}/flow/')
    assert resp.status_code == 200
    data = resp.data
    assert data['current_stage'] == lead.stage
    assert data['company_name'] == 'JP Corp'
    assert len(data['stages']) == 7
    assert 'timeline' in data


@pytest.mark.django_db
def test_list_deals_endpoint(auth_client, user, lead):
    lead.stage = LeadStage.CLOSED_WON
    lead.save(update_fields=['stage'])
    Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON, closed_by=user,
        closed_at='2026-04-01T00:00:00Z',
    )
    resp = auth_client.get('/api/deals/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['outcome'] == 'won'
