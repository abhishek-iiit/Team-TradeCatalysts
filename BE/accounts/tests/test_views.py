import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='john', email='john@example.com', password='securepass123'
    )


@pytest.mark.django_db
def test_login_returns_tokens(api_client, user):
    response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'securepass123',
    })
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert response.data['user']['email'] == 'john@example.com'


@pytest.mark.django_db
def test_login_wrong_password_returns_401(api_client, user):
    response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'wrongpassword',
    })
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get('/api/auth/me/')
    assert response.status_code == 200
    assert response.data['email'] == 'john@example.com'


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get('/api/auth/me/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, user):
    login_response = api_client.post('/api/auth/login/', {
        'email': 'john@example.com',
        'password': 'securepass123',
    })
    refresh_token = login_response.data['refresh']
    access_token = login_response.data['access']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    response = api_client.post('/api/auth/logout/', {'refresh': refresh_token})
    assert response.status_code == 200
