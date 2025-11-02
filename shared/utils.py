"""
Shared utility module for the bot and the web server.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def extract_domain(url):
    """
    Estrae il dominio (host) da un URL.

    Input: string `url`.
    Output: dominio in minuscolo senza il prefisso 'www.' quando presente.
    In caso di errore ritorna stringa vuota.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Rimuovi www. se presente
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ''

def get_article_metadata(url):
    """Extracts metadata (title, description, image) from a URL."""
    try:
        # Adds 'https://' if a protocol is missing to avoid errors.
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.info(f"'https://' protocol automatically added to: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Skip HEAD request for Hacker News links, as they return 405 (Method Not Allowed)
        if "news.ycombinator.com" not in url:
            # Perform a HEAD request to check the content type for other sites
            try:
                head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
                head_response.raise_for_status()
                
                content_type = head_response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    logger.info(f"URL {url} is not an HTML page (Content-Type: {content_type}).")
                    return {
                        "title": f"Link to file ({content_type})",
                        "description": f"The URL points to a file of type {content_type}.",
                        "image_url": "",
                        "domain": extract_domain(url),
                    }
            except requests.exceptions.RequestException as e:
                logger.warning(f"HEAD request failed for {url}: {e}. Proceeding with GET.")

        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Extract title
        title = (soup.select_one('meta[property="og:title"]') or \
                 soup.select_one('meta[name="twitter:title"]') or \
                 soup.select_one("title"))
        title = title.get("content") if title and title.has_attr('content') else (title.get_text() if title else None)

        # Extract description
        description = (soup.select_one('meta[property="og:description"]') or \
                       soup.select_one('meta[name="twitter:description"]') or \
                       soup.select_one('meta[name="description"]'))
        description = description.get("content") if description else None

        # Extract image
        image_url = (soup.select_one('meta[property="og:image"]') or \
                     soup.select_one('meta[name="twitter:image"]'))
        image_url = image_url.get("content") if image_url else None

        return {
            "title": title.strip() if title else "Title not found",
            "description": description.strip() if description else "",
            "image_url": image_url or "",
            "domain": extract_domain(url),
        }

    except Exception as e:
        logger.error(f"Error extracting metadata for {url}: {e}")
        return {
            "title": f"Error: {extract_domain(url)}",
            "description": str(e),
            "image_url": "",
            "domain": extract_domain(url),
        }