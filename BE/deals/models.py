from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class MeetingStatus(models.TextChoices):
    PROPOSED = 'proposed', 'Proposed'
    CONFIRMED = 'confirmed', 'Confirmed'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Meeting(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='meetings'
    )
    contact = models.ForeignKey(
        'leads.Contact', on_delete=models.CASCADE, related_name='meetings'
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_meetings',
    )
    calendar_event_id = models.CharField(max_length=200, blank=True)
    scheduled_at = models.DateTimeField()
    meeting_link = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=MeetingStatus.choices, default=MeetingStatus.PROPOSED
    )

    class Meta:
        db_table = 'meetings'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f'Meeting with {self.lead.company_name} at {self.scheduled_at}'


class DealOutcome(models.TextChoices):
    WON = 'won', 'Won'
    LOST = 'lost', 'Lost'


class Deal(TimestampedModel):
    lead = models.OneToOneField(
        'leads.Lead', on_delete=models.CASCADE, related_name='deal'
    )
    outcome = models.CharField(max_length=10, choices=DealOutcome.choices)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='closed_deals',
    )
    closed_at = models.DateTimeField()
    remarks = models.TextField(blank=True)
    deal_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'deals'
        ordering = ['-closed_at']

    def __str__(self):
        return f'Deal {self.outcome} — {self.lead.company_name}'
