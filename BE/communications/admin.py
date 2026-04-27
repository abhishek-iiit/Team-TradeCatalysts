from django.contrib import admin
from .models import EmailThread, EmailMessage


@admin.register(EmailThread)
class EmailThreadAdmin(admin.ModelAdmin):
    list_display = ['subject', 'thread_type', 'lead', 'contact', 'created_at']
    list_filter = ['thread_type']


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ['thread', 'direction', 'sent_at']
    list_filter = ['direction']
