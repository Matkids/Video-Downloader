import os
import re
import uuid
import hashlib
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_safe_filename(title="", platform="", extension="mp4"):
    """Generate a safe filename for downloaded videos"""
    # Clean title: remove special characters, limit length
    safe_title = re.sub(r'[^\w\s-]', '', title)
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    safe_title = safe_title.strip('-')[:50]  # Limit to 50 characters

    # Generate unique identifier
    unique_id = str(uuid.uuid4())[:8]
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

    # Combine parts
    if safe_title:
        filename = f"{platform}_{safe_title}_{timestamp}_{unique_id}.{extension}"
    else:
        filename = f"{platform}_{timestamp}_{unique_id}.{extension}"

    return filename


def validate_url(url, platform=None):
    """Validate if URL is valid for the given platform"""
    if not url or not isinstance(url, str):
        return False, "Invalid URL format"

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"

        # Platform-specific validation
        platform_patterns = {
            'youtube': [
                r'youtube\.com/watch\?.*v=',
                r'youtu\.be/',
                r'youtube\.com/embed/',
            ],
            'facebook': [
                r'facebook\.com/',
                r'fb\.watch/',
                r'fb\.com/',
            ],
            'tiktok': [
                r'tiktok\.com/@[^/]+/video/',
                r'vm\.tiktok\.com/',
                r'tiktok\.com/t/',
            ],
            'instagram': [
                r'instagram\.com/p/',
                r'instagram\.com/reel/',
            ],
            'twitter': [
                r'twitter\.com/',
                r'x\.com/',
            ],
        }

        if platform and platform in platform_patterns:
            patterns = platform_patterns[platform]
            url_lower = url.lower()
            if not any(re.search(pattern, url_lower) for pattern in patterns):
                return False, f"URL does not match {platform} format"

        return True, "Valid URL"

    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def get_video_id_from_url(url, platform):
    """Extract video ID from platform-specific URL"""
    patterns = {
        'youtube': [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ],
        'tiktok': [
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
            r'tiktok\.com/t/([a-zA-Z0-9]+)',
        ],
        'instagram': [
            r'instagram\.com/p/([a-zA-Z0-9_-]+)',
            r'instagram\.com/reel/([a-zA-Z0-9_-]+)',
        ],
        'facebook': [
            r'facebook\.com/watch/(\d+)',
            r'fb\.watch/([a-zA-Z0-9]+)',
        ],
        'twitter': [
            r'twitter\.com/[^/]+/status/(\d+)',
            r'x\.com/[^/]+/status/(\d+)',
        ],
    }

    if platform in patterns:
        for pattern in patterns[platform]:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

    return None


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds):
    """Format duration in human readable format"""
    if not seconds:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def create_download_directory():
    """Create download directory if it doesn't exist"""
    download_path = Path(settings.MEDIA_ROOT) / 'downloads'
    download_path.mkdir(parents=True, exist_ok=True)
    return download_path


def create_temp_directory():
    """Create temporary directory for downloads"""
    temp_path = Path(settings.MEDIA_ROOT) / 'temp'
    temp_path.mkdir(parents=True, exist_ok=True)
    return temp_path


def cleanup_temp_files(max_age_hours=24):
    """Clean up temporary files older than specified hours"""
    import logging
    logger = logging.getLogger(__name__)

    temp_path = Path(settings.MEDIA_ROOT) / 'temp'
    if not temp_path.exists():
        return

    cutoff_time = timezone.now() - timezone.timedelta(hours=max_age_hours)
    cleaned_count = 0
    cleaned_size = 0

    for file_path in temp_path.glob('*'):
        if file_path.is_file():
            try:
                file_mtime = timezone.datetime.fromtimestamp(
                    file_path.stat().st_mtime,
                    tz=timezone.get_current_timezone()
                )

                if file_mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_count += 1
                    cleaned_size += file_size
                    logger.info(f"Cleaned up temp file: {file_path.name}")

            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {str(e)}")

    if cleaned_count > 0:
        logger.info(
            f"Temp cleanup: {cleaned_count} files, "
            f"{format_file_size(cleaned_size)} freed"
        )


def get_download_stats():
    """Get statistics about downloads"""
    from downloader.models import VideoDownload

    stats = {
        'total_downloads': VideoDownload.objects.count(),
        'completed_downloads': VideoDownload.objects.filter(status='completed').count(),
        'failed_downloads': VideoDownload.objects.filter(status='failed').count(),
        'pending_downloads': VideoDownload.objects.filter(status='pending').count(),
        'total_storage_used': 0,
    }

    # Calculate storage used
    completed_downloads = VideoDownload.objects.filter(status='completed')
    for download in completed_downloads:
        if download.file_size:
            stats['total_storage_used'] += download.file_size

    # Format storage size
    stats['total_storage_used_formatted'] = format_file_size(stats['total_storage_used'])

    # Platform breakdown
    platform_stats = {}
    for platform, _ in VideoDownload.PLATFORM_CHOICES:
        platform_count = VideoDownload.objects.filter(platform=platform).count()
        if platform_count > 0:
            platform_stats[platform] = platform_count

    stats['platform_breakdown'] = platform_stats

    return stats


def generate_thumbnail_from_video(video_path):
    """Generate thumbnail from video file (placeholder for future implementation)"""
    # This would require additional dependencies like ffmpeg-python
    # For now, return None
    return None


def check_rate_limit(user_ip, platform):
    """Check if user has exceeded rate limit for a platform"""
    from downloader.models import VideoDownload, PlatformConfig
    from django.utils import timezone

    try:
        config = PlatformConfig.objects.get(platform=platform)
    except PlatformConfig.DoesNotExist:
        return True, "Platform not configured"

    if config.rate_limit_per_hour <= 0:
        return True, "No rate limit configured"

    # Count downloads in the last hour
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    recent_downloads = VideoDownload.objects.filter(
        ip_address=user_ip,
        platform=platform,
        created_at__gte=one_hour_ago
    ).count()

    if recent_downloads >= config.rate_limit_per_hour:
        return False, f"Rate limit exceeded: {config.rate_limit_per_hour} downloads per hour"

    return True, "Rate limit OK"