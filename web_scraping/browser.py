import base64
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

BASE_OUTPUT = Path("output")
BASE_INPUT = Path("input")
URLS_FILE = BASE_INPUT / "urls.input"
MAX_WORKERS = 2
MAX_ATTEMPTS = 2
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def load_urls(file_path: Path) -> list[str]:
    if not file_path.exists():
        logger.error(
            "Input file %s does not exist. Please create it and add URLs to scrape.",
            file_path,
        )
        sys.exit(1)

    with file_path.open("r", encoding="utf-8") as file:
        urls = [line_stripped for line in file if (line_stripped := line.strip())]

    if not urls:
        logger.warning("No URLs found in %s", file_path)
        sys.exit(0)

    logger.info("Found %d URLs to scrape: %s", len(urls), urls)
    return urls


def run_parallel_scrape(urls: list[str]) -> None:
    workers = min(MAX_WORKERS, len(urls))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(scrape_url, index, url)
            for index, url in enumerate(urls, start=1)
        ]
        for future in as_completed(futures):
            future.result()


def scrape_url(index: int, url: str) -> None:
    output_dir = BASE_OUTPUT / f"url_{index}"
    output_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        driver = create_driver()
        try:
            driver.get(url)
            wait_for_page_ready(driver)

            external_links = extract_external_links(driver, urlparse(url).netloc)
            loaded_assets = extract_loaded_assets(driver)

            screenshot_path = output_dir / "screenshot.png"
            driver.save_screenshot(str(screenshot_path))
            write_scrape_output(output_dir, loaded_assets, driver.page_source)

            logger.info(
                "Scraped %s (url_%d): %d external links, %d loaded assets.",
                url,
                index,
                len(external_links),
                len(loaded_assets),
            )
            return
        except WebDriverException as error:
            if attempt == MAX_ATTEMPTS:
                raise Exception
            logger.warning(
                "Attempt %d/%d failed for %s (%s). Retrying...",
                attempt,
                MAX_ATTEMPTS,
                url,
                type(error).__name__,
            )
            continue
        except OSError as error:
            logger.error("Failed %s: File I/O error: %s", url, error)
            return
        except Exception as e:
            logger.error("Failed %s: %s", url, e)
            return
        finally:
            driver.quit()


def create_driver() -> webdriver.Chrome:
    return webdriver.Chrome(service=Service(), options=build_chrome_options())


def build_chrome_options() -> Options:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={USER_AGENT}")
    return options


def wait_for_page_ready(driver: webdriver.Chrome, timeout: int = 15) -> None:
    WebDriverWait(driver, timeout).until(
        lambda browser: browser.execute_script("return document.readyState") == "complete"
    )


def extract_external_links(driver: webdriver.Chrome, base_domain: str) -> set[str]:
    hrefs = driver.execute_script(
        "return Array.from(document.querySelectorAll('a'))"
        ".map(el => el.href).filter(Boolean);"
    )
    return {href for href in hrefs if is_external_link(href, base_domain)}


def is_external_link(link: str, base_domain: str) -> bool:
    parsed = urlparse(link)
    return False if not parsed.netloc or parsed.scheme.lower() not in {"http", "https"} else parsed.netloc != base_domain


def extract_loaded_assets(driver: webdriver.Chrome) -> set[str]:
    img_srcs = driver.execute_script(
        "return Array.from(document.querySelectorAll('img'))"
        ".map(el => el.src).filter(Boolean);"
    )
    script_srcs = driver.execute_script(
        "return Array.from(document.querySelectorAll('script[src]'))"
        ".map(el => el.src).filter(Boolean);"
    )
    css_hrefs = driver.execute_script(
        "return Array.from(document.querySelectorAll('link[rel=\"stylesheet\"]'))"
        ".map(el => el.href).filter(Boolean);"
    )
    return set(img_srcs) | set(script_srcs) | set(css_hrefs)


def write_scrape_output(output_dir: Path, loaded_assets: set[str], page_html: str) -> None:
    screenshot_path = output_dir / "screenshot.png"
    browse_path = output_dir / "browse.json"

    screenshot_b64 = encode_file_base64(screenshot_path)
    data = {
        "html": page_html,
        "resources": sorted(loaded_assets),
        "screenshot": screenshot_b64,
    }

    with browse_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def encode_file_base64(file_path: Path) -> str:
    with file_path.open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def is_retryable_error(error: Exception) -> bool:
    return isinstance(error, (TimeoutException, WebDriverException))

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    BASE_OUTPUT.mkdir(parents=True, exist_ok=True)
    urls = load_urls(URLS_FILE)

    logger.info("Scraping URLs...")
    run_parallel_scrape(urls)
    logger.info("Scraping complete.")

if __name__ == "__main__":
    main()
