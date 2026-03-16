"""
ComfortLighting AI Research Agent.

Runs an agentic loop using Claude tool-use to research a company and
return a LeadResearchResult ready to pre-populate the Add Lead form.
"""
import json
import os
import time
import uuid
from datetime import datetime
from typing import Optional

import anthropic

from .schemas.lead_research_result import FieldResult, LeadResearchResult
from .tools.web_search import web_search
from .tools.fetch_url import fetch_url
from .tools.calculate_roi import calculate_roi

# ── Agent tool definitions ─────────────────────────────────────────────────────

TOOLS = [
    {
        'name': 'web_search',
        'description': (
            'Search the internet for information about a company. '
            'Returns a list of results with title, URL, and snippet. '
            'Use specific queries like "CompanyName facility address sq ft" or '
            '"CompanyName operations manager contact".'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The search query string.',
                },
            },
            'required': ['query'],
        },
    },
    {
        'name': 'fetch_url',
        'description': (
            'Fetch and parse the plain-text content of a URL. '
            'Use this to read company websites, About/Team pages, '
            'news articles, and property records after finding URLs via web_search.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                    'description': 'The full URL to fetch (must start with http:// or https://).',
                },
            },
            'required': ['url'],
        },
    },
    {
        'name': 'calculate_roi',
        'description': (
            'Calculate the LED lighting retrofit ROI for a prospect. '
            'Call this once you have sq_footage and facility_type. '
            'Returns annual_savings_usd, kwh_savings, payback_years, '
            'net_5yr_savings, installed_cost, rebate_estimate.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'sq_footage': {
                    'type': 'number',
                    'description': 'Facility square footage (required).',
                },
                'facility_type': {
                    'type': 'string',
                    'description': (
                        'Type of facility: warehouse, cold storage, lab, '
                        'manufacturing, showroom, garage, distribution center, other.'
                    ),
                },
                'utility_rate': {
                    'type': 'number',
                    'description': (
                        'Local electricity rate in $/kWh. '
                        'Use 0.13 (US commercial average) if unknown.'
                    ),
                },
            },
            'required': ['sq_footage', 'facility_type'],
        },
    },
]

MAX_ITERATIONS = 20
TIMEOUT_SECS   = 55   # Leave 5 s headroom under Flask's 60 s limit


# ── System prompt ──────────────────────────────────────────────────────────────

def _load_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), 'prompts', 'research_system_prompt.txt')
    with open(path, encoding='utf-8') as f:
        return f.read()


# ── Tool dispatcher ────────────────────────────────────────────────────────────

def _dispatch(name: str, inputs: dict) -> str:
    try:
        if name == 'web_search':
            result = web_search(inputs.get('query', ''))
        elif name == 'fetch_url':
            result = fetch_url(inputs.get('url', ''))
        elif name == 'calculate_roi':
            result = calculate_roi(
                sq_footage=float(inputs.get('sq_footage', 0)),
                facility_type=str(inputs.get('facility_type', 'warehouse')),
                utility_rate=inputs.get('utility_rate'),
            )
        else:
            result = {'error': f'Unknown tool: {name}'}
    except Exception as exc:
        result = {'error': str(exc)}
    return json.dumps(result)


