"""
Image Tools - Code for the download_image custom tool.

This is the same code that you used to implement the download_image tool in the
"Extend an AI agent with tools" exercise. The tool runs in this client app (not in
the managed agent's cloud environment), so that downloaded images are saved on
your computer where the web app can display them.
"""

import re
import html
import uuid
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Downloaded images are saved in the /downloads folder of this app
DOWNLOADS_FOLDER = Path(__file__).parent / "downloads"

# Image downloads: supported types (and the file extension to save them with), and the maximum size
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Many image sites (including Wikimedia Commons) reject requests that don't identify the client
# with a name and a contact URL
USER_AGENT = "ComputingHistoryAgent/1.0 (https://github.com/GraemeMalcolm/claude-labs)"


def fetch_image(url: str) -> Tuple[bytes, str]:
    """
    Helper function: download an image from a URL, and return its bytes and media type.

    If the URL is a web page rather than an image file, the page's main image
    (declared in its og:image metadata) is downloaded instead.
    """
    for _ in range(2):
        if urllib.parse.urlparse(url).scheme not in ("http", "https"):
            raise ValueError("Only http and https URLs can be downloaded.")

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            media_type = response.headers.get_content_type()
            data = response.read(MAX_IMAGE_BYTES + 1)

        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("The image is larger than 5 MB.")

        if media_type in IMAGE_TYPES:
            return data, media_type

        # Not an image - if it's a web page, look for its main image and try again
        if media_type == "text/html":
            match = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                data.decode("utf-8", errors="ignore"),
            )
            if match:
                url = urllib.parse.urljoin(url, html.unescape(match.group(1)))
                continue

        break

    raise ValueError(f"The URL returned '{media_type}' content, not a supported image file.")


def download_image(image_url: str, title: str, author: str, license: str, source_page_url: str) -> Dict[str, str]:
    """Download an image, save it in the downloads folder, and return its details."""
    data, media_type = fetch_image(image_url)

    # Create a safe, unique file name from the title (never trust a file name from the web)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "image"
    filename = f"{slug}-{uuid.uuid4().hex[:8]}{IMAGE_TYPES[media_type]}"

    DOWNLOADS_FOLDER.mkdir(exist_ok=True)
    (DOWNLOADS_FOLDER / filename).write_bytes(data)
    logger.info("Downloaded %s to %s", image_url, filename)

    return {
        "filename": filename,
        "title": title,
        "author": author,
        "license": license,
        "source_page_url": source_page_url,
    }
