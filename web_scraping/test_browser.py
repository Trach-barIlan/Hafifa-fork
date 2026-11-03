import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from browser import is_external_link, is_retryable_error, load_existing_json


class BrowserHelpersTests(unittest.TestCase):
    def test_is_external_link_detects_http_links(self):
        self.assertTrue(is_external_link("https://example.com/about", "bbc.com"))
        self.assertFalse(is_external_link("https://bbc.com/news", "bbc.com"))

    def test_is_external_link_filters_non_http_schemes(self):
        self.assertFalse(is_external_link("mailto:hello@example.com", "bbc.com"))
        self.assertFalse(is_external_link("javascript:void(0)", "bbc.com"))
        self.assertFalse(is_external_link("data:text/plain,hello", "bbc.com"))

    def test_is_retryable_error_marks_timeouts_and_driver_errors(self):
        from selenium.common.exceptions import TimeoutException, WebDriverException

        self.assertTrue(is_retryable_error(TimeoutException("timed out")))
        self.assertTrue(is_retryable_error(WebDriverException("driver failed")))
        self.assertFalse(is_retryable_error(ValueError("not a selenium error")))

    def test_load_existing_json_returns_empty_dict_for_invalid_json(self):
        with TemporaryDirectory() as tmp_dir:
            bad_file = Path(tmp_dir) / "bad.json"
            bad_file.write_text("{not valid json}", encoding="utf-8")

            self.assertEqual(load_existing_json(bad_file), {})


if __name__ == "__main__":
    unittest.main()
