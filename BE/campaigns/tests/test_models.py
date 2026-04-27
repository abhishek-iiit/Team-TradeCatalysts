import pytest
from django.contrib.auth import get_user_model
from campaigns.models import Product, Campaign, CampaignStatus

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='seller', email='seller@test.com', password='pass'
    )


@pytest.mark.django_db
def test_product_creation(user):
    product = Product.objects.create(
        name='Acetone',
        hsn_code='29141100',
        cas_number='67-64-1',
        created_by=user,
    )
    assert product.name == 'Acetone'
    assert product.brochure_pdf.name is None
    assert str(product) == 'Acetone'


@pytest.mark.django_db
def test_campaign_creation(user):
    product = Product.objects.create(
        name='Acetone', hsn_code='29141100', cas_number='67-64-1', created_by=user
    )
    campaign = Campaign.objects.create(
        title='India Acetone Search',
        country_filters=['IN', 'US'],
        num_transactions_yr=10,
        created_by=user,
    )
    campaign.products.add(product)
    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.products.count() == 1
    assert str(campaign) == 'India Acetone Search'
