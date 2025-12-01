from django.urls import path
from . import views

app_name = 'downloader_api'

urlpatterns = [
    # API endpoints
    path('', views.VideoDownloadAPIView.as_view(), name='video-download-api'),
    path('<uuid:pk>/', views.VideoDownloadDetailView.as_view(), name='video-download-detail'),
    path('download/<uuid:pk>/', views.FileDownloadView.as_view(), name='file-download'),
    path('validate-url/', views.validate_url, name='validate-url'),
    path('platforms/', views.supported_platforms, name='supported-platforms'),
    path('configs/', views.platform_configs, name='platform-configs'),
    path('webhook/download-complete/', views.webhook_download_complete, name='webhook-download-complete'),
]