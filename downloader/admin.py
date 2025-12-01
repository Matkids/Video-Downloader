from django.contrib import admin
from .models import VideoDownload, PlatformConfig, DownloadHistory


@admin.register(VideoDownload)
class VideoDownloadAdmin(admin.ModelAdmin):
    list_display = [
        'video_title', 'platform', 'status', 'user', 'file_size_mb',
        'quality', 'download_count', 'created_at'
    ]
    list_filter = ['platform', 'status', 'quality', 'created_at']
    search_fields = ['video_title', 'original_url', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at', 'download_count']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'platform', 'original_url', 'status')
        }),
        ('Video Details', {
            'fields': ('video_title', 'video_description', 'video_duration', 'thumbnail_url')
        }),
        ('File Information', {
            'fields': ('downloaded_file', 'file_size', 'file_format', 'quality')
        }),
        ('Status & Progress', {
            'fields': ('progress_percentage', 'error_message')
        }),
        ('Metadata', {
            'fields': ('download_count', 'ip_address', 'user_agent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )

    def file_size_mb(self, obj):
        return obj.file_size_mb
    file_size_mb.short_description = 'File Size (MB)'


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = [
        'platform', 'is_active', 'max_file_size_mb', 'api_key_required',
        'rate_limit_per_hour', 'created_at'
    ]
    list_filter = ['is_active', 'api_key_required']
    search_fields = ['platform']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['platform']

    fieldsets = (
        ('Basic Configuration', {
            'fields': ('platform', 'is_active')
        }),
        ('Download Limits', {
            'fields': ('max_file_size_mb', 'rate_limit_per_hour')
        }),
        ('File Settings', {
            'fields': ('supported_formats',)
        }),
        ('API Configuration', {
            'fields': ('api_key_required', 'api_key')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'video_download', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['user__username', 'video_download__video_title', 'ip_address']
    readonly_fields = ['id', 'downloaded_at']
    ordering = ['-downloaded_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False