from rest_framework import serializers
from .models import Product, Campaign, ProductStageConfig


class ProductSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    has_brochure = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'hsn_code', 'cas_number', 'description',
            'technical_specs', 'brochure_pdf', 'has_brochure',
            'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by_email', 'has_brochure', 'created_at', 'updated_at']

    def get_has_brochure(self, obj):
        return bool(obj.brochure_pdf)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProductStageConfigSerializer(serializers.ModelSerializer):
    has_document = serializers.SerializerMethodField()

    class Meta:
        model = ProductStageConfig
        fields = [
            'id', 'product', 'stage', 'subject_line', 'email_content',
            'document', 'has_document', 'trigger_days', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'has_document', 'created_at', 'updated_at']

    def get_has_document(self, obj):
        return bool(obj.document and obj.document.name)


class CampaignSerializer(serializers.ModelSerializer):
    product_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=True
    )
    products = ProductSerializer(many=True, read_only=True)
    lead_count = serializers.IntegerField(read_only=True, default=0)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id', 'title', 'product_ids', 'products', 'country_filters',
            'num_transactions_yr', 'data_year', 'status', 'lead_count',
            'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'lead_count', 'created_by_email', 'created_at', 'updated_at']

    def create(self, validated_data):
        product_ids = validated_data.pop('product_ids', [])
        validated_data['created_by'] = self.context['request'].user
        campaign = super().create(validated_data)
        campaign.products.set(product_ids)
        return campaign
