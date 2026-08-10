from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.metrics import metrics_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('metrics', metrics_view),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
