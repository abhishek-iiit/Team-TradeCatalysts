from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmailMessage, MessageDirection
from .serializers import InboxMessageSerializer
from .services.email_sender import GmailSMTPSender


class InboxViewSet(viewsets.ReadOnlyModelViewSet):
    """List inbound emails and allow reply + lead-stage control."""
    permission_classes = [IsAuthenticated]
    serializer_class = InboxMessageSerializer

    def get_queryset(self):
        return (
            EmailMessage.objects
            .filter(direction=MessageDirection.INBOUND)
            .select_related(
                'thread',
                'thread__contact',
                'thread__lead',
            )
            .order_by('-sent_at')
        )

    @action(detail=True, methods=['post'], url_path='reply')
    def reply(self, request, pk=None):
        """
        Reply to an inbound message. Optionally update lead stage and/or pause state.

        Body:
            reply_content (str): reply text
            set_stage     (str, optional): new LeadStage value
            pause_auto_flow (bool, optional): set lead.auto_flow_paused
        """
        message = self.get_object()
        reply_content = request.data.get('reply_content', '').strip()
        set_stage = request.data.get('set_stage')
        pause_auto_flow = request.data.get('pause_auto_flow')

        if not reply_content:
            return Response({'error': 'reply_content is required.'}, status=status.HTTP_400_BAD_REQUEST)

        thread = message.thread
        contact = thread.contact
        GmailSMTPSender().send_draft_reply(thread, contact, reply_content)

        lead = thread.lead
        update_fields = ['updated_at']

        if set_stage and set_stage != lead.stage:
            lead.stage = set_stage
            update_fields.append('stage')

        if pause_auto_flow is not None:
            lead.auto_flow_paused = bool(pause_auto_flow)
            update_fields.append('auto_flow_paused')

        lead.save(update_fields=update_fields)

        return Response({'status': 'sent', 'lead_stage': lead.stage, 'auto_flow_paused': lead.auto_flow_paused})

    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, pk=None):
        """Toggle auto_flow_paused on the lead without sending a reply."""
        message = self.get_object()
        lead = message.thread.lead
        lead.auto_flow_paused = not lead.auto_flow_paused
        lead.save(update_fields=['auto_flow_paused', 'updated_at'])
        return Response({'auto_flow_paused': lead.auto_flow_paused})

    @action(detail=True, methods=['post'], url_path='generate-reply')
    def generate_reply(self, request, pk=None):
        """Use Gemini to draft a reply for this inbound message thread."""
        from ai_assistant.services.gemini_client import GeminiClient
        message = self.get_object()
        thread = message.thread
        lead = thread.lead
        try:
            draft_content, _ = GeminiClient().generate_draft(lead, thread)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'draft': draft_content})
