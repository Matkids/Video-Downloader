from django.urls import path
from . import views

app_name = 'downloader'

urlpatterns = [
    # Web interface
    path('', views.home, name='home'),
]