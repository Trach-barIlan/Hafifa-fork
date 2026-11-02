import base64
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

BASE_OUTPUT = Path("output")
BASE_INPUT = Path("input")
URLS_FILE = BASE_INPUT / "urls.input"
MAX_WORKERS = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class ScrapeResult:
    url: str
    external_links: int = 0
    loaded_assets: int = 0
    error: str | None = None


def load_urls(file_path: Path) -> list[str]:
    if not file_path.exists():
        print(f"Input file {file_path} does not exist. Please create it and add URLs to scrape.")
        sys.exit(1)

    with file_path.open("r", encoding="utf-8") as file:
        urls = [line.strip() for line in file if line.strip()]

    if not urls:
        print(f"No URLs found in {file_path}")
        sys.exit(0)

    print(f"Found {len(urls)} URLs to scrape: {urls}")
    return urls


def build_chrome_options() -> Options:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={USER_AGENT}")
    return options


def create_driver() -> webdriver.Chrome:
    return webdriver.Chrome(service=Service(), options=build_chrome_options())


def extract_external_links(driver: webdriver.Chrome, base_domain: str) -> set[str]:
    hrefs = driver.execute_script(
        "return Array.from(document.querySelectorAll('a'))"
        ".map(el => el.href).filter(Boolean);"
    )
    return {
        href
        for href in hrefs
        if urlparse(href).netloc and urlparse(href).netloc != base_domain
    }


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


def encode_file_base64(file_path: Path) -> str:
    with file_path.open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def load_existing_json(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except JSONDecodeError:
        return {}


def write_scrape_output(output_dir: Path, loaded_assets: set[str], page_html: str) -> None:
    screenshot_path = output_dir / "screenshot.png"
    browse_path = output_dir / "browse.json"

    screenshot_b64 = encode_file_base64(screenshot_path)
    data = load_existing_json(browse_path)
    data["screenshot"] = screenshot_b64
    data["resource"] = sorted(loaded_assets)
    data["html"] = page_html

    with browse_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def scrape_url(index: int, url: str) -> ScrapeResult:
    output_dir = BASE_OUTPUT / f"url_{index}"
    output_dir.mkdir(parents=True, exist_ok=True)

    driver = create_driver()
    try:
        driver.get(url)
        driver.implicitly_wait(5)

        external_links = extract_external_links(driver, urlparse(url).netloc)
        loaded_assets = extract_loaded_assets(driver)

        screenshot_path = output_dir / "screenshot.png"
        driver.save_screenshot(str(screenshot_path))
        write_scrape_output(output_dir, loaded_assets, driver.page_source)

        return ScrapeResult(
            url=url,
            external_links=len(external_links),
            loaded_assets=len(loaded_assets),
        )
    except TimeoutException as error:
        return ScrapeResult(url=url, error=f"Timeout while loading page: {error}")
    except WebDriverException as error:
        return ScrapeResult(url=url, error=f"WebDriver error: {error}")
    except OSError as error:
        return ScrapeResult(url=url, error=f"File I/O error: {error}")
    finally:
        driver.quit()


def run_parallel_scrape(urls: list[str]) -> list[ScrapeResult]:
    workers = min(MAX_WORKERS, len(urls))
    results: list[ScrapeResult] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(scrape_url, index, url)
            for index, url in enumerate(urls, start=1)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    return results


def print_summary(results: list[ScrapeResult]) -> None:
    for result in results:
        if result.error:
            print(f"Failed {result.url}: {result.error}")
            continue

        print(
            f"Scraped {result.url}: {result.external_links} external links, "
            f"{result.loaded_assets} loaded assets."
        )


def main() -> None:
    BASE_OUTPUT.mkdir(parents=True, exist_ok=True)
    urls = load_urls(URLS_FILE)

    print("Scraping URLs...")
    results = run_parallel_scrape(urls)
    print_summary(results)
    print("Scraping complete.")


if __name__ == "__main__":
    main()
