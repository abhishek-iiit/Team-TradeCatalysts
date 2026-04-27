from django.urls import path
from . import views

urlpatterns = [
    path('trade-data/preview/', views.preview, name='trade-data-preview'),
    path('trade-data/import/', views.import_leads, name='trade-data-import'),
    path('trade-data/explore/', views.explore, name='trade-data-explore'),
]
