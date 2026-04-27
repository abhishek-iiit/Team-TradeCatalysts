import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from communications.models import EmailThread
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='av1', email='av1@test.com', password='pass')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def campaign(user):
    return Campaign.objects.create(title='AI Camp', created_by=user)


@pytest.fixture
def product(campaign):
    return Product.objects.create(
        name='Benzene', hsn_code='2902', cas_number='71-43-2',
        created_by=campaign.created_by,
    )


@pytest.fixture
def lead(campaign, product):
    l = Lead.objects.create(
        campaign=campaign, company_name='AI Buyer', company_country='JP',
        stage=LeadStage.INTRO_SENT,
    )
    campaign.products.add(product)
    return l


@pytest.fixture
def contact(lead):
    return Contact.objects.create(
        lead=lead, first_name='Kenji', email='kenji@aibuyer.jp',
        source=ContactSource.VOLZA, is_primary=True,
    )


@pytest.fixture
def thread(lead, contact):
    return EmailThread.objects.create(
        lead=lead, contact=contact,
        subject='Introduction | Benzene', thread_type='intro',
    )


@pytest.fixture
def draft(lead, thread):
    return AIDraft.objects.create(
        lead=lead, thread=thread,
        draft_content='Test draft content.', context_summary='ctx',
    )


@pytest.mark.django_db
def test_list_pending_drafts(auth_client, draft):
    resp = auth_client.get('/api/ai-drafts/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['id'] == str(draft.id)
    assert resp.data[0]['draft_content'] == 'Test draft content.'
    assert resp.data[0]['lead_company_name'] == 'AI Buyer'


@pytest.mark.django_db
def test_list_excludes_non_pending(auth_client, draft):
    draft.status = DraftStatus.SENT
    draft.save()
    resp = auth_client.get('/api/ai-drafts/')
    assert resp.status_code == 200
    assert len(resp.data) == 0


@pytest.mark.django_db
@patch('ai_assistant.views.GmailSMTPSender')
def test_approve_draft_sends_email_and_marks_sent(mock_sender_cls, auth_client, user, draft):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/approve/')

    assert resp.status_code == 200
    draft.refresh_from_db()
    assert draft.status == DraftStatus.SENT
    assert draft.reviewed_by == user
    mock_sender.send_draft_reply.assert_called_once_with(
        draft.thread, draft.thread.contact, draft.draft_content
    )
    assert draft.lead.actions.filter(action_type=ActionType.AI_DRAFT_APPROVED).exists()


@pytest.mark.django_db
def test_approve_non_pending_returns_400(auth_client, draft):
    draft.status = DraftStatus.SENT
    draft.save()
    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/approve/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_reject_draft_marks_rejected_and_logs_action(auth_client, user, draft):
    resp = auth_client.post(f'/api/ai-drafts/{draft.id}/reject/')

    assert resp.status_code == 200
    draft.refresh_from_db()
    assert draft.status == DraftStatus.REJECTED
    assert draft.reviewed_by == user
    assert draft.lead.actions.filter(action_type=ActionType.AI_DRAFT_REJECTED).exists()


@pytest.mark.django_db
@patch('ai_assistant.tasks.async_task')
def test_generate_draft_endpoint_queues_task(mock_async, auth_client, lead, thread):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 202
    assert resp.data['status'] == 'generating'
    mock_async.assert_called_once_with(
        'ai_assistant.tasks.generate_ai_draft_task',
        str(lead.id),
        str(thread.id),
    )


@pytest.mark.django_db
def test_generate_draft_no_thread_returns_400(auth_client, lead):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_generate_draft_with_existing_pending_returns_400(auth_client, lead, thread, draft):
    resp = auth_client.post(f'/api/leads/{lead.id}/generate-draft/')
    assert resp.status_code == 400
