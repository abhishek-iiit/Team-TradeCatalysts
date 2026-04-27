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
