from django.db.models import Exists, OuterRef, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Lead, LeadAction, LeadStage, Contact
from .serializers import (
    LeadListSerializer,
    LeadDetailSerializer,
    LeadActionSerializer,
    LeadUpdateSerializer,
)


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post']  # POST only via custom actions (e.g. actions_list)

    def create(self, request, *args, **kwargs):
        """Leads are created by the Volza ingestion task, not via the API."""
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('POST')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LeadDetailSerializer
        if self.action == 'partial_update':
            return LeadUpdateSerializer
        return LeadListSerializer

    def get_queryset(self):
        qs = Lead.objects.select_related('campaign', 'assigned_to').order_by('-created_at')
        if self.action == 'retrieve':
            return qs.prefetch_related(
                'contacts',
                'actions',
                'actions__performed_by',
            )
        return qs.prefetch_related('contacts')

    def partial_update(self, request, *args, **kwargs):
        lead = self.get_object()
        serializer = LeadUpdateSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Re-fetch with full relations for detail response
        lead = Lead.objects.select_related('campaign', 'assigned_to').prefetch_related(
            'contacts', 'actions', 'actions__performed_by'
        ).get(pk=lead.pk)
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=['get', 'post'], url_path='actions')
    def actions_list(self, request, pk=None):
        lead = self.get_object()
        if request.method == 'GET':
            qs = lead.actions.select_related('performed_by').order_by('-created_at')
            return Response(LeadActionSerializer(qs, many=True).data)
        serializer = LeadActionSerializer(
            data=request.data,
            context={'request': request, 'lead': lead},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='threads')
    def threads(self, request, pk=None):
        from communications.serializers import EmailThreadSerializer
        lead = self.get_object()
        qs = lead.threads.select_related('contact').prefetch_related('messages').order_by('-created_at')
        return Response(EmailThreadSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    from campaigns.models import Campaign, CampaignStatus

    total_leads = Lead.objects.count()
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE).count()

    stage_counts = {stage.value: 0 for stage in LeadStage}
    for stage in LeadStage:
        stage_counts[stage.value] = Lead.objects.filter(stage=stage).count()

    has_reachable_contact = Exists(
        Contact.objects.filter(lead=OuterRef('pk')).filter(
            Q(email__isnull=False) | Q(phone__isnull=False)
        )
    )
    missing_contact_count = (
        Lead.objects.annotate(has_contact=has_reachable_contact)
        .filter(has_contact=False)
        .count()
    )

    return Response({
        'total_leads': total_leads,
        'active_campaigns': active_campaigns,
        'leads_by_stage': stage_counts,
        'missing_contact_count': missing_contact_count,
    })
