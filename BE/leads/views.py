from django.db.models import Exists, OuterRef, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Lead, LeadAction, LeadStage, Contact, ActionType
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

    @action(detail=True, methods=['post'], url_path='send-intro')
    def send_intro(self, request, pk=None):
        from communications.tasks import async_task
        lead = self.get_object()

        if lead.stage != LeadStage.DISCOVERED:
            return Response(
                {'error': f'Lead must be in discovered stage, current: {lead.stage}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact = (
            lead.contacts
            .filter(email__isnull=False)
            .exclude(email='')
            .order_by('-is_primary')
            .first()
        )
        if not contact:
            return Response(
                {'error': 'No contact with email found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task('communications.tasks.send_intro_email_task', str(lead.id), str(contact.id))
        return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='send-pricing')
    def send_pricing(self, request, pk=None):
        from communications.tasks import async_task
        lead = self.get_object()

        if lead.stage != LeadStage.INTRO_SENT:
            return Response(
                {'error': f'Lead must be in intro_sent stage, current: {lead.stage}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact = (
            lead.contacts
            .filter(email__isnull=False)
            .exclude(email='')
            .order_by('-is_primary')
            .first()
        )
        if not contact:
            return Response(
                {'error': 'No contact with email found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task('communications.tasks.send_pricing_email_task', str(lead.id), str(contact.id))
        return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='bulk-send-intro')
    def bulk_send_intro(self, request):
        from communications.tasks import async_task
        lead_ids = request.data.get('lead_ids', [])
        if not lead_ids:
            return Response({'error': 'lead_ids required'}, status=status.HTTP_400_BAD_REQUEST)

        queued = 0
        for lead_id in lead_ids:
            try:
                lead = Lead.objects.prefetch_related('contacts').get(id=lead_id)
            except Lead.DoesNotExist:
                continue

            if lead.stage != LeadStage.DISCOVERED:
                continue

            contact = (
                lead.contacts
                .filter(email__isnull=False)
                .exclude(email='')
                .order_by('-is_primary')
                .first()
            )
            if not contact:
                continue

            async_task('communications.tasks.send_intro_email_task', str(lead.id), str(contact.id))
            queued += 1

        return Response({'queued': queued}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='generate-draft')
    def generate_draft(self, request, pk=None):
        from ai_assistant.tasks import async_task
        lead = self.get_object()

        thread = lead.threads.order_by('-created_at').first()
        if not thread:
            return Response(
                {'error': 'No email thread found for this lead. Send an intro email first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_draft = lead.ai_drafts.filter(status='pending_review').exists()
        if pending_draft:
            return Response(
                {'error': 'A pending draft already exists for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_task(
            'ai_assistant.tasks.generate_ai_draft_task',
            str(lead.id),
            str(thread.id),
        )
        return Response({'status': 'generating'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='schedule-meeting')
    def schedule_meeting(self, request, pk=None):
        from deals.services.calendar_invite import CalendarInviteService
        from deals.models import Meeting
        from deals.serializers import ScheduleMeetingSerializer, MeetingSerializer

        lead = self.get_object()
        serializer = ScheduleMeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            contact = lead.contacts.get(id=data['contact_id'])
        except Contact.DoesNotExist:
            return Response(
                {'error': 'Contact not found for this lead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calendar_service = CalendarInviteService()
        event_id = calendar_service.create_event(
            lead=lead,
            contact=contact,
            scheduled_at=data['scheduled_at'],
            meeting_link=data.get('meeting_link', ''),
        )

        meeting = Meeting.objects.create(
            lead=lead,
            contact=contact,
            scheduled_by=request.user,
            calendar_event_id=event_id,
            scheduled_at=data['scheduled_at'],
            meeting_link=data.get('meeting_link', ''),
            notes=data.get('notes', ''),
        )

        LeadAction.objects.create(
            lead=lead,
            performed_by=request.user,
            action_type=ActionType.MEETING_SCHEDULED,
            notes=f'Meeting scheduled for {data["scheduled_at"].strftime("%Y-%m-%d %H:%M UTC")}',
            metadata={'meeting_id': str(meeting.id)},
        )

        lead.stage = LeadStage.MEETING_SET
        lead.save(update_fields=['stage', 'updated_at'])

        return Response(MeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='meetings')
    def meetings(self, request, pk=None):
        from deals.models import Meeting
        from deals.serializers import MeetingSerializer

        lead = self.get_object()
        qs = lead.meetings.select_related('contact', 'scheduled_by').order_by('scheduled_at')
        return Response(MeetingSerializer(qs, many=True).data)


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
