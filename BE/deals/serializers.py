from rest_framework import serializers
from .models import Meeting, Deal


class DealSerializer(serializers.ModelSerializer):
    closed_by_email = serializers.SerializerMethodField()
    lead_company_name = serializers.CharField(source='lead.company_name', read_only=True)

    class Meta:
        model = Deal
        fields = [
            'id', 'outcome', 'closed_at', 'remarks', 'deal_value',
            'closed_by_email', 'lead_company_name', 'created_at',
        ]

    def get_closed_by_email(self, obj):
        return obj.closed_by.email if obj.closed_by else None


class CloseDealSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['won', 'lost'])
    remarks = serializers.CharField(required=False, default='', allow_blank=True)
    deal_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )


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
    notes = serializers.CharField(required=False, default='')


class MeetingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['status', 'meeting_link', 'notes']
