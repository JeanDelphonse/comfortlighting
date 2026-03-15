import os
import re
import anthropic

SYSTEM_PROMPT = (
    "You are a concise lighting sales proposal writer for ComfortLighting.net.\n"
    "Write a brief, professional proposal using only the client data provided.\n"
    "Use few words. No filler. Lead with value.\n"
    "Structure your response in exactly these five labeled sections:\n"
    "  1. GREETING - One sentence. Address contact by name.\n"
    "  2. PROBLEM - One or two sentences. Name their lighting challenge.\n"
    "  3. SOLUTION - Two to three sentences. How ComfortLighting solves it.\n"
    "  4. VALUE - One to two sentences. ROI, energy savings, uptime, or compliance.\n"
    "  5. NEXT STEP - One sentence. Clear call to action.\n"
    "Do not include pricing. Do not include headers or markdown. Plain text only."
)


def build_prompt(lead) -> str:
    def v(val):
        return str(val) if val is not None else "Not provided"

    return (
        f"Client: {v(lead.company_name)}\n"
        f"Contact: {v(lead.contact)}\n"
        f"Location: {v(lead.address)}\n"
        f"Facility Size: {v(lead.sq_ft)} sq ft\n"
        f"Target Zones: {v(lead.targets)}\n"
        f"Estimated ROI: {v(lead.roi)}%\n"
        f"Other Locations / Scale: {v(lead.annual_sales_locations)}\n"
        f"Notes / Context: {v(lead.notes)}\n"
        "Write the proposal now."
    )


def generate(lead) -> str:
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        timeout=30.0,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': build_prompt(lead)}],
    )
    return message.content[0].text


def parse_sections(text: str) -> dict:
    result = {
        'greeting': '',
        'problem': '',
        'solution': '',
        'value_prop': '',
        'next_step': '',
    }

    # Pattern matches labels like "1. GREETING", "GREETING:", "GREETING —", "GREETING -", etc.
    pattern = (
        r'(?:(?:\d+\.\s*)?GREETING\s*[-—:]?\s*)'
        r'|(?:(?:\d+\.\s*)?PROBLEM\s*[-—:]?\s*)'
        r'|(?:(?:\d+\.\s*)?SOLUTION\s*[-—:]?\s*)'
        r'|(?:(?:\d+\.\s*)?VALUE(?:\s+PROP(?:OSITION)?)?\s*[-—:]?\s*)'
        r'|(?:(?:\d+\.\s*)?NEXT\s+STEP\s*[-—:]?\s*)'
    )

    parts = re.split(pattern, text, flags=re.IGNORECASE)
    labels = re.findall(pattern, text, flags=re.IGNORECASE)

    def normalise(label: str) -> str:
        label = label.upper().strip(' \t\n\r-—:')
        if 'GREETING' in label:
            return 'greeting'
        if 'PROBLEM' in label:
            return 'problem'
        if 'SOLUTION' in label:
            return 'solution'
        if 'VALUE' in label:
            return 'value_prop'
        if 'NEXT' in label:
            return 'next_step'
        return ''

    for i, label in enumerate(labels):
        key = normalise(label)
        if key and i + 1 < len(parts):
            result[key] = parts[i + 1].strip()

    return result
