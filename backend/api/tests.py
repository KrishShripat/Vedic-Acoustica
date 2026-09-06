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
