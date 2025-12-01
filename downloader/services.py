import os
import re
import uuid
import logging
from datetime import timedelta
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from django.conf import settings
from django.core.files import File
from .models import VideoDownload, PlatformConfig

logger = logging.getLogger(__name__)


class BaseDownloaderService:
    """Base class for all platform downloaders"""

    def __init__(self, video_download: VideoDownload):
        self.video_download = video_download
        self.platform_config = self.get_platform_config()

    def get_platform_config(self):
        try:
            return PlatformConfig.objects.get(platform=self.video_download.platform)
        except PlatformConfig.DoesNotExist:
            logger.error(f"No configuration found for platform: {self.video_download.platform}")
            return None

    def extract_video_id(self, url):
        """Extract video ID from URL - to be implemented by subclasses"""
        raise NotImplementedError

    def get_video_info(self, video_id):
        """Get video information - to be implemented by subclasses"""
        raise NotImplementedError

    def download_video(self, video_id, quality='high'):
        """Download video - to be implemented by subclasses"""
        raise NotImplementedError

    def process_download(self):
        """Main method to process the download"""
        try:
            self.video_download.status = 'downloading'
            self.video_download.save()

            # Extract video ID from URL
            video_id = self.extract_video_id(self.video_download.original_url)
            if not video_id:
                raise ValueError("Invalid video URL or could not extract video ID")

            # Get video information
            video_info = self.get_video_info(video_id)
            if video_info:
                self.video_download.video_title = video_info.get('title', '')
                self.video_download.video_description = video_info.get('description', '')
                self.video_download.video_duration = video_info.get('duration')
                self.video_download.thumbnail_url = video_info.get('thumbnail_url', '')
                self.video_download.save()

            # Download video
            file_path = self.download_video(video_id, self.video_download.quality)
            if file_path and os.path.exists(file_path):
                # Save file to model
                with open(file_path, 'rb') as f:
                    filename = os.path.basename(file_path)
                    self.video_download.downloaded_file.save(filename, File(f))

                # Update file info
                self.video_download.file_size = os.path.getsize(file_path)
                self.video_download.file_format = self.get_file_format(file_path)
                self.video_download.status = 'completed'
                self.video_download.progress_percentage = 100

                # Clean up temporary file
                os.remove(file_path)

                logger.info(f"Successfully downloaded: {self.video_download.video_title}")
            else:
                # Update progress to show failure
                self.video_download.status = 'failed'
                self.video_download.error_message = f"Download failed - no file returned from {self.video_download.platform}"
                self.video_download.save()
                raise ValueError(f"Download failed - no file returned from {self.video_download.platform}")

        except Exception as e:
            self.video_download.status = 'failed'
            self.video_download.error_message = str(e)
            logger.error(f"Download failed for {self.video_download.original_url}: {str(e)}")

        finally:
            self.video_download.save()

    def get_file_format(self, file_path):
        """Extract file format from file path"""
        return Path(file_path).suffix.lower().lstrip('.')


