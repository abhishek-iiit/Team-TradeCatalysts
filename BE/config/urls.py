from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('campaigns.urls')),
    path('api/', include('leads.urls')),
    path('api/', include('ai_assistant.urls')),
    path('api/', include('deals.urls')),
    path('api/', include('communications.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
