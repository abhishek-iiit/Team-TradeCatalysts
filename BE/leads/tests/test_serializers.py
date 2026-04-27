import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, LeadAction, ActionType, ContactSource
from leads.serializers import LeadDetailSerializer, LeadActionSerializer

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.fixture
def lead(campaign):
    return Lead.objects.create(campaign=campaign, company_name='Acme', company_country='IN')


@pytest.mark.django_db
def test_lead_detail_includes_contacts_and_actions(lead):
    Contact.objects.create(
        lead=lead, first_name='Jane', email='jane@acme.com', source=ContactSource.VOLZA
    )
    LeadAction.objects.create(lead=lead, action_type=ActionType.NOTE, notes='Test note')

    data = LeadDetailSerializer(lead).data

    assert len(data['contacts']) == 1
    assert data['contacts'][0]['email'] == 'jane@acme.com'
    assert len(data['actions']) == 1
    assert data['actions'][0]['action_type'] == 'note'
    assert data['actions'][0]['performed_by_email'] is None  # system action


@pytest.mark.django_db
def test_lead_action_serializer_performed_by_email(lead, user):
    action = LeadAction.objects.create(
        lead=lead,
        action_type=ActionType.FOLLOW_UP_CALL,
        performed_by=user,
        notes='Called the customer',
    )
    data = LeadActionSerializer(action).data
    assert data['performed_by_email'] == 'u@t.com'
    assert data['notes'] == 'Called the customer'


@pytest.mark.django_db
def test_lead_detail_includes_volza_fields(lead):
    lead.volza_data = {'raw': True}
    lead.pricing_trend = {'2024': 120.5}
    lead.save()

    data = LeadDetailSerializer(lead).data
    assert 'volza_data' in data
    assert 'pricing_trend' in data
    assert 'purchase_history' in data
