from rest_framework import serializers
from .models import AIDraft


class AIDraftSerializer(serializers.ModelSerializer):
    lead_id = serializers.UUIDField(source='lead.id', read_only=True)
    lead_company_name = serializers.CharField(source='lead.company_name', read_only=True)
    thread_subject = serializers.CharField(source='thread.subject', read_only=True)
    thread_type = serializers.CharField(source='thread.thread_type', read_only=True)
    reviewed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = AIDraft
        fields = [
            'id', 'status', 'draft_content', 'context_summary',
            'lead_id', 'lead_company_name',
            'thread_subject', 'thread_type',
            'reviewed_by_email', 'reviewed_at', 'created_at',
        ]

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None
