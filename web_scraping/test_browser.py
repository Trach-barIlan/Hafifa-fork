import base64
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from browser import (
    is_external_link,
    is_http_url,
    is_retryable_error,
    load_urls,
    logger,
    write_scrape_output,
)


class BrowserHelpersTests(unittest.TestCase):
    def test_is_http_url_accepts_valid_http_and_https_urls(self):
        self.assertTrue(is_http_url("https://example.com/asset.js"))
        self.assertTrue(is_http_url("http://example.com/image.png"))
        self.assertFalse(is_http_url("data:application/javascript;base64,abc"))
        self.assertFalse(is_http_url("javascript:void(0)"))
        self.assertFalse(is_http_url("mailto:info@example.com"))
        self.assertFalse(is_http_url(""))

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

    def test_write_scrape_output_writes_expected_json_structure(self):
        with TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            (output_dir / "screenshot.png").write_bytes(b"dummy image bytes")

            write_scrape_output(
                output_dir=output_dir,
                resources={"https://example.com/style.css", "https://example.com/logo.png"},
                page_html="<html><body>Hello</body></html>",
            )

            browse_json_path = output_dir / "browse.json"
            self.assertTrue(browse_json_path.exists())

            with browse_json_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            self.assertEqual(data["html"], "<html><body>Hello</body></html>")
            self.assertEqual(
                data["resources"],
                ["https://example.com/logo.png", "https://example.com/style.css"],
            )
            self.assertEqual(
                data["screenshot"],
                base64.b64encode(b"dummy image bytes").decode("utf-8"),
            )

    def test_load_urls_reads_urls_from_file(self):
        with TemporaryDirectory() as tmp_dir:
            url_file = Path(tmp_dir) / "urls.input"
            url_file.write_text("https://example.com\n\nhttps://google.com\n", encoding="utf-8")

            with self.assertLogs(logger, level="INFO") as cm:
                urls = load_urls(url_file)

            self.assertEqual(urls, ["https://example.com", "https://google.com"])
            self.assertTrue(any("Found 2 URLs to scrape" in msg for msg in cm.output))


if __name__ == "__main__":
    unittest.main()
