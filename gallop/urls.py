from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

# 🔹 Swagger imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# 🔹 Swagger configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Gallop API",
        default_version='v1',
        description="Student Progress + AI Exam API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔹 Your app URLs
    path('', include('gallop_app.urls')),

    # 🔹 Swagger UI
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0)),
]

# 🔹 Media files (images) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)