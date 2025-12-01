import os
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from downloader.models import VideoDownload

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old and failed downloads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete downloads older than this many days (default: 30)'
        )
        parser.add_argument(
            '--keep-completed',
            action='store_true',
            help='Keep completed downloads, only delete failed ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        keep_completed = options['keep_completed']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        self.stdout.write(
            f"Cleaning up downloads older than {days} days "
            f"(before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No files will be deleted"))

        # Get downloads to delete
        queryset = VideoDownload.objects.filter(created_at__lt=cutoff_date)

        if keep_completed:
            queryset = queryset.exclude(status='completed')

        downloads = queryset.select_related('user')

        if not downloads.exists():
            self.stdout.write(self.style.SUCCESS("No downloads found to clean up"))
            return

        total_size = 0
        deleted_count = 0
        file_errors = 0

        for download in downloads:
            file_size = 0

            # Delete associated file if it exists
            if download.downloaded_file:
                try:
                    file_size = download.downloaded_file.size
                    if not dry_run:
                        download.downloaded_file.delete(save=False)
                except Exception as e:
                    logger.error(f"Error deleting file for download {download.id}: {str(e)}")
                    file_errors += 1

            total_size += file_size

            # Delete the download record
            if not dry_run:
                try:
                    download.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting download record {download.id}: {str(e)}")
                    file_errors += 1
            else:
                deleted_count += 1

            # Display progress
            if dry_run:
                self.stdout.write(
                    f"Would delete: {download.platform} - "
                    f"{download.video_title[:50]}... "
                    f"({file_size / (1024*1024):.2f} MB)"
                )

        # Summary
        size_mb = total_size / (1024 * 1024)
        size_gb = size_mb / 1024

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup completed:\n"
                f"- Downloads processed: {len(downloads)}\n"
                f"- Downloads deleted: {deleted_count}\n"
                f"- File space freed: {size_mb:.2f} MB ({size_gb:.2f} GB)\n"
                f"- Errors encountered: {file_errors}"
            )
        )

        if file_errors > 0:
            self.stdout.write(
                self.style.WARNING(f"Encountered {file_errors} errors during cleanup")
            )