class YouTubeDownloader(BaseDownloaderService):
    """YouTube video downloader using yt-dlp"""

    def extract_video_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, video_id):
        """Get YouTube video information using yt-dlp"""
        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

                # Convert duration from seconds to timedelta
                duration_seconds = info.get('duration')
                duration = None
                if duration_seconds:
                    duration = timedelta(seconds=duration_seconds)

                return {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': duration,
                    'thumbnail_url': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                }
        except Exception as e:
            logger.error(f"Error getting YouTube video info: {str(e)}")
            return None

    def download_video(self, video_id, quality='high'):
        """Download YouTube video using yt-dlp"""
        try:
            import yt_dlp

            # Quality mapping
            quality_map = {
                'low': 'worst[ext=mp4]',
                'medium': 'worst[height<=720][ext=mp4]',
                'high': 'best[height<=1080][ext=mp4]',
                'highest': 'best[ext=mp4]/best'
            }

            format_selector = quality_map.get(quality, quality_map['high'])
            logger.info(f"Downloading YouTube video {video_id} with quality: {quality} ({format_selector})")

            # Create temporary download directory
            temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
            temp_dir.mkdir(exist_ok=True)

            # Generate unique filename
            temp_filename = f"youtube_{video_id}_{uuid.uuid4().hex[:8]}.mp4"
            temp_path = temp_dir / temp_filename

            ydl_opts = {
                'format': format_selector,
                'outtmpl': str(temp_path),
                'quiet': False,  # Enable logging for debugging
                'no_warnings': False,
                'extract_flat': False,
                'progress_hooks': [self._progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            if temp_path.exists():
                file_size = temp_path.stat().st_size
                logger.info(f"Successfully downloaded YouTube video to {temp_path} ({file_size} bytes)")
                return str(temp_path)
            else:
                logger.error(f"YouTube download failed - no file created at {temp_path}")
                return None

        except Exception as e:
            logger.error(f"Error downloading YouTube video: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            percent = d.get('percent', 0)
            if percent:
                self.video_download.progress_percentage = int(percent)
                self.video_download.save()
                logger.info(f"Download progress: {percent:.1f}%")
        elif d['status'] == 'finished':
            logger.info("Download completed successfully")
        elif d['status'] == 'error':
            logger.error(f"Download error: {d.get('error', 'Unknown error')}")


class FacebookDownloader(BaseDownloaderService):
    """Facebook video downloader"""

    def extract_video_id(self, url):
        """Extract Facebook video ID from URL"""
        # Facebook video URLs can be complex, so we'll return the URL as is
        # and let the downloader handle it
        return self.video_download.original_url

    def get_video_info(self, video_id):
        """Get Facebook video information"""
        # For Facebook, we might need to use a different approach
        # This is a placeholder implementation
        return {
            'title': 'Facebook Video',
            'description': '',
            'duration': timedelta(seconds=0),
            'thumbnail_url': '',
        }

    def download_video(self, video_id, quality='high'):
        """Download Facebook video using yt-dlp"""
        try:
            import yt_dlp

            temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
            temp_dir.mkdir(exist_ok=True)

            temp_filename = f"facebook_{uuid.uuid4().hex[:8]}.mp4"
            temp_path = temp_dir / temp_filename

            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': str(temp_path),
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_id])

            if temp_path.exists():
                return str(temp_path)
            else:
                return None

        except Exception as e:
            logger.error(f"Error downloading Facebook video: {str(e)}")
            return None


class TikTokDownloader(BaseDownloaderService):
    """TikTok video downloader"""

    def extract_video_id(self, url):
        """Extract TikTok video ID from URL"""
        patterns = [
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
            r'tiktok\.com/t/([a-zA-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, video_id):
        """Get TikTok video information"""
        return {
            'title': 'TikTok Video',
            'description': '',
            'duration': timedelta(seconds=0),
            'thumbnail_url': '',
        }

    def download_video(self, video_id, quality='high'):
        """Download TikTok video using yt-dlp"""
        try:
            import yt_dlp

            temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
            temp_dir.mkdir(exist_ok=True)

            temp_filename = f"tiktok_{uuid.uuid4().hex[:8]}.mp4"
            temp_path = temp_dir / temp_filename

            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': str(temp_path),
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_download.original_url])

            if temp_path.exists():
                return str(temp_path)
            else:
                return None

        except Exception as e:
            logger.error(f"Error downloading TikTok video: {str(e)}")
            return None


def get_downloader_service(platform: str, video_download: VideoDownload) -> BaseDownloaderService:
    """Factory function to get appropriate downloader service"""

    downloaders = {
        'youtube': YouTubeDownloader,
        'facebook': FacebookDownloader,
        'tiktok': TikTokDownloader,
    }

    downloader_class = downloaders.get(platform)
    if not downloader_class:
        raise ValueError(f"Unsupported platform: {platform}")

    return downloader_class(video_download)