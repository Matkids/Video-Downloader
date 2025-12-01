from rest_framework import serializers
from .models import VideoDownload, PlatformConfig, DownloadHistory


class VideoDownloadSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quality_display = serializers.CharField(source='get_quality_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            'id', 'platform', 'platform_display', 'original_url', 'video_title',
            'video_description', 'video_duration', 'thumbnail_url', 'downloaded_file',
            'file_size', 'file_size_mb', 'file_format', 'quality', 'quality_display',
            'status', 'status_display', 'error_message', 'progress_percentage',
            'created_at', 'updated_at', 'completed_at', 'download_count',
            'file_url', 'download_url'
        ]
        read_only_fields = [
            'id', 'user', 'file_size', 'created_at', 'updated_at',
            'completed_at', 'download_count', 'error_message', 'status'
        ]

    def get_file_url(self, obj):
        if obj.downloaded_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.downloaded_file.url)
        return None

    def get_download_url(self, obj):
        if obj.downloaded_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/download/{obj.id}/')
        return None

    def validate_platform(self, value):
        from .models import VideoDownload
        valid_platforms = [choice[0] for choice in VideoDownload.PLATFORM_CHOICES]
        if value not in valid_platforms:
            raise serializers.ValidationError(f"Platform must be one of: {', '.join(valid_platforms)}")
        return value

    def validate_quality(self, value):
        from .models import VideoDownload
        valid_qualities = [choice[0] for choice in VideoDownload.QUALITY_CHOICES]
        if value not in valid_qualities:
            raise serializers.ValidationError(f"Quality must be one of: {', '.join(valid_qualities)}")
        return value


class PlatformConfigSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)

    class Meta:
        model = PlatformConfig
        fields = [
            'id', 'platform', 'platform_display', 'is_active', 'max_file_size_mb',
            'supported_formats', 'api_key_required', 'rate_limit_per_hour',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DownloadHistorySerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source='video_download.video_title', read_only=True)
    platform = serializers.CharField(source='video_download.platform', read_only=True)

    class Meta:
        model = DownloadHistory
        fields = ['id', 'video_download', 'video_title', 'platform', 'downloaded_at', 'ip_address']
        read_only_fields = ['id', 'downloaded_at']