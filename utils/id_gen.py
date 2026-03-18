import re
import secrets
import string
from datetime import datetime, timezone

# Character set: uppercase A-Z (excluding I, O) + digits 2-9 (excluding 0, 1)
SAFE_CHARS = ''.join([
    c for c in string.ascii_uppercase if c not in ('I', 'O')
]) + '23456789'
# SAFE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  (32 characters)

# Table prefix registry
PREFIX_MAP = {
    'users':              'USR',
    'leads':              'LED',
    'proposals':          'PRP',
    'contracts':          'CON',
    'contract_versions':  'CVR',
    'clause_templates':   'CLT',
    'lead_activities':    'ACT',
    'expense_categories': 'EXC',
    'lead_stage_history': 'LSH',
    'agent_research_log': 'ARL',
    'system_config':      'CFG',
}

# Regex pattern for validating IDs: PREFIX-YYMMDD-RANDOM6
ID_PATTERN = re.compile(
    r'^(USR|LED|PRP|CON|CVR|CLT|ACT|EXC|LSH|ARL|CFG)-'
    r'\d{6}-'
    r'[A-HJ-NP-Z2-9]{6}$'
)


def generate_id(table_name: str) -> str:
    """
    Generate a unique alphanumeric ID for the given table.
    Format: {PREFIX}-{YYMMDD}-{RANDOM6}
    Example: LED-250318-K7X2MQ
    """
    prefix = PREFIX_MAP.get(table_name)
    if not prefix:
        raise ValueError(f'Unknown table: {table_name}')
    date   = datetime.now(timezone.utc).strftime('%y%m%d')
    suffix = ''.join(secrets.choice(SAFE_CHARS) for _ in range(6))
    return f'{prefix}-{date}-{suffix}'


def make_id(table_name: str):
    """
    Factory that returns a zero-argument callable for use as a
    SQLAlchemy column default.
    Usage: id = Column(String(17), primary_key=True,
                       default=make_id('leads'))
    """
    return lambda: generate_id(table_name)


def is_valid_id(value: str) -> bool:
    """Return True if the string matches the ComfortLighting ID format."""
    return bool(ID_PATTERN.match(value))


def validate_id_param(id_value: str, expected_prefix: str = None):
    """
    Validate an ID from a URL parameter.
    Raises ValueError if format is invalid or prefix does not match.
    Use in Flask routes before querying the database.
    """
    if not is_valid_id(id_value):
        raise ValueError(f'Invalid ID format: {id_value}')
    if expected_prefix and not id_value.startswith(expected_prefix + '-'):
        raise ValueError(f'Expected {expected_prefix} prefix, got: {id_value}')


def generate_unique_id(table_name: str, db_session) -> str:
    """
    Generate an ID and verify it does not already exist in the table.
    Retries up to 5 times before raising an error.
    In practice, collision probability is < 1 in 1 billion per day.
    """
    from sqlalchemy import text
    for attempt in range(5):
        new_id = generate_id(table_name)
        result = db_session.execute(
            text(f'SELECT 1 FROM {table_name} WHERE id = :id'),
            {'id': new_id}
        ).fetchone()
        if result is None:
            return new_id
    raise RuntimeError(f'Could not generate unique ID for {table_name} after 5 attempts')
