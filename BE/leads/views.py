from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Lead
from .serializers import LeadListSerializer


class LeadViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeadListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Lead.objects
            .select_related('campaign', 'assigned_to')
            .prefetch_related('contacts')
            .order_by('-created_at')
        )
