from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('leads', views.LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
]
