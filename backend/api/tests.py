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

    def test_upload_assigns_recording_to_authenticated_user(self):
        from api.models import AudioRecording
        from django.core.files.uploadedfile import SimpleUploadedFile
        from unittest.mock import patch

        audio = SimpleUploadedFile('owned.wav', b'RIFF', content_type='audio/wav')
        with patch('api.tasks.build_playback_file_task.delay'):
            response = self.client.post(
                reverse('upload_audio'),
                {'audio_file': audio, 'title': 'Owned recording'},
                format='multipart',
            )
        self.assertEqual(response.status_code, 201)
        recording = AudioRecording.objects.get(pk=response.data['id'])
        self.assertEqual(recording.owner, self.user)

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
        user = get_user_model().objects.get(username='alice')
        self.assertNotEqual(user.password, 'supersecret123')
        self.assertTrue(user.check_password('supersecret123'))
        self.assertTrue(user.is_active)

    def test_register_duplicate_username_rejected(self):
        self.register()
        response = self.register(username='ALICE')
        self.assertEqual(response.status_code, 400)

    def test_register_requires_fields(self):
        response = self.client.post(reverse('auth_register'), {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_rejects_invalid_username_without_mutating_it(self):
        response = self.register(username='Alice Smith')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='AliceSmith').exists())

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

    def test_registration_login_and_token_auth_keep_submitted_username(self):
        register_response = self.register(username='Alice.Mixed-Case')
        self.assertEqual(register_response.status_code, 201)
        registered_username = register_response.data['user']['username']
        self.assertEqual(registered_username, 'Alice.Mixed-Case')

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
        import os
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
                title='Owned', owner=user, matrices_file='analysis_matrices/1_matrices.npz'
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
            self.assertTrue(AudioRecording.objects.filter(pk=shared_id, owner=None).exists())
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