# ── JSON parser ────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Extract the first JSON object from a text string."""
    import re
    match = re.search(r'\{[\s\S]+\}', text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _make_field(data: dict, key: str) -> FieldResult:
    f = (data or {}).get(key) or {}
    return FieldResult(
        value      = f.get('value') or None,
        confidence = f.get('confidence', 'Not Found'),
        source     = f.get('source') or None,
    )


def _not_found_result(run_id: str, status: str, error: Optional[str],
                      search_count: int, urls_fetched: int,
                      tokens_used: int, duration: float) -> LeadResearchResult:
    nf = FieldResult(value=None, confidence='Not Found', source=None)
    return LeadResearchResult(
        company_name=nf, contact_name=nf, contact_title=nf,
        phone=nf, email=nf, address=nf, sq_footage=nf,
        potential_roi=nf, annual_sales=nf, notes=nf, facility_type=nf,
        employee_count=nf, other_locations=nf, annual_kwh_savings=nf,
        payback_period=nf, website_url=nf, linkedin_url=nf, recent_news=nf,
        agent_run_id=run_id, total_searches=search_count,
        total_urls_fetched=urls_fetched, tokens_used=tokens_used,
        run_duration_sec=round(duration, 2), raw_json='{}',
        status=status, error_message=error,
    )


# ── Log writer ─────────────────────────────────────────────────────────────────

def _write_log(run_id: str, company_searched: str, user_id: int,
               result: LeadResearchResult) -> None:
    from ..models import db, AgentResearchLog
    form_fields = result.to_form_dict()
    populated   = sum(1 for f in form_fields.values() if f.get('value'))
    not_found   = len(form_fields) - populated

    log = AgentResearchLog(
        run_id           = run_id,
        company_searched = company_searched,
        user_id          = user_id,
        fields_populated = populated,
        fields_not_found = not_found,
        tokens_used      = result.tokens_used,
        run_duration_sec = result.run_duration_sec,
        search_count     = result.total_searches,
        urls_fetched     = result.total_urls_fetched,
        raw_json         = result.raw_json or '{}',
        status           = result.status,
        error_message    = result.error_message,
    )
    try:
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ── Main entry point ───────────────────────────────────────────────────────────

def run_research_agent(company_name: str, location_hint: str,
                       run_id: str, user_id: int) -> LeadResearchResult:
    """
    Run the full research agent for a given company name.
    Always writes to agent_research_log before returning.
    """
    from flask import current_app
    from ..models import db, AgentResearchLog, SystemConfig

    start_time    = time.time()
    search_count  = 0
    urls_fetched  = 0
    tokens_used   = 0
    status        = 'success'
    error_message = None

    current_app.logger.info('[agent %s] starting research for %r (location=%r)', run_id, company_name, location_hint)

    # ── Daily token budget check ───────────────────────────────────────────────
    try:
        budget = int(SystemConfig.get('agent_daily_token_budget', '500000'))
    except (TypeError, ValueError):
        budget = 500_000

    today_start  = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        today_tokens = (
            db.session.query(db.func.sum(AgentResearchLog.tokens_used))
            .filter(AgentResearchLog.created_at >= today_start)
            .scalar() or 0
        )
    except Exception:
        db.session.rollback()
        today_tokens = 0   # table may not exist yet; skip budget check
    current_app.logger.info('[agent %s] budget=%d today_tokens=%d', run_id, budget, today_tokens)
    if today_tokens >= budget:
        current_app.logger.info('[agent %s] daily budget exceeded — aborting', run_id)
        result = _not_found_result(
            run_id, 'error',
            'Daily token budget exceeded. Try again tomorrow.',
            0, 0, 0, 0.0,
        )
        _write_log(run_id, company_name, user_id, result)
        return result

    # ── Build client and messages ──────────────────────────────────────────────
    api_key = current_app.config.get('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY', '')
    current_app.logger.info('[agent %s] ANTHROPIC_API_KEY present=%s (len=%d)',
                            run_id, bool(api_key), len(api_key))
    client  = anthropic.Anthropic(api_key=api_key)

    query_str = company_name
    if location_hint:
        query_str += f' ({location_hint})'

    system_prompt = _load_system_prompt()
    messages = [
        {
            'role': 'user',
            'content': (
                f'Research this company for ComfortLighting lead generation: {query_str}\n\n'
                'Use your tools to gather all required data points, then return '
                'the complete LeadResearchResult JSON object as your final response.'
            ),
        }
    ]

    final_data: dict = {}

    # ── Agentic loop ───────────────────────────────────────────────────────────
    try:
        for iteration in range(MAX_ITERATIONS):
            elapsed = time.time() - start_time
            if elapsed > TIMEOUT_SECS:
                current_app.logger.info('[agent %s] timeout after %.1fs at iteration %d', run_id, elapsed, iteration)
                status = 'timeout'
                break

            current_app.logger.info('[agent %s] iteration %d — calling Claude (tokens_so_far=%d)', run_id, iteration, tokens_used)
            response = client.messages.create(
                model      = 'claude-sonnet-4-6',
                max_tokens = 4096,
                system     = system_prompt,
                tools      = TOOLS,
                messages   = messages,
            )

            tokens_used += response.usage.input_tokens + response.usage.output_tokens
            current_app.logger.info('[agent %s] iteration %d — stop_reason=%s tokens_used=%d',
                                    run_id, iteration, response.stop_reason, tokens_used)

            if response.stop_reason == 'end_turn':
                for block in response.content:
                    if hasattr(block, 'text') and block.text:
                        final_data = _parse_json(block.text)
                current_app.logger.info('[agent %s] end_turn — final_data keys=%s', run_id, list(final_data.keys()))
                break

            if response.stop_reason == 'tool_use':
                messages.append({'role': 'assistant', 'content': response.content})
                tool_results = []

                for block in response.content:
                    if block.type == 'tool_use':
                        current_app.logger.info('[agent %s] tool_call: %s(%s)', run_id, block.name,
                                                str(block.input)[:120])
                        output = _dispatch(block.name, block.input)
                        current_app.logger.info('[agent %s] tool_result: %s → %s', run_id, block.name,
                                                output[:200])
                        tool_results.append({
                            'type':        'tool_result',
                            'tool_use_id': block.id,
                            'content':     output,
                        })
                        if block.name == 'web_search':
                            search_count += 1
                        elif block.name == 'fetch_url':
                            urls_fetched += 1

                messages.append({'role': 'user', 'content': tool_results})
            else:
                current_app.logger.info('[agent %s] unexpected stop_reason=%s — exiting loop', run_id, response.stop_reason)
                break

    except anthropic.APITimeoutError:
        status        = 'timeout'
        error_message = 'Anthropic API timed out.'
        current_app.logger.error('[agent %s] Anthropic API timeout', run_id)
    except Exception as exc:
        status        = 'error'
        error_message = str(exc)[:500]
        current_app.logger.error('[agent %s] %s: %s', run_id, company_name, exc, exc_info=True)

    duration = time.time() - start_time

    if status == 'success' and not final_data:
        status = 'partial'

    raw_json_str = json.dumps(final_data) if final_data else '{}'

    result = LeadResearchResult(
        company_name      = _make_field(final_data, 'company_name'),
        contact_name      = _make_field(final_data, 'contact_name'),
        contact_title     = _make_field(final_data, 'contact_title'),
        phone             = _make_field(final_data, 'phone'),
        email             = _make_field(final_data, 'email'),
        address           = _make_field(final_data, 'address'),
        sq_footage        = _make_field(final_data, 'sq_footage'),
        potential_roi     = _make_field(final_data, 'potential_roi'),
        annual_sales      = _make_field(final_data, 'annual_sales'),
        notes             = _make_field(final_data, 'notes'),
        facility_type     = _make_field(final_data, 'facility_type'),
        employee_count    = _make_field(final_data, 'employee_count'),
        other_locations   = _make_field(final_data, 'other_locations'),
        annual_kwh_savings= _make_field(final_data, 'annual_kwh_savings'),
        payback_period    = _make_field(final_data, 'payback_period'),
        website_url       = _make_field(final_data, 'website_url'),
        linkedin_url      = _make_field(final_data, 'linkedin_url'),
        recent_news       = _make_field(final_data, 'recent_news'),
        agent_run_id      = run_id,
        total_searches    = search_count,
        total_urls_fetched= urls_fetched,
        tokens_used       = tokens_used,
        run_duration_sec  = round(duration, 2),
        raw_json          = raw_json_str,
        status            = status,
        error_message     = error_message,
    )

    _write_log(run_id, company_name, user_id, result)
    return result
