"""
URL fetcher tool using requests + BeautifulSoup.
Strips navigation, scripts, and boilerplate before returning plain text.
"""
import re

import requests

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; ComfortLightingResearch/1.0; '
        '+https://comfortlighting.net)'
    ),
    'Accept': 'text/html,application/xhtml+xml',
}

MAX_RESPONSE_BYTES = 512 * 1024   # 512 KB cap — avoids huge downloads
MAX_TEXT_CHARS     = 6000         # Chars returned to the agent


def fetch_url(url: str) -> dict:
    """
    Fetch a URL and return its cleaned plain-text content.
    Returns {'url': ..., 'text': ..., 'length': N} or {'url': ..., 'error': ...}.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return {'url': url, 'error': 'Invalid URL — must start with http:// or https://.', 'text': ''}

    try:
        resp = requests.get(
            url,
            headers=_HEADERS,
            timeout=12,
            stream=True,
        )
        resp.raise_for_status()

        # Read up to MAX_RESPONSE_BYTES to avoid huge payloads
        content = b''
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= MAX_RESPONSE_BYTES:
                break

        # Detect encoding
        encoding = resp.encoding or 'utf-8'
        html = content.decode(encoding, errors='replace')

        # Parse with BeautifulSoup if available, else regex strip
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer',
                             'header', 'aside', 'noscript']):
                tag.decompose()
            text = soup.get_text(separator=' ', strip=True)
        except ImportError:
            text = re.sub(r'<[^>]+>', ' ', html)

        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return {
            'url':    url,
            'text':   text[:MAX_TEXT_CHARS],
            'length': len(text),
        }

    except requests.exceptions.Timeout:
        return {'url': url, 'error': 'Request timed out.', 'text': ''}
    except requests.exceptions.TooManyRedirects:
        return {'url': url, 'error': 'Too many redirects.', 'text': ''}
    except Exception as exc:
        return {'url': url, 'error': str(exc)[:200], 'text': ''}
