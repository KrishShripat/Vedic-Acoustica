from django.contrib import admin

from .models import AudioRecording


@admin.register(AudioRecording)
class AudioRecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'uploaded_at', 'is_analyzed')
    list_filter = ('is_analyzed',)
    search_fields = ('title',)
    readonly_fields = ('uploaded_at',)
