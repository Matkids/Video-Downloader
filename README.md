# Video Downloader Application

A powerful Django-based web application for downloading videos from multiple platforms including YouTube, Facebook, TikTok, Instagram, and Twitter.

## Features

- **Multi-Platform Support**: Download videos from YouTube, Facebook, TikTok, Instagram, and Twitter
- **Quality Options**: Choose from multiple video quality options (Low, Medium, High, Highest)
- **REST API**: Comprehensive REST API for integration with other applications
- **User Authentication**: Support for user accounts and download history
- **Progress Tracking**: Real-time download progress monitoring
- **Admin Interface**: Full Django admin interface for managing downloads and configurations
- **Responsive Design**: Mobile-friendly web interface
- **Secure Downloads**: Secure file handling and download management

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5, JavaScript
- **Video Processing**: yt-dlp
- **Task Queue**: Celery with Redis (optional for background tasks)

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (optional, for background tasks)
- Node.js (optional, for asset management)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Video_Downloader
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Required Directories

```bash
# Create media directory for storing downloaded videos
mkdir -p media/downloads

# Create logs directory for application logs
mkdir -p logs

# Set proper permissions for media directory (Linux/Mac)
chmod 755 media/
chmod 755 media/downloads/
```

### 5. Environment Configuration

```bash
cp .env.example .env
# Edit .env file with your configuration
```

Edit the `.env` file with your database credentials and other settings:

```env
# Database Configuration
DB_NAME=video_downloader_db
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Security
SECRET_KEY=your-very-secret-key-here
DEBUG=True

# Media and Static Files
MEDIA_ROOT=/path/to/your/project/media
STATIC_ROOT=/path/to/your/project/staticfiles
```

### 6. Database Setup

```bash
# Create PostgreSQL database
createdb video_downloader_db

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic
```

### 9. Start Development Server

```bash
python manage.py runserver
```

## Configuration

### Database and Media Settings

Update the `settings.py` file with your PostgreSQL credentials and media settings:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'video_downloader_db'),
        'USER': os.getenv('DB_USER', 'your_username'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Media and Static Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Download settings
DOWNLOAD_DIR = os.path.join(MEDIA_ROOT, 'downloads')
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

### Platform Configuration

Access the Django admin interface to configure platform-specific settings:

1. Go to `/admin/`
2. Navigate to "Platform configs"
3. Configure each platform's settings including:
   - Maximum file size
   - Supported formats
   - Rate limits
   - API keys (if required)

## API Endpoints

### Download API
- `POST /api/` - Create a new download request
- `GET /api/` - List user's downloads (authenticated)
- `GET /api/{id}/` - Get download details
- `DELETE /api/{id}/` - Delete a download
- `GET /api/download/{id}/` - Download the video file

### Utility Endpoints
- `GET /api/platforms/` - Get supported platforms
- `POST /api/validate-url/` - Validate video URL
- `GET /api/configs/` - Get platform configurations (admin only)

## Usage

### Web Interface

1. Visit the home page
2. Paste the video URL
3. Select the platform and quality
4. Click "Download Video"
5. Monitor progress and download when complete

### API Usage

```bash
# Create download request
curl -X POST http://localhost:8000/api/ \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "platform": "youtube",
    "quality": "high"
  }'

# Check download status
curl -X GET http://localhost:8000/api/{download_id}/

# Download video file
curl -X GET http://localhost:8000/api/download/{download_id}/ -o video.mp4
```

## File Structure

```
Video_Downloader/
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── .env                    # Configuration file (create from .env.example)
├── video_downloader/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── downloader/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── services.py
│   └── urls.py
├── templates/
│   └── downloader/
│       └── home.html
├── static/                 # Static files (CSS, JavaScript, images)
│   ├── css/
│   ├── js/
│   └── images/
├── staticfiles/            # Collected static files (created by collectstatic)
├── media/                  # User uploaded and downloaded files
│   └── downloads/          # Downloaded video files stored here
└── logs/                   # Application logs
    ├── django.log
    └── downloader.log
```

## Security Considerations

- Regularly update dependencies
- Use environment variables for sensitive configuration
- Implement rate limiting
- Monitor file uploads and downloads
- Use HTTPS in production
- Configure CORS settings appropriately

## Performance Optimization

- Use Celery for background downloads
- Implement caching for frequently accessed data
- Optimize database queries
- Use CDN for static file serving
- Implement file cleanup for old downloads

## Troubleshooting

### Common Issues

1. **Download Failures**: Check yt-dlp installation and version
2. **Database Errors**: Verify PostgreSQL connection and permissions
3. **File Permission Issues**: Ensure media directory has proper permissions
4. **Platform-Specific Issues**: Check platform configurations and API limits
5. **Media Directory Not Found**: Make sure `media/downloads/` directory exists and is writable
6. **Static Files Not Loading**: Run `python manage.py collectstatic` after adding static files
7. **Environment Variables Not Loading**: Ensure `.env` file is in the project root and properly formatted

### Directory Setup Verification

After installation, verify your directory structure:

```bash
# Check if media directory exists
ls -la media/
ls -la media/downloads/

# Check if logs directory exists
ls -la logs/

# Check static files
ls -la static/

# Test Django can find media files
python manage.py shell
>>> from django.conf import settings
>>> import os
>>> print("Media root:", settings.MEDIA_ROOT)
>>> print("Downloads dir exists:", os.path.exists(os.path.join(settings.MEDIA_ROOT, 'downloads')))
```

### Logs

Check the application logs for detailed error information:

```bash
tail -f logs/django.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on the GitHub repository.