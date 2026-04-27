import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from leads.models import Lead, Contact, ContactSource
from communications.models import EmailThread, ThreadType
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def thread(db):
    user = User.objects.create_user(username='u', email='u@t.com', password='p')
    campaign = Campaign.objects.create(title='C', created_by=user)
    lead = Lead.objects.create(campaign=campaign, company_name='Corp', company_country='US')
    contact = Contact.objects.create(
        lead=lead, first_name='Ann', email='ann@corp.com', source=ContactSource.VOLZA
    )
    return EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Re: Intro', thread_type=ThreadType.NEGOTIATION,
    )


@pytest.mark.django_db
def test_ai_draft_defaults_to_pending(thread):
    draft = AIDraft.objects.create(
        lead=thread.lead,
        thread=thread,
        draft_content='Dear Ann, thank you for your response...',
        context_summary='Customer asked for 10% discount.',
    )
    assert draft.status == DraftStatus.PENDING_REVIEW
    assert draft.reviewed_by is None
    assert 'Corp' in str(draft)
