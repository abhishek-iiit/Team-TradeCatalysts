import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_create_with_email():
    user = User.objects.create_user(
        username='john',
        email='john@example.com',
        password='securepass123'
    )
    assert user.email == 'john@example.com'
    assert user.check_password('securepass123')
    assert str(user) == 'john@example.com'


@pytest.mark.django_db
def test_user_email_is_unique():
    User.objects.create_user(username='a', email='same@example.com', password='pass')
    with pytest.raises(Exception):
        User.objects.create_user(username='b', email='same@example.com', password='pass')
