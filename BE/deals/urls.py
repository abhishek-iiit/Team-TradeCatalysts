from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('meetings', views.MeetingViewSet, basename='meeting')
router.register('deals', views.DealViewSet, basename='deal')

urlpatterns = [
    path('', include(router.urls)),
]
