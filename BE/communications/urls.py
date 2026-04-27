from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InboxViewSet

router = DefaultRouter()
router.register('inbox', InboxViewSet, basename='inbox')

urlpatterns = [
    path('', include(router.urls)),
]
