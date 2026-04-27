from django.contrib import admin
from .models import Product, Campaign


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'hsn_code', 'cas_number', 'created_by', 'created_at']
    search_fields = ['name', 'hsn_code', 'cas_number']
    list_filter = ['created_at']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    filter_horizontal = ['products']
