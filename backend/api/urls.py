from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    path('auth/register/', auth_views.register, name='auth_register'),
    path('auth/login/', auth_views.login, name='auth_login'),
    path('auth/google/', auth_views.google_login, name='auth_google'),
    path('auth/logout/', auth_views.logout, name='auth_logout'),
    path('auth/verify-email/', auth_views.verify_email, name='auth_verify_email'),
    path('auth/verify-email/resend/', auth_views.resend_verification, name='auth_resend_verification'),
    path('auth/password-reset/', auth_views.password_reset, name='auth_password_reset'),
    path('auth/password-reset/confirm/', auth_views.password_reset_confirm, name='auth_password_reset_confirm'),
    path('auth/me/', auth_views.me, name='auth_me'),
    path('auth/delete-account/', auth_views.delete_account, name='auth_delete_account'),
    path('admin/overview/', auth_views.admin_overview, name='admin_overview'),
    path('upload/', views.upload_audio, name='upload_audio'),
    path('recordings/', views.list_recordings, name='list_recordings'),
    path('recordings/<int:pk>/', views.recording_detail, name='recording_detail'),
    path('analyze/<int:pk>/', views.analyze_audio, name='analyze_audio'),
    path('analyze/<int:pk>/status/', views.analysis_status, name='analysis_status'),
    path('analyze/<int:pk>/progress/', views.analysis_progress, name='analysis_progress'),
]
