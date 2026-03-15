"""
Web search tool using Serper API (Google results).
Falls back gracefully if SERPER_API_KEY is not configured.
"""
import os

import requests


def web_search(query: str, num_results: int = 5) -> dict:
    """
    Search the internet for the given query.
    Returns {'results': [...], 'total': N} or {'error': '...', 'results': []}.
    """
    api_key = os.getenv('SERPER_API_KEY', '')
    if not api_key:
        return {
            'error': 'SERPER_API_KEY is not configured — web search unavailable.',
            'results': [],
        }

    try:
        resp = requests.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY':     api_key,
                'Content-Type':  'application/json',
            },
            json={'q': query, 'num': num_results, 'gl': 'us'},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get('organic', [])[:num_results]:
            results.append({
                'title':   item.get('title', ''),
                'url':     item.get('link', ''),
                'snippet': item.get('snippet', ''),
            })

        # Include knowledge graph snippet if present
        if data.get('knowledgeGraph'):
            kg = data['knowledgeGraph']
            results.insert(0, {
                'title':   kg.get('title', ''),
                'url':     kg.get('website', ''),
                'snippet': kg.get('description', ''),
                'source':  'Knowledge Graph',
            })

        return {'results': results, 'total': len(results)}

    except requests.exceptions.Timeout:
        return {'error': 'Search timed out.', 'results': []}
    except Exception as exc:
        return {'error': str(exc), 'results': []}
