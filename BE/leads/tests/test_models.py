import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, LeadStage, Contact, ContactSource, LeadAction, ActionType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u', email='u@t.com', password='p')


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='Test', created_by=user)


@pytest.mark.django_db
def test_lead_defaults(campaign):
    lead = Lead.objects.create(
        campaign=campaign,
        company_name='Acme Corp',
        company_country='IN',
    )
    assert lead.stage == LeadStage.DISCOVERED
    assert lead.auto_flow_paused is False
    assert str(lead) == 'Acme Corp (discovered)'


@pytest.mark.django_db
def test_lead_has_missing_contact_when_no_contacts(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Ghost Inc', company_country='US'
    )
    assert lead.has_missing_contact is True


@pytest.mark.django_db
def test_lead_not_missing_contact_when_email_present(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Ghost Inc', company_country='US'
    )
    Contact.objects.create(
        lead=lead, first_name='Jane', last_name='Doe',
        email='jane@ghost.com', source=ContactSource.VOLZA
    )
    assert lead.has_missing_contact is False


@pytest.mark.django_db
def test_lead_action_system_action_has_no_performer(campaign):
    lead = Lead.objects.create(
        campaign=campaign, company_name='Sys Inc', company_country='DE'
    )
    action = LeadAction.objects.create(
        lead=lead, action_type=ActionType.INTRO_EMAIL,
        notes='Sent automatically'
    )
    assert action.performed_by is None
