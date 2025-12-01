import os
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.models import User
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import VideoDownload, PlatformConfig, DownloadHistory
from .services import get_downloader_service
from .serializers import VideoDownloadSerializer, PlatformConfigSerializer
from .utils import get_client_ip

logger = logging.getLogger(__name__)


def home(request):
    """Home page with video download interface"""
    return render(request, 'downloader/home.html')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def supported_platforms(request):
    """Get list of supported platforms"""
    platforms = VideoDownload.PLATFORM_CHOICES
    platform_data = [{'value': choice[0], 'label': choice[1]} for choice in platforms]
    return Response({'platforms': platform_data})


class VideoDownloadAPIView(APIView):
    """API endpoint for video downloads"""
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Create a new video download request"""
        serializer = VideoDownloadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get platform configuration
                platform = serializer.validated_data['platform']
                platform_config = PlatformConfig.objects.filter(platform=platform, is_active=True).first()

                if not platform_config:
                    return Response(
                        {'error': f'Platform {platform} is not supported or inactive'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create video download instance
                video_download = serializer.save(
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # Start download process
                try:
                    downloader_service = get_downloader_service(platform, video_download)
                    # In a real application, you might want to use Celery for background tasks
                    downloader_service.process_download()

                    return Response(
                        VideoDownloadSerializer(video_download).data,
                        status=status.HTTP_201_CREATED
                    )
                except Exception as e:
                    logger.error(f"Download failed: {str(e)}")
                    return Response(
                        {'error': f'Download failed: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            except Exception as e:
                logger.error(f"Error processing download request: {str(e)}")
                return Response(
                    {'error': 'Internal server error'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get list of video downloads for authenticated user"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        downloads = VideoDownload.objects.filter(user=request.user).order_by('-created_at')
        serializer = VideoDownloadSerializer(downloads, many=True)
        return Response(serializer.data)


class VideoDownloadDetailView(APIView):
    """API endpoint for specific video download details"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        """Get details of a specific video download"""
        try:
            video_download = VideoDownload.objects.get(pk=pk)

            # Check if user has permission to view this download
            if video_download.user and video_download.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = VideoDownloadSerializer(video_download, context={'request': request})
            return Response(serializer.data)

        except VideoDownload.DoesNotExist:
            return Response(
                {'error': 'Download not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, pk):
        """Delete a video download"""
        try:
            video_download = VideoDownload.objects.get(pk=pk)

            # Check if user has permission to delete this download
            if video_download.user and video_download.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Delete file if exists
            if video_download.downloaded_file:
                video_download.downloaded_file.delete(save=False)

            video_download.delete()
            return Response(
                {'message': 'Download deleted successfully'},
                status=status.HTTP_200_OK
            )

        except VideoDownload.DoesNotExist:
            return Response(
                {'error': 'Download not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_url(request):
    """Validate if URL is supported for download"""
    url = request.data.get('url')
    platform = request.data.get('platform')

    if not url or not platform:
        return Response(
            {'error': 'URL and platform are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if platform is supported
    supported_platforms = [choice[0] for choice in VideoDownload.PLATFORM_CHOICES]
    if platform not in supported_platforms:
        return Response(
            {'error': f'Platform {platform} is not supported'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check platform configuration
    platform_config = PlatformConfig.objects.filter(platform=platform, is_active=True).first()
    if not platform_config:
        return Response(
            {'error': f'Platform {platform} is not active'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Create a temporary video download to test URL extraction
        temp_download = VideoDownload(platform=platform, original_url=url)
        downloader_service = get_downloader_service(platform, temp_download)
        video_id = downloader_service.extract_video_id(url)

        if not video_id:
            return Response(
                {'error': 'Invalid URL format for this platform'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'valid': True,
            'platform': platform,
            'video_id': video_id
        })

    except Exception as e:
        logger.error(f"URL validation failed: {str(e)}")
        return Response(
            {'error': 'URL validation failed'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def platform_configs(request):
    """Get platform configurations (admin only)"""
    configs = PlatformConfig.objects.all()
    serializer = PlatformConfigSerializer(configs, many=True)
    return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class FileDownloadView(View):
    """Handle file downloads"""

    def get(self, request, pk):
        """Download video file"""
        try:
            video_download = get_object_or_404(VideoDownload, pk=pk)

            # Check if user has permission to download
            if video_download.user and video_download.user != request.user:
                if not request.user.is_authenticated:
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=401
                    )
                if not request.user.is_staff:
                    return JsonResponse(
                        {'error': 'Permission denied'},
                        status=403
                    )

            # Check if file exists
            if not video_download.downloaded_file:
                return JsonResponse(
                    {'error': 'File not available'},
                    status=404
                )

            # Increment download count
            video_download.download_count += 1
            video_download.save(update_fields=['download_count'])

            # Log download history
            if request.user.is_authenticated:
                DownloadHistory.objects.create(
                    user=request.user,
                    video_download=video_download,
                    ip_address=get_client_ip(request)
                )

            # Serve file
            file_path = video_download.downloaded_file.path
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    response = HttpResponse(
                        f.read(),
                        content_type='application/octet-stream'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    response['Content-Length'] = os.path.getsize(file_path)
                    return response
            else:
                return JsonResponse(
                    {'error': 'File not found'},
                    status=404
                )

        except Exception as e:
            logger.error(f"File download error: {str(e)}")
            return JsonResponse(
                {'error': 'Download failed'},
                status=500
            )




@csrf_exempt
@require_http_methods(["POST"])
def webhook_download_complete(request):
    """Webhook for async download completion (for future use with Celery)"""
    try:
        download_id = request.POST.get('download_id')
        status = request.POST.get('status')
        error_message = request.POST.get('error_message', '')

        video_download = VideoDownload.objects.get(pk=download_id)
        video_download.status = status
        if error_message:
            video_download.error_message = error_message

        if status == 'completed':
            video_download.progress_percentage = 100

        video_download.save()

        return JsonResponse({'status': 'success'})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse(
            {'error': 'Webhook failed'},
            status=500
        )