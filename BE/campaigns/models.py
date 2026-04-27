from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class CampaignStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'


class Product(TimestampedModel):
    name = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=50)
    cas_number = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    technical_specs = models.JSONField(default=dict)
    brochure_pdf = models.FileField(upload_to='brochures/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
    )

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Campaign(TimestampedModel):
    title = models.CharField(max_length=255)
    products = models.ManyToManyField(Product, related_name='campaigns', blank=True)
    country_filters = models.JSONField(default=list)
    num_transactions_yr = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns',
    )
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.ACTIVE,
    )

    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
