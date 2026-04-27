from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class LeadStage(models.TextChoices):
    DISCOVERED = 'discovered', 'Discovered'
    INTRO_SENT = 'intro_sent', 'Intro Sent'
    DOCUMENTS_SENT = 'documents_sent', 'Documents Sent'
    REQUIREMENTS_ASKED = 'requirements_asked', 'Requirements Asked'
    PRICING_SENT = 'pricing_sent', 'Pricing Sent'
    PRICING_FOLLOWUP = 'pricing_followup', 'Pricing Follow-Up'
    MEETING_SENT = 'meeting_sent', 'Meeting Sent'
    DEAL_SENT = 'deal_sent', 'Deal Sent'
    CLOSED_WON = 'closed_won', 'Closed Won'
    CLOSED_LOST = 'closed_lost', 'Closed Lost'


class Lead(TimestampedModel):
    campaign = models.ForeignKey(
        'campaigns.Campaign', on_delete=models.CASCADE, related_name='leads'
    )
    company_name = models.CharField(max_length=255)
    company_country = models.CharField(max_length=10)
    company_website = models.CharField(max_length=255, blank=True)
    stage = models.CharField(
        max_length=30, choices=LeadStage.choices, default=LeadStage.DISCOVERED
    )
    auto_flow_paused = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_leads',
    )
    volza_data = models.JSONField(default=dict)
    pricing_trend = models.JSONField(default=dict)
    purchase_history = models.JSONField(default=dict)

    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company_name} ({self.stage})'

    @property
    def has_missing_contact(self):
        return not self.contacts.filter(
            models.Q(email__isnull=False) | models.Q(phone__isnull=False)
        ).exists()


class ContactSource(models.TextChoices):
    VOLZA = 'volza', 'Volza'
    LUSHA = 'lusha', 'Lusha'
    MANUAL = 'manual', 'Manual'


class Contact(TimestampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    source = models.CharField(
        max_length=20, choices=ContactSource.choices, default=ContactSource.VOLZA
    )
    is_primary = models.BooleanField(default=False)
    lusha_raw = models.JSONField(default=dict)

    class Meta:
        db_table = 'contacts'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} @ {self.lead.company_name}'


class ActionType(models.TextChoices):
    INTRO_EMAIL = 'intro_email', 'Intro Email'
    INTRO_SMS = 'intro_sms', 'Intro SMS'
    DOCUMENTS_EMAIL = 'documents_email', 'Documents Email'
    DOCUMENTS_SMS = 'documents_sms', 'Documents SMS'
    REQUIREMENTS_EMAIL = 'requirements_email', 'Requirements Email'
    REQUIREMENTS_SMS = 'requirements_sms', 'Requirements SMS'
    PRICING_EMAIL = 'pricing_email', 'Pricing Email'
    PRICING_SMS = 'pricing_sms', 'Pricing SMS'
    PRICING_FOLLOWUP_EMAIL = 'pricing_followup_email', 'Pricing Follow-Up Email'
    PRICING_FOLLOWUP_SMS = 'pricing_followup_sms', 'Pricing Follow-Up SMS'
    MEETING_EMAIL = 'meeting_email', 'Meeting Email'
    MEETING_SMS = 'meeting_sms', 'Meeting SMS'
    DEAL_EMAIL = 'deal_email', 'Deal Email'
    DEAL_SMS = 'deal_sms', 'Deal SMS'
    FOLLOW_UP_CALL = 'follow_up_call', 'Follow Up Call'
    MEETING_SCHEDULED = 'meeting_scheduled', 'Meeting Scheduled'
    NOTE = 'note', 'Note'
    AI_DRAFT_GENERATED = 'ai_draft_generated', 'AI Draft Generated'
    AI_DRAFT_APPROVED = 'ai_draft_approved', 'AI Draft Approved'
    AI_DRAFT_REJECTED = 'ai_draft_rejected', 'AI Draft Rejected'
    DEAL_CLOSED = 'deal_closed', 'Deal Closed'
    MANUAL_TAKEOVER = 'manual_takeover', 'Manual Takeover'


class LeadAction(TimestampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='actions')
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lead_actions',
    )
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = 'lead_actions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action_type} on {self.lead.company_name}'
