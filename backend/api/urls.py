from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    path('auth/register/', auth_views.register, name='auth_register'),
    path('auth/login/', auth_views.login, name='auth_login'),
    path('auth/logout/', auth_views.logout, name='auth_logout'),
    path('auth/me/', auth_views.me, name='auth_me'),
    path('admin/overview/', auth_views.admin_overview, name='admin_overview'),
    path('upload/', views.upload_audio, name='upload_audio'),
    path('recordings/', views.list_recordings, name='list_recordings'),
    path('recordings/<int:pk>/', views.recording_detail, name='recording_detail'),
    path('analyze/<int:pk>/', views.analyze_audio, name='analyze_audio'),
    path('analyze/<int:pk>/status/', views.analysis_status, name='analysis_status'),
    path('analyze/<int:pk>/progress/', views.analysis_progress, name='analysis_progress'),
]
