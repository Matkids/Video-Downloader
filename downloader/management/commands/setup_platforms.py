from django.core.management.base import BaseCommand
from downloader.models import PlatformConfig


class Command(BaseCommand):
    help = 'Setup default platform configurations'

    def handle(self, *args, **options):
        platforms_config = [
            {
                'platform': 'youtube',
                'is_active': True,
                'max_file_size_mb': 500,
                'supported_formats': ['mp4', 'webm', 'mp3'],
                'api_key_required': False,
                'rate_limit_per_hour': 100,
            },
            {
                'platform': 'facebook',
                'is_active': True,
                'max_file_size_mb': 200,
                'supported_formats': ['mp4'],
                'api_key_required': False,
                'rate_limit_per_hour': 50,
            },
            {
                'platform': 'tiktok',
                'is_active': True,
                'max_file_size_mb': 100,
                'supported_formats': ['mp4'],
                'api_key_required': False,
                'rate_limit_per_hour': 60,
            },
            {
                'platform': 'instagram',
                'is_active': True,
                'max_file_size_mb': 150,
                'supported_formats': ['mp4'],
                'api_key_required': False,
                'rate_limit_per_hour': 50,
            },
            {
                'platform': 'twitter',
                'is_active': True,
                'max_file_size_mb': 100,
                'supported_formats': ['mp4'],
                'api_key_required': False,
                'rate_limit_per_hour': 50,
            },
        ]

        created_count = 0
        updated_count = 0

        for config_data in platforms_config:
            platform = config_data['platform']
            config, created = PlatformConfig.objects.update_or_create(
                platform=platform,
                defaults=config_data
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created platform config for {platform}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Updated platform config for {platform}')
                )
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully setup platform configurations: '
                f'{created_count} created, {updated_count} updated'
            )
        )