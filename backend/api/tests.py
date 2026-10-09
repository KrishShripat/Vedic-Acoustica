from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class RecordingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='tester', password='password123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_recordings_empty(self):
        response = self.client.get(reverse('list_recordings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])

    def test_list_recordings_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('list_recordings'))
        self.assertEqual(response.status_code, 401)

    def test_recording_detail_requires_auth(self):
        from api.models import AudioRecording
        rec = AudioRecording.objects.create(title='test_rec')
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('recording_detail', args=[rec.id]))
        self.assertEqual(response.status_code, 401)

    def test_recording_detail_authenticated(self):
        from api.models import AudioRecording
        rec = AudioRecording.objects.create(title='test_rec')
        response = self.client.get(reverse('recording_detail', args=[rec.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], rec.id)
        self.assertEqual(response.data['title'], 'test_rec')

    def test_upload_requires_file(self):
        response = self.client.post(reverse('upload_audio'), {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse('upload_audio'), {}, format='multipart')
        self.assertEqual(response.status_code, 401)

    def test_analyze_missing_recording_returns_404(self):
        response = self.client.post(reverse('analyze_audio', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_analyze_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse('analyze_audio', args=[999]))
        self.assertEqual(response.status_code, 401)


class UserIsolationTestCase(TestCase):
    def setUp(self):
        from api.models import AudioRecording
        User = get_user_model()
        self.user_a = User.objects.create_user(username='user_a', password='password123')
        self.user_b = User.objects.create_user(username='user_b', password='password123')
        self.admin = User.objects.create_user(username='admin', password='password123', is_staff=True)

        self.rec_a = AudioRecording.objects.create(title='A private', uploaded_by=self.user_a)
        self.rec_b = AudioRecording.objects.create(title='B private', uploaded_by=self.user_b)
        self.rec_public = AudioRecording.objects.create(title='Public sample', uploaded_by=None)
        self.client = APIClient()

    def test_list_recordings_isolation(self):
        # User A should only see rec_a and rec_public
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(reverse('list_recordings'))
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertIn(self.rec_a.id, ids)
        self.assertIn(self.rec_public.id, ids)
        self.assertNotIn(self.rec_b.id, ids)

        # User B should only see rec_b and rec_public
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(reverse('list_recordings'))
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertIn(self.rec_b.id, ids)
        self.assertIn(self.rec_public.id, ids)
        self.assertNotIn(self.rec_a.id, ids)

    def test_list_recordings_staff_sees_all(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('list_recordings'))
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertIn(self.rec_a.id, ids)
        self.assertIn(self.rec_b.id, ids)
        self.assertIn(self.rec_public.id, ids)

    def test_recording_detail_isolation(self):
        # User A cannot view user B's recording
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(reverse('recording_detail', args=[self.rec_b.id]))
        self.assertEqual(resp.status_code, 404)

        # User A can view their own recording
        resp = self.client.get(reverse('recording_detail', args=[self.rec_a.id]))
        self.assertEqual(resp.status_code, 200)

        # User A can view public recording
        resp = self.client.get(reverse('recording_detail', args=[self.rec_public.id]))
        self.assertEqual(resp.status_code, 200)

    def test_recording_detail_staff_can_view_any(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('recording_detail', args=[self.rec_b.id]))
        self.assertEqual(resp.status_code, 200)

    def test_analyze_audio_isolation(self):
        # User A cannot trigger analysis on user B's recording
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.post(reverse('analyze_audio', args=[self.rec_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_upload_attaches_uploaded_by(self):
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(user=self.user_a)
        wav_file = SimpleUploadedFile(
            "test_sample.wav",
            b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 20,
            content_type="audio/wav"
        )
        with patch('api.tasks.build_playback_file_task.delay'):
            resp = self.client.post(reverse('upload_audio'), {'audio_file': wav_file, 'title': 'My Chant'}, format='multipart')
        self.assertEqual(resp.status_code, 201)
        from api.models import AudioRecording
        created_rec = AudioRecording.objects.get(id=resp.data['id'])
        self.assertEqual(created_rec.uploaded_by, self.user_a)
        self.assertEqual(resp.data['uploaded_by'], self.user_a.id)

    def test_upload_rejects_non_audio_content_masquerading_as_wav(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(user=self.user_a)
        fake_wav = SimpleUploadedFile("malware.wav", b"<html><body>not audio</body></html>", content_type="audio/wav")
        resp = self.client.post(reverse('upload_audio'), {'audio_file': fake_wav, 'title': 'Malware'}, format='multipart')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('audio_file', resp.data)
        self.assertIn('does not match a valid audio format', resp.data['audio_file'][0])

    def test_upload_accepts_valid_audio_formats(self):
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(user=self.user_a)

        mp3_file = SimpleUploadedFile("valid.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x10" + b"\x00" * 20, content_type="audio/mpeg")
        with patch('api.tasks.build_playback_file_task.delay'):
            resp = self.client.post(reverse('upload_audio'), {'audio_file': mp3_file, 'title': 'Valid MP3'}, format='multipart')
        self.assertEqual(resp.status_code, 201)

        ogg_file = SimpleUploadedFile("valid.ogg", b"OggS\x00\x02\x00\x00\x00\x00" + b"\x00" * 20, content_type="audio/ogg")
        with patch('api.tasks.build_playback_file_task.delay'):
            resp = self.client.post(reverse('upload_audio'), {'audio_file': ogg_file, 'title': 'Valid OGG'}, format='multipart')
        self.assertEqual(resp.status_code, 201)

        flac_file = SimpleUploadedFile("valid.flac", b"fLaC\x00\x00\x00\x22" + b"\x00" * 20, content_type="audio/flac")
        with patch('api.tasks.build_playback_file_task.delay'):
            resp = self.client.post(reverse('upload_audio'), {'audio_file': flac_file, 'title': 'Valid FLAC'}, format='multipart')
        self.assertEqual(resp.status_code, 201)


class AuthAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, **overrides):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'supersecret123',
        }
        payload.update(overrides)
        return self.client.post(reverse('auth_register'), payload, format='json')

    def test_register_returns_token_and_user(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'alice')
        self.assertFalse(response.data['user']['is_staff'])

    def test_register_duplicate_username_rejected(self):
        self.register()
        response = self.register(username='ALICE')
        self.assertEqual(response.status_code, 400)

    def test_register_requires_fields(self):
        response = self.client.post(reverse('auth_register'), {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_short_password_rejected(self):
        response = self.register(password='short')
        self.assertEqual(response.status_code, 400)

    def test_login_with_username(self):
        self.register()
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_login_with_email(self):
        self.register()
        response = self.client.post(
            reverse('auth_login'),
            {'email': 'alice@example.com', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password_rejected(self):
        self.register()
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'wrongpass'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_me_returns_current_user(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(reverse('auth_me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['username'], 'bob')

    def test_me_requires_auth(self):
        response = self.client.get(reverse('auth_me'))
        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_token(self):
        response = self.register()
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        logout_resp = self.client.post(reverse('auth_logout'))
        self.assertEqual(logout_resp.status_code, 200)
        me_resp = self.client.get(reverse('auth_me'))
        self.assertEqual(me_resp.status_code, 401)

    def test_admin_overview_requires_staff(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse('admin_overview'))
        self.assertEqual(response.status_code, 403)

    def test_admin_overview_returns_counts(self):
        from api.models import AudioRecording
        admin = get_user_model().objects.create_user(
            username='admin1', password='password123', is_staff=True
        )
        get_user_model().objects.create_user(username='regular1', password='password123')
        AudioRecording.objects.create(title='rec-a')
        AudioRecording.objects.create(title='rec-b', is_analyzed=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse('admin_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['counts']['total_recordings'], 2)
        self.assertEqual(response.data['counts']['analyzed_recordings'], 1)
        self.assertEqual(len(response.data['recordings']), 2)
        self.assertEqual(len(response.data['users']), 2)


class AnalysisProgressTestCase(TestCase):
    def test_extract_features_reports_granular_progress(self):
        import wave
        import numpy as np
        from tempfile import NamedTemporaryFile
        from ml_engine.audio_processing import extract_features

        sr = 22050
        t = np.arange(int(sr * 0.4)) / sr
        tone = (0.4 * np.sin(2 * np.pi * 261.63 * t)).astype(np.float32)

        with NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            with wave.open(tmp.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes((tone * 32767).astype(np.int16).tobytes())
            seen = []
            extract_features(tmp.name, progress_cb=lambda pct, detail: seen.append(pct))
            import os
            os.unlink(tmp.name)

        self.assertGreaterEqual(len(seen), 3)
        final = seen[-1]
        self.assertEqual(final, 30)
        steps = [p for p, _ in zip(seen[:-1], seen[1:])]
        for a, b in zip(seen[:-1], seen[1:]):
            self.assertGreaterEqual(b, a)

    def test_analysis_progress_endpoint_defaults_to_running(self):
        import os
        from api.models import AudioRecording
        from api.views import _progress_path
        rec = AudioRecording.objects.create(title='t')
        try:
            os.unlink(_progress_path(rec.id))
        except FileNotFoundError:
            pass
        response = self.client.get(reverse('analysis_progress', args=[rec.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'running')
        self.assertEqual(response.data['stage'], 'Queued')

    def test_analysis_progress_endpoint_reflects_snapshot(self):
        import os
        from api.models import AudioRecording
        from api.views import _set_progress, _progress_path
        rec = AudioRecording.objects.create(title='t')
        try:
            os.unlink(_progress_path(rec.id))
        except FileNotFoundError:
            pass
        _set_progress(rec.id, 'Feature Extraction', 26, detail='Extracting F0 pitch track (pYIN)…')
        response = self.client.get(reverse('analysis_progress', args=[rec.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['stage'], 'Feature Extraction')
        self.assertEqual(response.data['percent'], 26)
        self.assertEqual(response.data['status'], 'running')
        self.assertIn('pYIN', response.data['detail'])
        os.unlink(_progress_path(rec.id))


def test_analysis_progress_endpoint_reports_done_when_file_cleaned(self):
        import os
        from api.models import AudioRecording
        from api.views import _progress_path
        rec = AudioRecording.objects.create(title='t', is_analyzed=True)
        try:
            os.unlink(_progress_path(rec.id))
        except FileNotFoundError:
            pass
        response = self.client.get(reverse('analysis_progress', args=[rec.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'done')
        self.assertEqual(response.data['percent'], 100)
        self.assertEqual(response.data['stage'], 'Complete')


class PlaybackFileTestCase(TestCase):
    def test_playback_file_returns_mp3_url_when_present(self):
        import os
        from api.models import AudioRecording
        from django.core.files.base import ContentFile

        rec = AudioRecording.objects.create(title='t')
        rec.audio_file.save('p1.wav', ContentFile(b'\x00' * 44))
        mp3_path = os.path.splitext(rec.audio_file.path)[0] + '.mp3'
        with open(mp3_path, 'wb') as fh:
            fh.write(b'ID3')
        try:
            self.assertEqual(rec.playback_file, '/media/recordings/p1.mp3')
        finally:
            rec.audio_file.delete(save=False)
            if os.path.exists(mp3_path):
                os.remove(mp3_path)

    def test_playback_file_none_when_missing(self):
        from api.models import AudioRecording
        from django.core.files.base import ContentFile

        rec = AudioRecording.objects.create(title='t')
        rec.audio_file.save('p2.wav', ContentFile(b'\x00' * 44))
        try:
            self.assertIsNone(rec.playback_file)
        finally:
            rec.audio_file.delete(save=False)


class MatrixPathSecurityTestCase(TestCase):
    """Verify path traversal confinement on _load_matrices()."""

    def setUp(self):
        import numpy as np
        from api.views import _matrices_root
        self.matrices_dir = _matrices_root()
        self.valid_rel_path = 'analysis_matrices/test_security_matrices.npz'
        self.valid_full_path = self.matrices_dir / 'test_security_matrices.npz'

        # Write a dummy .npz file
        np.savez_compressed(
            str(self.valid_full_path),
            dummy_data=np.array([1, 2, 3], dtype=np.int32)
        )

    def tearDown(self):
        if self.valid_full_path.exists():
            self.valid_full_path.unlink()

    def test_valid_matrix_file_loads_successfully(self):
        from api.views import _load_matrices
        result = _load_matrices(self.valid_rel_path)
        self.assertIsNotNone(result)
        self.assertIn('dummy_data', result)
        self.assertEqual(result['dummy_data'].tolist(), [1, 2, 3])

    def test_path_traversal_relative_rejected(self):
        from api.views import _load_matrices
        # Attempt to escape analysis_matrices via ..
        self.assertIsNone(_load_matrices('../db.sqlite3'))
        self.assertIsNone(_load_matrices('analysis_matrices/../db.sqlite3'))
        self.assertIsNone(_load_matrices('../../something.npz'))

    def test_absolute_path_outside_rejected(self):
        from api.views import _load_matrices
        self.assertIsNone(_load_matrices('/etc/passwd'))
        self.assertIsNone(_load_matrices('C:/Windows/win.ini'))

    def test_directory_or_empty_rejected(self):
        from api.views import _load_matrices
        self.assertIsNone(_load_matrices(''))
        self.assertIsNone(_load_matrices(None))
        self.assertIsNone(_load_matrices('analysis_matrices'))

    def test_missing_file_returns_none(self):
        from api.views import _load_matrices
        self.assertIsNone(_load_matrices('analysis_matrices/non_existent_matrices.npz'))

    def test_symlink_outside_rejected(self):
        import os
        from pathlib import Path
        from django.conf import settings
        from api.views import _load_matrices
        symlink_path = self.matrices_dir / 'symlink_outside.npz'
        target_outside = Path(settings.MEDIA_ROOT) / 'secret.npz'
        try:
            target_outside.write_text('dummy')
            os.symlink(target_outside, symlink_path)
            self.assertIsNone(_load_matrices('analysis_matrices/symlink_outside.npz'))
        except (OSError, NotImplementedError):
            pass  # Handled safely when OS privileges restrict symlink creation
        finally:
            if symlink_path.is_symlink() or symlink_path.exists():
                symlink_path.unlink()
            if target_outside.exists():
                target_outside.unlink()


class SecuritySettingsTestCase(TestCase):
    def test_insecure_secret_keys_blocklist(self):
        from vedic_acoustica.settings import _KNOWN_INSECURE_SECRET_KEYS
        self.assertIn('change-me-in-production', _KNOWN_INSECURE_SECRET_KEYS)
        self.assertIn('django-insecure-dev-key-replace-in-production', _KNOWN_INSECURE_SECRET_KEYS)
        self.assertIn('django-insecure-hf-fallback-key-for-spaces', _KNOWN_INSECURE_SECRET_KEYS)
        self.assertIn('django-insecure-build-placeholder', _KNOWN_INSECURE_SECRET_KEYS)

    def test_sqlite_wal_mode_configured(self):
        from django.db import connection
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode;')
                mode = cursor.fetchone()[0]
                self.assertIn(mode.lower(), ('wal', 'memory'))

    def test_security_headers_middleware_present(self):
        resp = self.client.get('/api/recordings/')
        self.assertIn('Content-Security-Policy', resp.headers)
        self.assertIn("default-src 'self'", resp.headers['Content-Security-Policy'])
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(resp.headers.get('X-Frame-Options'), 'DENY')


class AnalysisStatusStreamTestCase(TestCase):
    def test_analysis_status_sse_headers_and_initial_event(self):
        resp = self.client.get('/api/analyze/99999/status/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/event-stream')
        self.assertEqual(resp['Cache-Control'], 'no-cache')
        self.assertEqual(resp['X-Accel-Buffering'], 'no')

        stream_iter = iter(resp.streaming_content)
        first_event = next(stream_iter)
        self.assertIn(b'data: ', first_event)
        self.assertIn(b'"stage": "Queued"', first_event)

    def test_analysis_progress_json_endpoint(self):
        resp = self.client.get('/api/analyze/99999/progress/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'running')
        self.assertEqual(resp.data['percent'], 0)

