from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('schema/', SpectacularAPIView.as_view(authentication_classes=[], permission_classes=[permissions.AllowAny]), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema', authentication_classes=[], permission_classes=[permissions.AllowAny]), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema', authentication_classes=[], permission_classes=[permissions.AllowAny]), name='redoc'),
]

urlpatterns += [
    path('api/v1/accounts/', include('apps.v1.accounts.urls')),
    path('api/v1/plans/', include('apps.v1.plans.urls')),
    path('api/v1/chat/', include('apps.v1.chat.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT, }, ), ]