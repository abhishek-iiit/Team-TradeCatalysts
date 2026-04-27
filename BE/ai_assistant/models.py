from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class DraftStatus(models.TextChoices):
    PENDING_REVIEW = 'pending_review', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    SENT = 'sent', 'Sent'


class AIDraft(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='ai_drafts'
    )
    thread = models.ForeignKey(
        'communications.EmailThread', on_delete=models.CASCADE, related_name='ai_drafts'
    )
    draft_content = models.TextField()
    context_summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=DraftStatus.choices, default=DraftStatus.PENDING_REVIEW
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_drafts',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_drafts'
        ordering = ['-created_at']

    def __str__(self):
        return f'Draft for {self.lead.company_name} ({self.status})'
