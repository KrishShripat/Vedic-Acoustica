from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class RecordingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_recordings_empty(self):
        response = self.client.get(reverse('list_recordings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_upload_requires_file(self):
        response = self.client.post(reverse('upload_audio'), {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_analyze_missing_recording_returns_404(self):
        response = self.client.post(reverse('analyze_audio', args=[999]))
        self.assertEqual(response.status_code, 404)
