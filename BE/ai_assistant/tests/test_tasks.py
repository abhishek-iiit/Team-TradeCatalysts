import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, Product
from leads.models import Lead, Contact, LeadStage, ContactSource, LeadAction, ActionType
from communications.models import EmailThread
from ai_assistant.models import AIDraft, DraftStatus

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='ai1', email='ai1@test.com', password='pass')


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


@pytest.mark.django_db
@patch('ai_assistant.tasks.GeminiClient')
def test_generate_draft_creates_ai_draft_and_action(mock_client_cls, lead, thread):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.generate_draft.return_value = ('Dear Kenji, great follow-up...', 'Context: intro email')

    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task(str(lead.id), str(thread.id))

    assert AIDraft.objects.filter(lead=lead, status=DraftStatus.PENDING_REVIEW).count() == 1
    assert lead.actions.filter(action_type=ActionType.AI_DRAFT_GENERATED).count() == 1


@pytest.mark.django_db
def test_generate_draft_skips_missing_lead():
    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000001')


@pytest.mark.django_db
@patch('ai_assistant.tasks.GeminiClient')
def test_generate_draft_stores_draft_content(mock_client_cls, lead, thread):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.generate_draft.return_value = ('Specific draft content here.', 'Summary text')

    from ai_assistant.tasks import generate_ai_draft_task
    generate_ai_draft_task(str(lead.id), str(thread.id))

    draft = AIDraft.objects.get(lead=lead)
    assert draft.draft_content == 'Specific draft content here.'
    assert draft.context_summary == 'Summary text'
