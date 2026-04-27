from django.contrib import admin
from .models import AIDraft


@admin.register(AIDraft)
class AIDraftAdmin(admin.ModelAdmin):
    list_display = ['lead', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status']
