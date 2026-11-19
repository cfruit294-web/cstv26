import shutil
import tempfile

from django.test import TestCase, override_settings

from core.media_access import serve_protected_media

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='cstv_test_media_access_')


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ServeProtectedMediaTests(TestCase):
    def setUp(self):
        import pathlib
        self.file_path = pathlib.Path(TEST_MEDIA_ROOT) / 'sample.txt'
        self.file_path.write_text('hello')

    @override_settings(USE_X_ACCEL_REDIRECT=False)
    def test_serves_file_directly_when_x_accel_disabled(self):
        response = serve_protected_media('sample.txt')
        self.assertNotIn('X-Accel-Redirect', response)
        self.assertEqual(b''.join(response.streaming_content), b'hello')

    @override_settings(USE_X_ACCEL_REDIRECT=True)
    def test_delegates_to_nginx_when_x_accel_enabled(self):
        response = serve_protected_media('sample.txt')
        self.assertEqual(response['X-Accel-Redirect'], '/internal-media/sample.txt')
        self.assertEqual(response.content, b'')

    def test_path_traversal_is_blocked(self):
        from django.http import Http404
        with self.assertRaises(Http404):
            serve_protected_media('../../etc/passwd')

    def test_missing_file_raises_404(self):
        from django.http import Http404
        with self.assertRaises(Http404):
            serve_protected_media('does-not-exist.txt')


class SafeMediaNameTests(TestCase):
    def test_accepts_nested_relative_path(self):
        from core.storage import safe_media_name
        self.assertEqual(safe_media_name('hls/abc', '720p/segment_001.ts'), 'hls/abc/720p/segment_001.ts')

    def test_rejects_escape_attempts(self):
        from django.http import Http404

        from core.storage import safe_media_name
        for bad in ('../x.ts', 'a/../../x.ts', '/etc/passwd', '..', '', 'a\\..\\x', 'a\x00b'):
            with self.subTest(bad=bad), self.assertRaises(Http404):
                safe_media_name('hls/abc', bad)
