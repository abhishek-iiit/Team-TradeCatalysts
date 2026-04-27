from django.contrib import admin
from .models import Meeting, Deal


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['lead', 'contact', 'scheduled_at', 'status']
    list_filter = ['status']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['lead', 'outcome', 'closed_by', 'closed_at', 'deal_value']
    list_filter = ['outcome']
