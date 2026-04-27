from rest_framework import serializers
from .models import EmailThread, EmailMessage


class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage
        fields = ['id', 'direction', 'body_text', 'sent_at', 'gmail_message_id']


class EmailThreadSerializer(serializers.ModelSerializer):
    messages = EmailMessageSerializer(many=True, read_only=True)
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = EmailThread
        fields = ['id', 'subject', 'thread_type', 'contact_name', 'messages', 'created_at']

    def get_contact_name(self, obj):
        return f'{obj.contact.first_name} {obj.contact.last_name}'.strip()


class InboxMessageSerializer(serializers.ModelSerializer):
    """Inbound email message with full thread + lead context."""
    thread_id = serializers.CharField(source='thread.id')
    thread_subject = serializers.CharField(source='thread.subject')
    thread_type = serializers.CharField(source='thread.thread_type')
    contact_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    lead_id = serializers.UUIDField(source='thread.lead.id')
    lead_company_name = serializers.CharField(source='thread.lead.company_name')
    lead_stage = serializers.CharField(source='thread.lead.stage')
    auto_flow_paused = serializers.BooleanField(source='thread.lead.auto_flow_paused')

    class Meta:
        model = EmailMessage
        fields = [
            'id', 'body_text', 'sent_at',
            'thread_id', 'thread_subject', 'thread_type',
            'contact_name', 'contact_email',
            'lead_id', 'lead_company_name', 'lead_stage', 'auto_flow_paused',
        ]

    def get_contact_name(self, obj):
        c = obj.thread.contact
        return f'{c.first_name} {c.last_name}'.strip()

    def get_contact_email(self, obj):
        return obj.thread.contact.email
