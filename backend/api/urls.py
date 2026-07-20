from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_audio, name='upload_audio'),
    path('recordings/', views.list_recordings, name='list_recordings'),
    path('recordings/<int:pk>/', views.recording_detail, name='recording_detail'),
    path('analyze/<int:pk>/', views.analyze_audio, name='analyze_audio'),
]
