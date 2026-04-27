import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from campaigns.models import Product, Campaign, CampaignStatus

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
def product(user):
    return Product.objects.create(
        name='Acetone', hsn_code='29141100', cas_number='67-64-1', created_by=user
    )


# ── Product tests ──

@pytest.mark.django_db
def test_list_products(auth_client, product):
    response = auth_client.get('/api/products/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['name'] == 'Acetone'


@pytest.mark.django_db
def test_create_product(auth_client):
    response = auth_client.post('/api/products/', {
        'name': 'Ethanol', 'hsn_code': '22071000', 'cas_number': '64-17-5'
    })
    assert response.status_code == 201
    assert Product.objects.filter(name='Ethanol').exists()


@pytest.mark.django_db
def test_delete_product(auth_client, product):
    response = auth_client.delete(f'/api/products/{product.id}/')
    assert response.status_code == 204
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_products_requires_auth(api_client):
    response = api_client.get('/api/products/')
    assert response.status_code == 401


# ── Campaign tests ──

@pytest.mark.django_db
def test_create_campaign_triggers_task(auth_client, product):
    from unittest.mock import patch
    with patch('campaigns.views.async_task') as mock_task:
        response = auth_client.post('/api/campaigns/', {
            'title': 'India Campaign',
            'product_ids': [str(product.id)],
            'country_filters': ['IN', 'US'],
            'num_transactions_yr': 10,
        }, format='json')
    assert response.status_code == 201
    assert mock_task.called
    assert Campaign.objects.filter(title='India Campaign').exists()


@pytest.mark.django_db
def test_list_campaigns_includes_lead_count(auth_client, user, product):
    from unittest.mock import patch
    from leads.models import Lead
    with patch('campaigns.views.async_task'):
        auth_client.post('/api/campaigns/', {
            'title': 'Test',
            'product_ids': [str(product.id)],
            'country_filters': ['IN'],
            'num_transactions_yr': 5,
        }, format='json')
    campaign = Campaign.objects.get(title='Test')
    Lead.objects.create(campaign=campaign, company_name='Corp A', company_country='IN')
    response = auth_client.get('/api/campaigns/')
    assert response.status_code == 200
    assert response.data[0]['lead_count'] == 1


@pytest.mark.django_db
def test_campaign_leads_endpoint(auth_client, user, product):
    from unittest.mock import patch
    from leads.models import Lead
    with patch('campaigns.views.async_task'):
        resp = auth_client.post('/api/campaigns/', {
            'title': 'Test',
            'product_ids': [str(product.id)],
            'country_filters': ['IN'],
            'num_transactions_yr': 5,
        }, format='json')
    campaign_id = resp.data['id']
    campaign = Campaign.objects.get(id=campaign_id)
    Lead.objects.create(campaign=campaign, company_name='Corp A', company_country='IN')
    Lead.objects.create(campaign=campaign, company_name='Corp B', company_country='US')
    response = auth_client.get(f'/api/campaigns/{campaign_id}/leads/')
    assert response.status_code == 200
    assert len(response.data) == 2
