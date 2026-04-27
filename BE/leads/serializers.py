from rest_framework import serializers
from .models import Lead, Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'designation',
            'email', 'phone', 'linkedin_url', 'source', 'is_primary',
        ]


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
