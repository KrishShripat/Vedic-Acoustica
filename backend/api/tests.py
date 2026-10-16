import os
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from api.auth_views import email_verification_generator


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
        rec = AudioRecording.objects.create(title='test_rec', uploaded_by=self.user)
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
        # User A should only see rec_a — not rec_b, and not the anonymous
        # (uploaded_by=NULL) recording, which must not leak to regular users.
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(reverse('list_recordings'))
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertIn(self.rec_a.id, ids)
        self.assertNotIn(self.rec_b.id, ids)
        self.assertNotIn(self.rec_public.id, ids)

        # User B should only see rec_b — not rec_a, not the anonymous recording.
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(reverse('list_recordings'))
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertIn(self.rec_b.id, ids)
        self.assertNotIn(self.rec_a.id, ids)
        self.assertNotIn(self.rec_public.id, ids)

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

        # User A cannot view an anonymous (uploaded_by=NULL) recording
        resp = self.client.get(reverse('recording_detail', args=[self.rec_public.id]))
        self.assertEqual(resp.status_code, 404)

    def test_recording_detail_staff_can_view_any(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('recording_detail', args=[self.rec_b.id]))
        self.assertEqual(resp.status_code, 200)

    def test_analyze_audio_isolation(self):
        # User A cannot trigger analysis on user B's recording
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.post(reverse('analyze_audio', args=[self.rec_b.id]))
        self.assertEqual(resp.status_code, 404)

        # User A cannot trigger analysis on an anonymous (uploaded_by=NULL) recording
        resp = self.client.post(reverse('analyze_audio', args=[self.rec_public.id]))
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
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self._email_configured = patch('api.auth_views.email_configured', return_value=True)
        self._send_email = patch('api.auth_views.send_email', return_value=True)
        self._email_configured.start()
        self.send_email = self._send_email.start()
        self.addCleanup(self._email_configured.stop)
        self.addCleanup(self._send_email.stop)

    def register(self, **overrides):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'supersecret123',
        }
        payload.update(overrides)
        return self.client.post(reverse('auth_register'), payload, format='json')

    def register_and_verify(self, **overrides):
        response = self.register(**overrides)
        self.assertEqual(response.status_code, 201)
        username = response.data['user']['username']
        user = get_user_model().objects.get(username=username)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_generator.make_token(user)
        verify = self.client.post(
            reverse('auth_verify_email'), {'uid': uid, 'token': token}, format='json'
        )
        self.assertEqual(verify.status_code, 200)
        return response

    def test_register_creates_inactive_account_and_sends_email(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('token', response.data)
        self.assertTrue(response.data['verification_required'])
        self.assertEqual(response.data['user']['username'], 'alice')
        self.assertFalse(response.data['user']['is_staff'])
        user = get_user_model().objects.get(username='alice')
        self.assertFalse(user.is_active)
        self.assertTrue(hasattr(user, 'email_verification'))
        self.assertFalse(user.email_verification.verified)
        self.send_email.assert_called()

    def test_register_blocked_when_email_not_configured(self):
        with patch('api.auth_views.email_configured', return_value=False):
            response = self.register(username='noconfig', email='nc@example.com')
        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            get_user_model().objects.filter(username='noconfig').exists()
        )

    def test_register_requires_email(self):
        response = self.register(email='')
        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_email_rejected(self):
        self.register()
        response = self.register(username='different', email='ALICE@example.com')
        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_username_rejected(self):
        self.register()
        response = self.register(username='ALICE', email='other@example.com')
        self.assertEqual(response.status_code, 400)

    def test_register_requires_fields(self):
        response = self.client.post(reverse('auth_register'), {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_short_password_rejected(self):
        response = self.register(password='short')
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_email_format_rejected(self):
        response = self.register(email='not-an-email')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Invalid email address format.')

    def test_register_username_validation(self):
        response = self.register(username='ab')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Username must be between 3 and 150 characters.', response.data['error'])

        response = self.register(username='bad user!')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Username contains invalid characters.', response.data['error'])

    def test_register_rate_limit_throttle(self):
        from django.core.cache import cache
        cache.clear()
        for i in range(10):
            res = self.register(username=f'user_{i}', email=f'user_{i}@example.com')
            self.assertEqual(res.status_code, 201)
        throttled_res = self.register(username='user_11', email='user_11@example.com')
        self.assertEqual(throttled_res.status_code, 429)

    def test_login_blocked_until_email_verified(self):
        self.register()
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.data.get('verification_required'))

    def test_login_with_username_after_verification(self):
        self.register_and_verify()
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_login_with_email_after_verification(self):
        self.register_and_verify()
        response = self.client.post(
            reverse('auth_login'),
            {'email': 'alice@example.com', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password_rejected(self):
        self.register_and_verify()
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
        self.register_and_verify()
        login = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'supersecret123'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
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


class PlaybackFileSubprocessSecurityTestCase(TestCase):
    def test_upload_filename_sanitization_strips_flags(self):
        from api.serializers import AudioRecordingSerializer
        serializer = AudioRecordingSerializer()

        class DummyFile:
            def __init__(self, name):
                self.name = name
                self.size = 100

            def read(self, n):
                return b'RIFF\x24\x00\x00\x00WAVEfmt '

            def tell(self):
                return 0

            def seek(self, pos):
                pass

        f = DummyFile('-rf.wav')
        validated = serializer.validate_audio_file(f)
        self.assertEqual(validated.name, 'rf.wav')

        f2 = DummyFile('..test.wav')
        validated2 = serializer.validate_audio_file(f2)
        self.assertEqual(validated2.name, 'test.wav')

    def test_build_playback_file_confined_to_media_root(self):
        from unittest.mock import MagicMock
        from api.views import _build_playback_file

        mock_rec = MagicMock()
        mock_rec.audio_file.path = '/etc/passwd'
        # Must return safely without executing ffmpeg on external path
        _build_playback_file(mock_rec)

    def test_build_playback_file_does_not_delete_mp3_source(self):
        """An uploaded .mp3 is its own playback file: _build_playback_file must
        never run ffmpeg in place and then delete the original upload."""
        import tempfile
        from django.core.files.base import ContentFile
        from django.test import override_settings
        from api.models import AudioRecording
        from api.views import _build_playback_file

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            rec = AudioRecording.objects.create(title='mp3 in place')
            rec.audio_file.save('inplace.mp3', ContentFile(b'ID3\x04\x00\x00'), save=True)
            src = rec.audio_file.path
            self.assertTrue(os.path.exists(src))

            _build_playback_file(rec)

            self.assertTrue(os.path.exists(src), 'original mp3 upload was deleted')


class GoogleLoginAPITestCase(TestCase):
    """Tests for POST /api/auth/google/ (Google Identity Services sign-in)."""

    GOOGLE_CLIENT_ID = '123456-test-client.apps.googleusercontent.com'

    def setUp(self):
        from unittest import mock
        self.google_env = mock.patch.dict(
            os.environ,
            {'GOOGLE_CLIENT_ID': self.GOOGLE_CLIENT_ID},
        )
        self.google_env.start()
        self.addCleanup(self.google_env.stop)
        self.client = APIClient()

    def _google(self, payload=None, verifier=None):
        from unittest import mock
        patcher = mock.patch(
            'api.auth_views.google_id_token.verify_oauth2_token',
            side_effect=verifier or (lambda *a, **k: {
                'email': 'researcher@gmail.com',
                'email_verified': True,
                'given_name': 'Reva',
                'family_name': 'Garg',
                'sub': 'gsub-123',
            }),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return self.client.post(
            reverse('auth_google'), payload or {}, format='json',
        )

    def test_google_login_creates_user_and_returns_token(self):
        from django.contrib.auth import get_user_model
        response = self._google({'credential': 'fake.jwt.token'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        user = get_user_model().objects.get(email='researcher@gmail.com')
        self.assertEqual(response.data['user']['username'], user.username)
        self.assertEqual(user.first_name, 'Reva')
        self.assertEqual(user.last_name, 'Garg')

    def test_google_login_existing_user_reuses_account(self):
        from django.contrib.auth import get_user_model
        get_user_model().objects.create_user(
            username='reva', email='researcher@gmail.com', password='hashed123',
        )
        response = self._google({'credential': 'fake.jwt.token'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['username'], 'reva')

    def test_google_login_activates_pending_unverified_account(self):
        from django.contrib.auth import get_user_model
        from api.models import EmailVerification
        user = get_user_model().objects.create_user(
            username='pending', email='researcher@gmail.com',
            password='hashed123', is_active=False,
        )
        EmailVerification.objects.create(user=user, verified=False)
        response = self._google({'credential': 'fake.jwt.token'})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verification.verified)

    def test_google_login_invalid_credential_rejected(self):
        def bad_verify(*args, **kwargs):
            raise ValueError('Bad signature')
        response = self._google({'credential': 'garbage'}, verifier=bad_verify)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid or expired Google credential.', response.data['error'])

    def test_google_login_unverified_email_rejected(self):
        def unverified(*args, **kwargs):
            return {'email': 'troll@example.com', 'email_verified': False}
        response = self._google({'credential': 'fake.jwt.token'}, verifier=unverified)
        self.assertEqual(response.status_code, 400)
        self.assertIn('not verified', response.data['error'])

    def test_google_login_unconfigured_returns_503(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('GOOGLE_CLIENT_ID', None)
            response = self.client.post(
                reverse('auth_google'), {'credential': 'x'}, format='json',
            )
        self.assertEqual(response.status_code, 503)




class ProfileAccountAPITestCase(TestCase):
    """Profile edit (PATCH /api/auth/me/) and account deletion tests.

    Ownership uses the ``uploaded_by`` FK (main branch's isolation field).
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self._email_configured = patch('api.auth_views.email_configured', return_value=True)
        self._send_email = patch('api.auth_views.send_email', return_value=True)
        self._email_configured.start()
        self._send_email.start()
        self.addCleanup(self._email_configured.stop)
        self.addCleanup(self._send_email.stop)

    def register(self, **overrides):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'supersecret123',
        }
        payload.update(overrides)
        return self.client.post(reverse('auth_register'), payload, format='json')

    def verify(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_generator.make_token(user)
        return self.client.post(
            reverse('auth_verify_email'), {'uid': uid, 'token': token}, format='json'
        )

    def test_register_stores_hashed_password_inactive_until_verified(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='alice')
        self.assertNotEqual(user.password, 'supersecret123')
        self.assertTrue(user.check_password('supersecret123'))
        self.assertFalse(user.is_active)
        self.assertEqual(self.verify(user).status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_register_rejects_invalid_username_without_mutating_it(self):
        response = self.register(username='Alice Smith')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='AliceSmith').exists())

    def test_registration_login_and_token_auth_keep_submitted_username(self):
        register_response = self.register(username='Alice.Mixed-Case')
        self.assertEqual(register_response.status_code, 201)
        registered_username = register_response.data['user']['username']
        self.assertEqual(registered_username, 'Alice.Mixed-Case')

        user = get_user_model().objects.get(username=registered_username)
        self.assertEqual(self.verify(user).status_code, 200)

        login_response = self.client.post(
            reverse('auth_login'),
            {'username': 'Alice.Mixed-Case', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.data['token'])
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {login_response.data['token']}"
        )
        me_response = self.client.get(reverse('auth_me'))
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data['user']['username'], registered_username)

    def test_me_payload_includes_is_active(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse('auth_me'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('is_active', response.data['user'])

    def test_me_updates_username_and_name(self):
        user = get_user_model().objects.create_user(
            username='bob', password='password123', first_name='Bob'
        )
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            reverse('auth_me'),
            {'username': 'bobby', 'first_name': 'Bobby', 'last_name': 'Smith'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['username'], 'bobby')
        self.assertEqual(response.data['user']['first_name'], 'Bobby')
        self.assertEqual(response.data['user']['last_name'], 'Smith')
        user.refresh_from_db()
        self.assertEqual(user.username, 'bobby')

    def test_me_rejects_duplicate_username_case_insensitively(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        get_user_model().objects.create_user(username='taken', password='password123')
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            reverse('auth_me'), {'username': 'TAKEN'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.username, 'bob')

    def test_me_rejects_empty_editable_values_and_privileged_fields(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        self.client.force_authenticate(user=user)
        for payload in (
            {'username': '   '},
            {'username': 'not a valid username'},
            {'first_name': '', 'last_name': ' '},
            {'is_staff': True},
            {'email': 'attacker@example.com'},
        ):
            with self.subTest(payload=payload):
                response = self.client.patch(
                    reverse('auth_me'), payload, format='json'
                )
                self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertEqual(user.email, '')

    def test_me_rejects_non_object_update(self):
        user = get_user_model().objects.create_user(username='bob', password='password123')
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            reverse('auth_me'), ['changed'], format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_me_update_requires_authentication(self):
        response = self.client.patch(
            reverse('auth_me'), {'username': 'changed'}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_account_deletion_removes_owned_data_but_preserves_unassigned_recordings(self):
        import tempfile
        from django.core.files.base import ContentFile
        from django.test import override_settings
        from api.models import AudioRecording

        user = get_user_model().objects.create_user(
            username='delete-me', password='password123'
        )
        token = Token.objects.create(user=user)
        self.client.force_authenticate(user=user)

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            owned = AudioRecording.objects.create(
                title='Owned', uploaded_by=user, matrices_file='analysis_matrices/1_matrices.npz'
            )
            owned.audio_file.save('owned.wav', ContentFile(b'RIFF'), save=True)
            audio_path = owned.audio_file.path
            playback_path = os.path.splitext(audio_path)[0] + '.mp3'
            with open(playback_path, 'wb') as playback:
                playback.write(b'ID3')
            matrix_path = os.path.join(media_root, owned.matrices_file)
            os.makedirs(os.path.dirname(matrix_path), exist_ok=True)
            with open(matrix_path, 'wb') as matrices:
                matrices.write(b'matrices')

            shared = AudioRecording.objects.create(title='Unassigned shared recording')
            owned_id = owned.pk
            shared_id = shared.pk

            response = self.client.delete(
                reverse('auth_delete_account'),
                {'confirmation': 'DELETE'},
                format='json',
            )

            self.assertEqual(response.status_code, 204)
            self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
            self.assertFalse(Token.objects.filter(pk=token.pk).exists())
            self.assertFalse(AudioRecording.objects.filter(pk=owned_id).exists())
            self.assertTrue(AudioRecording.objects.filter(pk=shared_id, uploaded_by=None).exists())
            self.assertFalse(os.path.exists(audio_path))
            self.assertFalse(os.path.exists(playback_path))
            self.assertFalse(os.path.exists(matrix_path))

    def test_account_deletion_requires_authentication(self):
        response = self.client.delete(reverse('auth_delete_account'))
        self.assertEqual(response.status_code, 401)

    def test_account_deletion_requires_exact_confirmation(self):
        user = get_user_model().objects.create_user(
            username='keep-me', password='password123'
        )
        token = Token.objects.create(user=user)
        self.client.force_authenticate(user=user)
        for confirmation in ('', 'delete', ' DELETE '):
            with self.subTest(confirmation=confirmation):
                response = self.client.delete(
                    reverse('auth_delete_account'),
                    {'confirmation': confirmation},
                    format='json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
                self.assertTrue(Token.objects.filter(pk=token.pk).exists())


class PasswordResetAPITestCase(TestCase):
    """Password-reset request + confirm flow (provider HTTP API mocked)."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # reset DRF throttle history shared across test methods
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='oldpassword123',
        )

    def _request_reset(self, email='reset@example.com'):
        with patch('api.auth_views.email_configured', return_value=True), \
                patch('api.auth_views.send_email', return_value=True) as send:
            response = self.client.post(
                reverse('auth_password_reset'), {'email': email}, format='json'
            )
        return response, send

    def test_reset_request_unavailable_without_provider(self):
        with patch('api.auth_views.email_configured', return_value=False):
            response = self.client.post(
                reverse('auth_password_reset'),
                {'email': 'reset@example.com'},
                format='json',
            )
        self.assertEqual(response.status_code, 503)

    def test_reset_request_requires_email(self):
        with patch('api.auth_views.email_configured', return_value=True):
            response = self.client.post(
                reverse('auth_password_reset'), {'email': ''}, format='json'
            )
        self.assertEqual(response.status_code, 400)

    def test_reset_request_sends_link_with_token(self):
        response, send = self._request_reset()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('reset@example.com', str(response.data))
        send.assert_called_once()
        to_email, subject, text, html = send.call_args.args
        self.assertEqual(to_email, 'reset@example.com')
        self.assertIn('reset=1', text)
        self.assertIn('uid=', text)
        self.assertIn('token=', text)
        self.assertIn('reset', subject.lower())

    def test_reset_request_does_not_reveal_unknown_email(self):
        response, send = self._request_reset(email='nobody@example.com')
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()

    def test_reset_confirm_sets_new_password_and_revokes_tokens(self):
        token = Token.objects.create(user=self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)

        response = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': uid, 'token': reset_token, 'password': 'brandnewpass456'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brandnewpass456'))
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_reset_confirm_rejects_bad_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': uid, 'token': 'not-a-real-token', 'password': 'brandnewpass456'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword123'))

    def test_reset_confirm_rejects_bad_uid(self):
        reset_token = default_token_generator.make_token(self.user)
        response = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': 'garbage', 'token': reset_token, 'password': 'brandnewpass456'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_confirm_rejects_short_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        response = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': uid, 'token': reset_token, 'password': 'short'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword123'))

    def test_reset_token_is_single_use(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        first = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': uid, 'token': reset_token, 'password': 'brandnewpass456'},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            reverse('auth_password_reset_confirm'),
            {'uid': uid, 'token': reset_token, 'password': 'anotherpass789'},
            format='json',
        )
        self.assertEqual(second.status_code, 400)


class EmailVerificationAPITestCase(TestCase):
    """Sign-up email verification: locked account until the link is opened."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()

    def register(self, **overrides):
        payload = {
            'username': 'verifyme',
            'email': 'verify@example.com',
            'password': 'supersecret123',
        }
        payload.update(overrides)
        with patch('api.auth_views.email_configured', return_value=True), \
                patch('api.auth_views.send_email', return_value=True) as send:
            response = self.client.post(reverse('auth_register'), payload, format='json')
        return response, send

    def test_register_creates_locked_account_and_sends_link(self):
        response, send = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['verification_required'])
        user = get_user_model().objects.get(username='verifyme')
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verification.verified)
        send.assert_called_once()
        text = send.call_args.args[2]
        self.assertIn('verify=1', text)
        self.assertIn('uid=', text)
        self.assertIn('token=', text)

    def test_register_unavailable_without_email_provider(self):
        with patch('api.auth_views.email_configured', return_value=False):
            response = self.client.post(
                reverse('auth_register'),
                {'username': 'noconfig', 'email': 'x@example.com', 'password': 'supersecret123'},
                format='json',
            )
        self.assertEqual(response.status_code, 503)

    def test_verify_activates_locked_account(self):
        response, _ = self.register()
        user = get_user_model().objects.get(username='verifyme')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_generator.make_token(user)
        verify = self.client.post(
            reverse('auth_verify_email'), {'uid': uid, 'token': token}, format='json'
        )
        self.assertEqual(verify.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verification.verified)

    def test_verify_rejects_bad_token(self):
        self.register()
        user = get_user_model().objects.get(username='verifyme')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verify = self.client.post(
            reverse('auth_verify_email'), {'uid': uid, 'token': 'bad-token'}, format='json'
        )
        self.assertEqual(verify.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_verify_requires_fields(self):
        verify = self.client.post(reverse('auth_verify_email'), {}, format='json')
        self.assertEqual(verify.status_code, 400)

    def test_login_locked_then_unlocked_after_verify(self):
        self.register()
        locked = self.client.post(
            reverse('auth_login'),
            {'username': 'verifyme', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(locked.status_code, 403)
        self.assertTrue(locked.data.get('verification_required'))

        user = get_user_model().objects.get(username='verifyme')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_generator.make_token(user)
        self.client.post(
            reverse('auth_verify_email'), {'uid': uid, 'token': token}, format='json'
        )
        unlocked = self.client.post(
            reverse('auth_login'),
            {'username': 'verifyme', 'password': 'supersecret123'},
            format='json',
        )
        self.assertEqual(unlocked.status_code, 200)
        self.assertIn('token', unlocked.data)

    def test_resend_is_generic_for_unknown_email(self):
        with patch('api.auth_views.email_configured', return_value=True), \
                patch('api.auth_views.send_email', return_value=True) as send:
            response = self.client.post(
                reverse('auth_resend_verification'),
                {'email': 'nobody@example.com'}, format='json',
            )
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()

    def test_resend_sends_for_unverified_account(self):
        self.register()
        with patch('api.auth_views.email_configured', return_value=True), \
                patch('api.auth_views.send_email', return_value=True) as send:
            response = self.client.post(
                reverse('auth_resend_verification'),
                {'email': 'verify@example.com'}, format='json',
            )
        self.assertEqual(response.status_code, 200)
        send.assert_called_once()

    def test_resend_does_not_send_for_verified_account(self):
        user = get_user_model().objects.create_user(
            username='active', email='active@example.com', password='supersecret123'
        )
        with patch('api.auth_views.email_configured', return_value=True), \
                patch('api.auth_views.send_email', return_value=True) as send:
            response = self.client.post(
                reverse('auth_resend_verification'),
                {'email': 'active@example.com'}, format='json',
            )
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()
