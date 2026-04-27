from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('products', views.ProductViewSet, basename='product')
router.register('campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('', include(router.urls)),
]
