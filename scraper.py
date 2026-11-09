import ipaddress
import socket
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

def is_safe_url(url: str) -> bool:
    """Blocks loopback, link-local, and private IP addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)

        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
            return False

        return True
    except Exception:
        return False


def extract_content_from_url(url: str) -> str:
    """Fetches web page and extracts clean readable text."""
    if not is_safe_url(url):
        raise ValueError(f"Blocked unsafe or invalid URL: {url}")

    headers = {
        "User-Agent": "ExamKnowledgeBot/1.0 (Educational Ingestion Pipeline)"
    }
    
    # 5-second timeout, stream to check size cap (max 2 MB)
    response = requests.get(url, headers=headers, timeout=5, stream=True)
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > 2 * 1024 * 1024:
        raise ValueError("Document exceeds maximum size limit (2 MB)")

    # Read body capped at 2 MB
    raw_html = response.raw.read(2 * 1024 * 1024, decode_content=True)

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove non-content elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        element.decompose()

    # Extract text and normalize spaces
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = "\n".join(chunk for chunk in chunks if chunk)

    if len(clean_text) < 100:
        raise ValueError("Extracted text is too short or page requires JavaScript rendering")

    return clean_text