import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource
from deals.models import Meeting, MeetingStatus, Deal, DealOutcome

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(username='u', email='u@t.com', password='p')
    campaign = Campaign.objects.create(title='C', created_by=user)
    lead = Lead.objects.create(campaign=campaign, company_name='BigCo', company_country='IN')
    contact = Contact.objects.create(
        lead=lead, first_name='CEO', email='ceo@bigco.com', source=ContactSource.VOLZA
    )
    return user, lead, contact


@pytest.mark.django_db
def test_meeting_defaults_to_proposed(setup):
    user, lead, contact = setup
    meeting = Meeting.objects.create(
        lead=lead, contact=contact, scheduled_by=user,
        scheduled_at=timezone.now(),
    )
    assert meeting.status == MeetingStatus.PROPOSED


@pytest.mark.django_db
def test_deal_is_one_to_one_with_lead(setup):
    user, lead, contact = setup
    deal = Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON,
        closed_by=user, closed_at=timezone.now(),
        remarks='Great partnership',
    )
    assert deal.outcome == 'won'
    assert lead.deal == deal


@pytest.mark.django_db
def test_deal_cannot_be_created_twice_for_same_lead(setup):
    user, lead, contact = setup
    Deal.objects.create(
        lead=lead, outcome=DealOutcome.WON,
        closed_by=user, closed_at=timezone.now(),
    )
    with pytest.raises(Exception):
        Deal.objects.create(
            lead=lead, outcome=DealOutcome.LOST,
            closed_by=user, closed_at=timezone.now(),
        )
