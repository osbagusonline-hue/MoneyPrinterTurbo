"""Offline contracts: paid submissions, credentials, reference and timed subtitles."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


provider = module('food_ad_provider')
renderer = module('render_bagus_food_ad')


class GeneratorTests(unittest.TestCase):
    def test_missing_key_does_not_submit(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as temp:
            http = MagicMock()
            with self.assertRaisesRegex(RuntimeError, 'VOLCENGINE_ARK_API_KEY'):
                provider.generate_meal(Path(temp)/'missing.png', Path(temp), session=http)
            http.post.assert_not_called()

    def test_reference_submission_download_cache_and_no_key_in_receipt(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'VOLCENGINE_ARK_API_KEY':'test-secret'}):
            folder = Path(temp)
            image = folder/'meal.png'
            image.write_bytes(b'image-reference')
            http = MagicMock()
            http.post.return_value.status_code = 200
            http.post.return_value.json.return_value = {'id':'task-1'}
            poll = MagicMock(status_code=200)
            poll.json.return_value = {'status':'succeeded', 'content':{'video_url':'https://cdn.example/clip.mp4'}}
            download = MagicMock()
            download.__enter__.return_value = download
            download.iter_content.return_value = [b'video']
            http.get.side_effect = [poll, download]
            path = provider.generate_meal(image, folder/'cache', session=http)
            self.assertEqual(path.read_bytes(), b'video')
            payload = http.post.call_args.kwargs['json']
            self.assertEqual(payload['duration'], 10)
            self.assertEqual(payload['ratio'], '9:16')
            self.assertTrue(payload['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            self.assertNotIn('headers', http.get.call_args_list[-1].kwargs)
            self.assertEqual(provider.generate_meal(image, folder/'cache', session=http), path)
            self.assertEqual(http.post.call_count, 1)
            receipt = next((folder/'cache').glob('*.json')).read_text()
            self.assertNotIn('test-secret', receipt)

    def test_ambiguous_submission_never_posts_again(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'VOLCENGINE_ARK_API_KEY':'test-secret'}):
            folder = Path(temp)
            image = folder/'meal.png'
            image.write_bytes(b'img')
            http = MagicMock()
            http.post.side_effect = provider.requests.Timeout()
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    provider.generate_meal(image, folder/'cache', session=http)
            self.assertEqual(http.post.call_count, 1)

    def test_resume_existing_task_without_paid_post(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'VOLCENGINE_ARK_API_KEY':'test-secret'}):
            folder = Path(temp)
            image = folder/'meal.png'
            image.write_bytes(b'img')
            http = MagicMock()
            http.post.return_value.status_code = 200
            http.post.return_value.json.return_value = {'id':'resume-me'}
            http.get.return_value.status_code = 403
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError, 'polling HTTP 403'):
                    provider.generate_meal(image, folder/'cache', session=http)
            self.assertEqual(http.post.call_count, 1)
            self.assertTrue(http.get.call_args.args[0].endswith('/resume-me'))

    def test_real_voice_subtitles_cover_the_script_and_fit_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'captions.srt'
            renderer.grouped_subtitles(ROOT/'assets/food_ads/bagus_ms_Yasmin.words.srt', target)
            text = target.read_text()
            self.assertIn('Bagus Sambal Belacan', text)
            self.assertIn('Dapatkan di Bagusmart', text)
            self.assertEqual(text.count(' --> '), 3)
            self.assertNotIn('00:00:10', text)


if __name__ == '__main__':
    unittest.main()
