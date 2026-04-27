from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from campaigns.tasks import async_task
from leads.serializers import LeadListSerializer
from leads.models import Lead
from .models import Product, Campaign, ProductStageConfig, ProductEmailStage
from .serializers import ProductSerializer, CampaignSerializer, ProductStageConfigSerializer

_STAGE_ORDER = [
    ProductEmailStage.INTRO,
    ProductEmailStage.DOCUMENTS,
    ProductEmailStage.REQUIREMENTS,
    ProductEmailStage.PRICING,
    ProductEmailStage.FOLLOWUP,
    ProductEmailStage.MEETING,
    ProductEmailStage.DEAL,
]

_STAGE_DEFAULT_DAYS = {
    'intro': 3,
    'documents': 3,
    'requirements': 2,
    'pricing': 3,
    'followup': 2,
    'meeting': 5,
    'deal': 0,
}


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Product.objects.select_related('created_by').order_by('-created_at')

    @action(detail=True, methods=['get'], url_path='stage-configs')
    def stage_configs(self, request, pk=None):
        product = self.get_object()
        existing = {c.stage: c for c in product.stage_configs.all()}
        result = []
        for stage in _STAGE_ORDER:
            if stage.value in existing:
                result.append(ProductStageConfigSerializer(existing[stage.value]).data)
            else:
                result.append({
                    'id': None,
                    'product': str(product.id),
                    'stage': stage.value,
                    'subject_line': '',
                    'email_content': '',
                    'document': None,
                    'has_document': False,
                    'trigger_days': _STAGE_DEFAULT_DAYS.get(stage.value, 4),
                })
        return Response(result)


class ProductStageConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductStageConfigSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        qs = ProductStageConfig.objects.select_related('product')
        product_id = self.request.query_params.get('product_id')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return (
            Campaign.objects
            .select_related('created_by')
            .prefetch_related('products')
            .annotate(lead_count=Count('leads'))
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        campaign = serializer.save()
        async_task('campaigns.tasks.enrich_leads_from_volza', str(campaign.id))

    @action(detail=True, methods=['get'], url_path='leads')
    def leads(self, request, pk=None):
        campaign = self.get_object()
        stage = request.query_params.get('stage')
        qs = Lead.objects.filter(campaign=campaign).select_related(
            'campaign', 'campaign__created_by', 'assigned_to'
        ).prefetch_related('contacts')
        if stage:
            qs = qs.filter(stage=stage)
        serializer = LeadListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='export-missing')
    def export_missing(self, request, pk=None):
        import csv
        import io
        from django.http import HttpResponse

        campaign = self.get_object()
        missing_leads = [
            lead for lead in campaign.leads.prefetch_related('contacts').all()
            if lead.has_missing_contact
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Company Name', 'Country', 'Website', 'Notes'])
        for lead in missing_leads:
            writer.writerow([
                lead.company_name,
                lead.company_country,
                lead.company_website,
                'No email or phone found',
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="missing-contacts-{campaign.id}.csv"'
        return response
