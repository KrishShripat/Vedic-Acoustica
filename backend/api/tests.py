from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class RecordingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_recordings_empty(self):
        response = self.client.get(reverse('list_recordings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])

    def test_upload_requires_file(self):
        response = self.client.post(reverse('upload_audio'), {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_analyze_missing_recording_returns_404(self):
        response = self.client.post(reverse('analyze_audio', args=[999]))
        self.assertEqual(response.status_code, 404)


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
