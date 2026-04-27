from rest_framework import serializers
from .models import Lead, Contact, LeadAction


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'designation',
            'email', 'phone', 'linkedin_url', 'source', 'is_primary',
        ]


class LeadActionSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = LeadAction
        fields = [
            'id', 'action_type', 'notes', 'metadata',
            'performed_by_email', 'created_at',
        ]
        read_only_fields = ['id', 'performed_by_email', 'created_at']

    def get_performed_by_email(self, obj):
        return obj.performed_by.email if obj.performed_by else None

    def create(self, validated_data):
        validated_data['performed_by'] = self.context['request'].user
        validated_data['lead'] = self.context['lead']
        return super().create(validated_data)


class LeadListSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)
    has_missing_contact = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'company_name', 'company_country', 'company_website',
            'stage', 'auto_flow_paused', 'has_missing_contact',
            'contacts', 'created_at', 'updated_at',
        ]

    def get_has_missing_contact(self, obj):
        return obj.has_missing_contact


class LeadDetailSerializer(LeadListSerializer):
    actions = LeadActionSerializer(many=True, read_only=True)

    class Meta(LeadListSerializer.Meta):
        fields = [
            'id', 'company_name', 'company_country', 'company_website',
            'stage', 'auto_flow_paused', 'has_missing_contact',
            'contacts', 'actions',
            'volza_data', 'pricing_trend', 'purchase_history',
            'created_at', 'updated_at',
        ]


class LeadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['stage', 'auto_flow_paused']
