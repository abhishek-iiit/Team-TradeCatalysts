from rest_framework import serializers
from .models import Meeting


class MeetingSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    lead_company_name = serializers.CharField(source='lead.company_name', read_only=True)
    scheduled_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'status', 'scheduled_at', 'meeting_link', 'notes',
            'calendar_event_id', 'contact_name', 'lead_company_name',
            'scheduled_by_email', 'created_at',
        ]

    def get_contact_name(self, obj):
        return f'{obj.contact.first_name} {obj.contact.last_name}'.strip()

    def get_scheduled_by_email(self, obj):
        return obj.scheduled_by.email if obj.scheduled_by else None


class ScheduleMeetingSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    contact_id = serializers.UUIDField()
    meeting_link = serializers.CharField(max_length=500, required=False, default='')
    notes = serializers.CharField(required=False, default='')


class MeetingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['status', 'meeting_link', 'notes']
