from django.contrib import admin
from .models import Lead, Contact, LeadAction


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_country', 'stage', 'auto_flow_paused', 'assigned_to', 'created_at']
    list_filter = ['stage', 'auto_flow_paused', 'company_country']
    search_fields = ['company_name']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'source', 'is_primary']
    list_filter = ['source', 'is_primary']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(LeadAction)
class LeadActionAdmin(admin.ModelAdmin):
    list_display = ['lead', 'action_type', 'performed_by', 'created_at']
    list_filter = ['action_type', 'created_at']
