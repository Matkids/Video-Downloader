from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class VideoDownload(models.Model):
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('facebook', 'Facebook'),
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    QUALITY_CHOICES = [
        ('low', 'Low (360p)'),
        ('medium', 'Medium (720p)'),
        ('high', 'High (1080p)'),
        ('highest', 'Highest Available'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    original_url = models.URLField(max_length=2048)
    video_title = models.CharField(max_length=500, blank=True)
    video_description = models.TextField(blank=True)
    video_duration = models.DurationField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=2048, blank=True)

    # File information
    downloaded_file = models.FileField(upload_to='downloads/', null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    file_format = models.CharField(max_length=10, blank=True)  # mp4, mp3, etc.
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='high')

    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    progress_percentage = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Additional metadata
    download_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['platform']),
        ]

    def __str__(self):
        return f"{self.platform} - {self.video_title or self.original_url[:50]}"

    @property
    def file_size_mb(self):
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video_download = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    class Meta:
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['user', 'downloaded_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.video_download.video_title}"


class PlatformConfig(models.Model):
    platform = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    max_file_size_mb = models.IntegerField(default=100)
    supported_formats = models.JSONField(default=list)  # ['mp4', 'mp3', 'webm']
    api_key_required = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, blank=True)
    rate_limit_per_hour = models.IntegerField(default=60)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform']

    def __str__(self):
        return f"{self.platform.title()} Config"