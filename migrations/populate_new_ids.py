"""
ComfortLighting — Alphanumeric ID Migration Runner
Phase 3 (continued): Populate new_id for all existing rows.

Run during maintenance window AFTER running STEP 3 of alphanumeric_id_migration.sql
(which adds the new_id columns).

Usage:
    cd /path/to/comfortlighting
    python migrations/populate_new_ids.py

The script:
  1. Generates a unique alphanumeric ID for every existing row in all 11 tables.
  2. Writes the new ID to the new_id column.
  3. Verifies no NULL values remain after the update.
  4. Prints a summary with row counts.

After this script completes, continue with STEP 4 onward in
alphanumeric_id_migration.sql.
"""

import sys
import os

# Add project root to path so we can import app + utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.id_gen import generate_id
from app import create_app
from app.models import db
from sqlalchemy import text

TABLES = [
    'users',
    'leads',
    'proposals',
    'contracts',
    'contract_versions',
    'clause_templates',
    'lead_activities',
    'expense_categories',
    'lead_stage_history',
    'agent_research_log',
    'system_config',
]


def populate_new_ids():
    app = create_app()
    with app.app_context():
        print('=== ComfortLighting Alphanumeric ID Migration ===')
        print('Populating new_id columns for all tables...\n')

        for table in TABLES:
            print(f'Processing {table}...')
            rows = db.session.execute(text(f'SELECT id FROM {table}')).fetchall()

            if not rows:
                print(f'  (empty table — skipped)')
                continue

            used = set()
            batch_size = 500
            batch = []

            for (old_id,) in rows:
                new_id = generate_id(table)
                # In-memory collision avoidance (probability negligible but safe)
                while new_id in used:
                    new_id = generate_id(table)
                used.add(new_id)
                batch.append({'new_id': new_id, 'old_id': old_id})

                if len(batch) >= batch_size:
                    _execute_batch(db, table, batch)
                    batch = []

            if batch:
                _execute_batch(db, table, batch)

            db.session.commit()

            # Verify no NULLs remain
            null_count = db.session.execute(
                text(f'SELECT COUNT(*) FROM {table} WHERE new_id IS NULL')
            ).scalar()
            assert null_count == 0, (
                f'ERROR: {null_count} NULL new_id values remain in {table}!'
            )

            print(f'  OK — {len(rows)} rows updated')

        print('\n=== All tables populated successfully ===')
        print('\nNext step: Run STEP 4 onward in alphanumeric_id_migration.sql')


def _execute_batch(db, table, batch):
    for item in batch:
        db.session.execute(
            text(f'UPDATE {table} SET new_id = :new_id WHERE id = :old_id'),
            item
        )


if __name__ == '__main__':
    populate_new_ids()
