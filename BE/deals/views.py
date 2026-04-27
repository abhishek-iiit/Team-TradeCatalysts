from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Meeting
from .serializers import MeetingSerializer, MeetingUpdateSerializer


class MeetingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        return Meeting.objects.select_related(
            'lead', 'contact', 'scheduled_by'
        ).order_by('scheduled_at')

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return MeetingUpdateSerializer
        return MeetingSerializer

    def partial_update(self, request, *args, **kwargs):
        meeting = self.get_object()
        serializer = MeetingUpdateSerializer(meeting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeetingSerializer(serializer.instance).data)
