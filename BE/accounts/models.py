from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    smtp_password = models.CharField(max_length=255, blank=True, help_text='App password for sending emails via your Gmail account')

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
