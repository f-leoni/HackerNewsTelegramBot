"""
Shared utility module for the bot and the web server.
"""
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
import re
import json
import time
from collections import Counter

logger = logging.getLogger(__name__)

def extract_domain(url):
    """
    Extracts the domain (host) from a URL.
    
    Args:
        url (str): The input URL string.
    Returns:
        str: The domain in lowercase, without the 'www.' prefix if present.
             Returns an empty string in case of an error.
    """
    try:
        parsed = urlparse(url)
        # If urlparse doesn't find a scheme, it puts the domain in 'path'.
        # We handle this case to correctly parse URLs like 'www.google.com'.
        if not parsed.netloc and parsed.path:
            domain = parsed.path.lower()
        else:
            domain = parsed.netloc.lower()

        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # A simple validation: a valid domain should contain at least one dot.
        if '.' not in domain:
            return ''
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


def _normalize_tags(tags, n=3):
    """Normalize tag list: lowercase, strip, dedupe, and clamp to n items."""
    if not tags:
        return []

    normalized = []
    seen = set()

    for tag in tags:
        if tag is None:
            continue
        cleaned = str(tag).strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
        if len(normalized) >= n:
            break

    return normalized


def _describe_gemini_error(error):
    """Return a compact, log-safe description for Gemini request failures."""
    if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
        status_code = error.response.status_code
        reason = error.response.reason or 'HTTP error'
        provider_message = ''

        try:
            error_payload = error.response.json()
            provider_message = error_payload.get('error', {}).get('message', '')
        except ValueError:
            provider_message = ''

        if provider_message:
            return f"HTTP {status_code} {reason}: {provider_message}"

        return f"HTTP {status_code} {reason}"

    return str(error)


def _sanitize_gemini_error_payload(error):
    """Return a log-safe JSON payload for Gemini errors when available."""
    if not isinstance(error, requests.exceptions.HTTPError) or error.response is None:
        return None

    try:
        payload = error.response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    error_info = payload.get('error')
    if not isinstance(error_info, dict):
        return None

    safe_payload = {}
    for key in ('code', 'message', 'status', 'details'):
        if key in error_info:
            safe_payload[key] = error_info[key]

    return safe_payload or None


def generate_tags_llm(title, description, domain='', n=3):
    """Generate tags with Gemini when configured, otherwise fall back locally."""
    text = f"{title or ''}\n{description or ''}".strip()
    gemini_enabled = os.getenv("GEMINI_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    content_preview = (title or description or domain or '').strip()[:80]

    if not gemini_enabled or not gemini_api_key:
        logger.info(
            "Gemini tags disabled or not configured; using local fallback for domain=%s preview=%r",
            domain or '-',
            content_preview,
        )
        return generate_tags(text, n=n)

    prompt = (
        "Generate exactly 3 concise lowercase tags for this bookmark. "
        "Return JSON only in this format: {\"tags\": [\"tag1\", \"tag2\", \"tag3\"]}.\n\n"
        f"title: {title or ''}\n"
        f"description: {description or ''}\n"
        f"domain: {domain or ''}\n"
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{gemini_model}:generateContent"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        logger.info(
            "Requesting Gemini tags model=%s domain=%s preview=%r",
            gemini_model,
            domain or '-',
            content_preview,
        )
        start_time = time.perf_counter()
        response = requests.post(url, params={"key": gemini_api_key}, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned by Gemini")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("No content parts returned by Gemini")

        raw_text = parts[0].get("text", "")
        parsed = json.loads(raw_text)
        tags = _normalize_tags(parsed.get("tags", []), n=n)
        if tags:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Gemini tags generated in %sms model=%s domain=%s tags=%s",
                elapsed_ms,
                gemini_model,
                domain or '-',
                tags,
            )
            return tags

        raise ValueError("Gemini returned empty tags")
    except Exception as e:
        fallback_tags = generate_tags(text, n=n)
        error_description = _describe_gemini_error(e)
        error_payload = _sanitize_gemini_error_payload(e)
        logger.warning(
            "Gemini tag generation failed for domain=%s model=%s; using fallback tags=%s error=%s",
            domain or '-',
            gemini_model,
            fallback_tags,
            error_description,
        )
        if error_payload is not None:
            logger.warning(
                "Gemini error payload domain=%s model=%s payload=%s",
                domain or '-',
                gemini_model,
                json.dumps(error_payload, ensure_ascii=True, separators=(',', ':')),
            )
        return fallback_tags


def generate_tags(text, n=3):
    """Generate up to `n` keyword-like tags from `text` using a simple frequency-based approach.

    This is a lightweight fallback extractor (no external models). It lowercases,
    splits on non-word chars, removes short tokens and a small stopword list,
    and returns the top `n` tokens.
    """
    if not text:
        return []

    # Small bilingual stopword list (English + Italian common words)
    stopwords = {
        'the','and','for','with','that','this','from','are','was','will','have','has','not','but','you','your',
        'per','una','un','il','la','le','di','e','che','da','in','su','con','del','della'
    }

    tokens = [t.lower() for t in re.findall(r"\w+", text, flags=re.UNICODE) if len(t) > 2]
    tokens = [t for t in tokens if t not in stopwords and not t.isdigit()]
    if not tokens:
        return []

    counts = Counter(tokens)
    most_common = [t for t, _ in counts.most_common(n*3)]  # take a few more to dedupe

    # Normalize tags: remove duplicates preserving order
    seen = set()
    tags = []
    for t in most_common:
        if t in seen: continue
        seen.add(t)
        tags.append(t)
        if len(tags) >= n:
            break

    return tags