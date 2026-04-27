from django.db import models
from common.models import TimestampedModel


class ThreadType(models.TextChoices):
    INTRO = 'intro', 'Intro'
    PRICING = 'pricing', 'Pricing'
    FOLLOWUP = 'followup', 'Follow-Up'
    NEGOTIATION = 'negotiation', 'Negotiation'


class EmailThread(TimestampedModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='threads'
    )
    contact = models.ForeignKey(
        'leads.Contact', on_delete=models.CASCADE, related_name='threads'
    )
    subject = models.CharField(max_length=500)
    thread_type = models.CharField(max_length=20, choices=ThreadType.choices)
    gmail_thread_id = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'email_threads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.thread_type}: {self.subject}'


class MessageDirection(models.TextChoices):
    OUTBOUND = 'outbound', 'Outbound'
    INBOUND = 'inbound', 'Inbound'


class EmailMessage(TimestampedModel):
    thread = models.ForeignKey(
        EmailThread, on_delete=models.CASCADE, related_name='messages'
    )
    direction = models.CharField(max_length=10, choices=MessageDirection.choices)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    sent_at = models.DateTimeField()
    gmail_message_id = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'email_messages'
        ordering = ['sent_at']

    def __str__(self):
        return f'{self.direction} — {self.thread.subject}'
