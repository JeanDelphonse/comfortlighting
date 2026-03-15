import os
import re
import anthropic

SYSTEM_PROMPT = (
    "You are a legal contract assembly engine for ComfortLighting.net.\n"
    "You populate pre-approved legal clause templates with client data.\n\n"
    "RULES — STRICTLY ENFORCED:\n"
    "  1. Use ONLY the clause templates provided. Do not invent new clauses.\n"
    "  2. Substitute ALL placeholders (shown as {{PLACEHOLDER}}) with client data.\n"
    "  3. Do not change any legal language, obligations, or liability terms.\n"
    "  4. Do not add, remove, or reorder contract sections.\n"
    "  5. If a data field is missing, insert [TO BE CONFIRMED] as the placeholder.\n"
    "  6. Output must be plain text, section by section, using the exact section headings provided.\n"
    "  7. Do not add preamble, commentary, or markdown formatting.\n\n"
    "Output each section on a new line prefixed with its heading label.\n"
    "Example: PARTIES: [populated text here]"
)

# Maps section headings in LLM output to DB column names
SECTION_MAP = [
    ('PARTIES',               'section_parties'),
    ('RECITALS',              'section_recitals'),
    ('SCOPE OF WORK',         'section_scope'),
    ('COMPENSATION',          'section_compensation'),
    ('TIMELINE',              'section_timeline'),
    ('WARRANTIES',            'section_warranties'),
    ('PERFORMANCE GUARANTEE', 'section_performance'),
    ('INDEMNIFICATION',       'section_indemnification'),
    ('LIMITATION OF LIABILITY','section_liability'),
    ('TERMINATION',           'section_termination'),
    ('DISPUTE RESOLUTION',    'section_dispute'),
    ('GOVERNING LAW',         'section_governing_law'),
    ('NOTICES',               'section_notices'),
    ('ENTIRE AGREEMENT',      'section_entire_agreement'),
    ('SIGNATURE BLOCK',       'section_signatures'),
]

CLAUSE_KEYS = [
    'PARTIES_TEMPLATE', 'RECITALS_TEMPLATE', 'SCOPE_OF_WORK_TEMPLATE',
    'COMPENSATION_TEMPLATE', 'TIMELINE_TEMPLATE', 'WARRANTY_TEMPLATE',
    'PERFORMANCE_GUARANTEE_TEMPLATE', 'INDEMNIFICATION_TEMPLATE',
    'LIMITATION_OF_LIABILITY_TEMPLATE', 'TERMINATION_TEMPLATE',
    'DISPUTE_RESOLUTION_TEMPLATE', 'GOVERNING_LAW_TEMPLATE',
    'NOTICES_TEMPLATE', 'ENTIRE_AGREEMENT_TEMPLATE', 'SIGNATURE_BLOCK_TEMPLATE',
]


def build_contract_prompt(lead, templates: dict) -> str:
    def v(val):
        return str(val).strip() if val is not None else 'Not provided'

    data_block = (
        f"CLIENT DATA:\n"
        f"  Company:       {v(lead.company_name)}\n"
        f"  Contact:       {v(lead.contact)}\n"
        f"  Address:       {v(lead.address)}\n"
        f"  Email:         {v(lead.email)}\n"
        f"  Facility Size: {v(lead.sq_ft)} sq ft\n"
        f"  Target Zones:  {v(lead.targets)}\n"
        f"  ROI Estimate:  {v(lead.roi)}%\n"
        f"  Start Date:    {v(lead.expected)}\n"
        f"  Other Sites:   {v(lead.annual_sales_locations)}\n"
        f"  Notes:         {v(lead.notes)}\n\n"
        f"CLAUSE TEMPLATES TO POPULATE:\n"
    )
    for key in CLAUSE_KEYS:
        tmpl = templates.get(key, f'[{key} — TEMPLATE NOT FOUND]')
        data_block += f"  [{key}]\n  {tmpl}\n\n"
    data_block += "Assemble the contract now."
    return data_block


def generate(lead, templates: dict) -> str:
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=4096,
        timeout=60.0,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': build_contract_prompt(lead, templates)}],
    )
    return message.content[0].text


def parse_contract_sections(text: str) -> dict:
    """Split LLM output into named contract sections."""
    import logging
    logger = logging.getLogger(__name__)

    result = {col: '' for _, col in SECTION_MAP}
    headings = [h for h, _ in SECTION_MAP]
    # Build split pattern on all headings
    pattern = r'(?m)^(' + '|'.join(re.escape(h) for h in headings) + r')\s*:'
    parts = re.split(pattern, text)
    # parts = [pre, heading1, content1, heading2, content2, ...]
    if len(parts) >= 3:
        i = 1
        while i < len(parts) - 1:
            heading = parts[i].strip().upper()
            content = parts[i + 1].strip()
            matched = False
            for h, col in SECTION_MAP:
                if h == heading:
                    result[col] = content
                    matched = True
                    break
            if not matched:
                logger.warning(f'Contract parser: unrecognised heading "{heading}"')
            i += 2

    for heading, col in SECTION_MAP:
        if not result[col]:
            result[col] = '[SECTION MISSING — REVIEW REQUIRED]'
            logger.warning(f'Contract section missing: {heading}')

    return result
