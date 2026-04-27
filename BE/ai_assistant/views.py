from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from communications.services.email_sender import GmailSMTPSender
from .models import AIDraft, DraftStatus
from .serializers import AIDraftSerializer


class AIDraftViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIDraftSerializer
    http_method_names = ['get', 'post']

    def get_queryset(self):
        qs = AIDraft.objects.select_related(
            'lead', 'thread', 'thread__contact', 'reviewed_by'
        ).order_by('-created_at')
        if self.action == 'list':
            return qs.filter(status=DraftStatus.PENDING_REVIEW)
        return qs

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed('POST')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        from leads.models import LeadAction, ActionType

        draft = self.get_object()
        if draft.status != DraftStatus.PENDING_REVIEW:
            return Response(
                {'error': 'Only pending_review drafts can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = request.data.get('reply_content') or draft.draft_content
        attachment = request.FILES.get('attachment')

        sender = GmailSMTPSender(user=request.user)
        sender.send_draft_reply(draft.thread, draft.thread.contact, content, attachment=attachment)

        draft.status = DraftStatus.SENT
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

        LeadAction.objects.create(
            lead=draft.lead,
            performed_by=request.user,
            action_type=ActionType.AI_DRAFT_APPROVED,
            notes='AI draft approved and sent.',
            metadata={'draft_id': str(draft.id)},
        )

        return Response(AIDraftSerializer(draft).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        from leads.models import LeadAction, ActionType

        draft = self.get_object()
        if draft.status != DraftStatus.PENDING_REVIEW:
            return Response(
                {'error': 'Only pending_review drafts can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        draft.status = DraftStatus.REJECTED
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

        LeadAction.objects.create(
            lead=draft.lead,
            performed_by=request.user,
            action_type=ActionType.AI_DRAFT_REJECTED,
            notes='AI draft rejected.',
            metadata={'draft_id': str(draft.id)},
        )

        return Response(AIDraftSerializer(draft).data)
