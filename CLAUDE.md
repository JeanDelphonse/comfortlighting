# CLAUDE.md — ComfortLighting Lead Inventory System

## Project Overview
Flask web application for ComfortLighting.net. A lead inventory and sales pipeline management system with AI-powered proposal and contract generation, lead user assignment, WIP board, and sales activity/expense tracking. Deployed on GoDaddy cPanel via Passenger WSGI.

## Stack
- **Backend:** Python 3.11, Flask 3.x, SQLAlchemy + PyMySQL, Flask-Login, Flask-WTF (CSRF), Flask-Limiter
- **LLM:** Anthropic Claude API (`anthropic` SDK) — model `claude-sonnet-4-6`
- **PDF:** ReportLab (pure Python, GoDaddy-safe — do NOT switch to WeasyPrint without verifying GTK availability)
- **DB:** MySQL (cPanel localhost), schema in `sql/schema.sql`. SQLite supported for local dev (`sqlite:///comfortlighting.db`)
- **Deployment:** GoDaddy cPanel, Passenger WSGI entry point `passenger_wsgi.py`
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, vanilla JS (no framework)

## Project Structure
```
comfortlighting/
├── passenger_wsgi.py          # WSGI entry point — must export `application`
├── app.py                     # Dev server entry point
├── config.py                  # Config class (loads .env); UPLOAD_FOLDER, MAX_CONTENT_LENGTH
├── set_admin_password.py      # One-time password reset CLI tool
├── uploads/                   # Receipt file storage (NOT web-accessible; served via Flask)
│   └── receipts/{lead_id}/    # Files named {entry_id}_{timestamp}.{ext}
├── app/
│   ├── __init__.py            # create_app() factory, blueprints, context_processor (pending_expense_count)
│   │                          # Logging: error.log (ERROR+), research.log (INFO+), console in debug mode
│   ├── extensions.py          # Flask-Limiter singleton (avoids circular imports)
│   ├── decorators.py          # Shared decorators: admin_required
│   ├── models.py              # SQLAlchemy models: User, Lead, LeadStageHistory, Proposal, Contract,
│   │                          #   ContractVersion, ClauseTemplate, SystemConfig,
│   │                          #   ExpenseCategory, LeadActivity, AgentResearchLog
│   ├── constants.py           # ACTION_VALUES, PROGRESS_VALUES, ACTION_BADGE_CLASS, LEADS_PER_PAGE
│   ├── auth/routes.py         # /login, /logout
│   ├── leads/routes.py        # /, /leads/add, /leads/<id>, /leads/<id>/edit, /leads/<id>/delete
│   │                          # /leads/<id>/wip (PATCH) — toggle WIP via progress field
│   │                          # /leads/<id>/progress (PATCH) — pipeline stage change; returns diagram HTML fragment
│   │                          # /leads/<id>/hold (POST) — place On Hold (saves previous_progress)
│   │                          # /leads/<id>/unhold (POST) — remove On Hold (restores previous_progress)
│   │                          # /leads/<id>/stage-history (GET) — JSON stage history for a lead
│   │                          # /leads/research (POST) — AI agent research endpoint
│   │                          # PIPELINE_STAGES list + _build_diagram_context() helper in routes.py
│   │                          # validate_lead() handles assigned_user_id server-side
│   ├── admin/routes.py        # /admin/users, /admin/clause-templates, /admin/clause-templates/<key>
│   │                          # /admin/expenses, /admin/expenses/approve|reject|reimburse|export
│   │                          # /admin/settings/mileage-rate
│   │                          # /admin/research-log, /admin/research-log/<run_id>
│   ├── proposals/
│   │   ├── llm.py             # generate(), parse_sections(), build_prompt(), SYSTEM_PROMPT
│   │   ├── pdf.py             # render_pdf(lead, proposal) → bytes (ReportLab)
│   │   └── routes.py          # /proposals/generate, /proposals/save, /proposals/<id>/pdf, /proposals/mark_sent
│   ├── contracts/
│   │   ├── llm.py             # generate(), parse_contract_sections(), build_contract_prompt(), SECTION_MAP
│   │   ├── pdf.py             # render_pdf(lead, contract) → bytes (ReportLab, DRAFT watermark)
│   │   └── routes.py          # /contracts/generate, /contracts/<id>/save, /contracts/<id>/approve,
│   │                          # /contracts/<lead_id>/pdf, /contracts/<id>/mark_sent, /contracts/<id>/versions
│   │                          # Protected by role_required('admin', 'legal') — returns JSON 403 on fail
│   ├── activities/
│   │   └── routes.py          # /leads/<id>/activities (log), /leads/<id>/activities/add,
│   │                          # /leads/<id>/activities/<entry_id> (view/edit/delete/submit)
│   │                          # /leads/<id>/activities/receipt/<entry_id>
│   │                          # /expenses/subcategories (AJAX)
│   │                          # Access: admin always; sales only if lead.assigned_user_id == current_user.id
│   ├── agent/                     # AI Agent Lead Research package
│   │   ├── __init__.py
│   │   ├── research_agent.py      # run_research_agent() — Claude tool-use agentic loop
│   │   │                          # MAX_ITERATIONS=6, TIMEOUT_SECS=25 (tuned for GoDaddy shared hosting)
│   │   ├── prompts/
│   │   │   └── research_system_prompt.txt  # Agent system prompt — strict 3 tool call budget
│   │   ├── schemas/
│   │   │   └── lead_research_result.py     # FieldResult, LeadResearchResult dataclasses
│   │   └── tools/
│   │       ├── web_search.py      # Serper API wrapper
│   │       ├── fetch_url.py       # URL fetcher with BeautifulSoup text extraction
│   │       └── calculate_roi.py   # LED retrofit ROI calculator (loads params from system_config)
│   ├── static/
│   │   ├── .htaccess              # Require all granted — fixes Apache permission error on GoDaddy
│   │   ├── css/app.css            # Includes .confidence-badge, .confidence-high/medium/low styles
│   │   ├── css/pipeline_diagram.css  # Arrow states, draw-on @keyframes, pulse-ring, On Hold badge
│   │   └── js/
│   │       ├── app.js
│   │       ├── activity_form.js   # Category AJAX, mileage calc, conditional fields
│   │       ├── wip_board.js       # WIP drag-and-drop (native HTML5 events, not SortableJS)
│   │       │                      # Auto-reloads page 6s after drop (undo cancels reload)
│   │       ├── agent_autofill.js  # Research button, progress bar, field population, badges
│   │       └── pipeline_diagram.js  # Stage node clicks, modal open/confirm, PATCH fetch, DOM replace
│   └── templates/
│       ├── base.html              # Includes Expenses nav link + pending badge for admin
│       │                          # Includes pipeline_diagram.css and pipeline_diagram.js globally
│       ├── auth/login.html
│       ├── leads/index.html, add.html, edit.html, view.html, _form.html
│       │   leads/_progress_diagram.html  # SVG pipeline diagram partial (include + AJAX fragment render)
│       │   leads/_stage_modal.html       # Bootstrap stage-change confirmation modal
│       │                          # add.html: RESEARCH_URL uses url_for(_external=True) for absolute URL
│       │                          # add.html: Research button disabled if SERPER_API_KEY not set
│       │                          # _form.html has data-agent-field attributes on wrappers
│       ├── activities/form.html, log.html, view_entry.html
│       └── admin/users.html, clause_templates.html, expense_queue.html, research_log.html
├── sql/
│   ├── schema.sql                         # Full DDL — all tables for fresh install
│   ├── seed_leads.sql                     # 17 lead records from SalesStatusBlank.xlsx
│   ├── seed_clause_templates.sql          # 15 legal clause templates with {{PLACEHOLDER}} tokens
│   ├── migrate_add_legal_role.sql         # ALTER TABLE users — add 'legal' role
│   ├── migration_add_assigned_user.sql    # ALTER TABLE leads — add assigned_user_id FK
│   ├── migration_add_wip_columns.sql      # ALTER TABLE leads — add wip, wip_since columns
│   ├── migration_system_config.sql        # CREATE system_config; seed IRS mileage rate
│   ├── migration_create_lead_activities.sql  # CREATE expense_categories + lead_activities; seed categories
│   ├── migration_agent_research.sql       # CREATE agent_research_log; ALTER leads ADD agent_research_run_id;
│   │                                      # seed 8 ROI config params + agent_daily_token_budget=2000000
│   └── migration_workflow_diagram.sql     # ALTER leads ADD previous_progress, stage_changed_at;
│                                          # CREATE lead_stage_history (with days_in_stage column)
├── docs/
│   └── *.docx / *.xlsx                    # PRD documents and seed data spreadsheet
└── logs/
    ├── error.log                          # RotatingFileHandler, 5 MB × 5 backups, ERROR level only
    └── research.log                       # RotatingFileHandler, 5 MB × 3 backups, INFO+ always on
```

## Running Locally
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY
python app.py
```

**SQLite for local dev** (no MySQL needed):
```
DATABASE_URL=sqlite:///comfortlighting.db
```
Then create tables:
```bash
python -c "from app import create_app, db; app=create_app(); app.app_context().push(); db.create_all()"
```
Create admin user:
```bash
python -c "
from app import create_app, db
from app.models import User, SystemConfig
app = create_app()
with app.app_context():
    u = User(username='admin', email='admin@example.com', role='admin', active=True)
    u.set_password('admin123')
    db.session.add(u)
    db.session.add(SystemConfig(config_key='irs_mileage_rate', config_value='0.67'))
    db.session.commit()
"
```

## Environment Variables (`.env`)
| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `DATABASE_URL` | Yes | `mysql+pymysql://user:pass@localhost/comfortlighting` or `sqlite:///comfortlighting.db` |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for proposal/contract/agent research |
| `SERPER_API_KEY` | No | Serper.dev API key — Research button disabled if absent |
| `AGENT_DAILY_TOKEN_BUDGET` | No | Not used directly — budget stored in `system_config` table (default: 2000000) |

## Database
All schema in `sql/schema.sql`. Tables: `users`, `leads`, `proposals`, `contracts`, `contract_versions`, `clause_templates`, `system_config`, `expense_categories`, `lead_activities`, `agent_research_log`.

**On first deploy (fresh install):**
1. Run `schema.sql` in phpMyAdmin
2. Run `seed_clause_templates.sql` to load 15 contract clause templates
3. Run `migration_create_lead_activities.sql` to seed 9 expense categories + 34 subcategories
4. Run `migration_agent_research.sql` to create agent_research_log and seed ROI + token budget config
5. Run `python set_admin_password.py admin <password>` to set admin password
6. Optionally run `seed_leads.sql` for sample lead data

**On upgrade (existing DB — run in order):**
1. `migrate_add_legal_role.sql` — add legal role to users (contract feature)
2. `migration_add_assigned_user.sql` — add assigned_user_id to leads
3. `migration_add_wip_columns.sql` — add wip, wip_since columns to leads
4. `migration_system_config.sql` — create system_config, seed IRS mileage rate
5. `migration_create_lead_activities.sql` — create expense_categories + lead_activities, seed categories
6. `migration_agent_research.sql` — create agent_research_log, add agent_research_run_id to leads, seed ROI config params

**Adjusting agent daily token budget** (if "Daily token budget exceeded" error):
```sql
UPDATE system_config SET config_value = '2000000' WHERE config_key = 'agent_daily_token_budget';
```

## User Roles
| Role | Access |
|---|---|
| `admin` | Full access — leads, users, proposals, contracts, clause templates, all expense entries |
| `legal` | Proposals (read), contracts (generate/edit/approve/export/send) |
| `sales` | Leads (read/write), proposals (generate/edit/export/send), read-only contract status. Activities only for leads assigned to them |

## Key Architectural Rules

### API URLs in JavaScript — CRITICAL
All fetch() URLs MUST be generated via Jinja2 `url_for()`, never hardcoded. The app is deployed at a subdirectory (`/comfortlighting/`) on the server; hardcoded paths like `/proposals/generate` will resolve to the server root and 404.

**For API endpoints called via fetch() — use `_external=True` for absolute URL:**
```javascript
const RESEARCH_URL = "{{ url_for('leads.research_lead', _external=True) }}";
```

**For routes with path parameters — use a data attribute on a DOM element:**
```html
<div id="wip-section" data-toggle-url="{{ url_for('leads.toggle_wip', lead_id=0) }}">
```
```javascript
const tpl = document.getElementById('wip-section').dataset.toggleUrl;
function wipUrl(id) { return tpl.replace('/0/wip', '/' + id + '/wip'); }
```

**For blueprints with a known prefix:**
```javascript
const BASE = "{{ url_for('contracts.generate') }}".replace('/generate', '');
function urlSave(id) { return BASE + '/' + id + '/save'; }
```

### Decorators (`app/decorators.py`)
- `admin_required` — redirect non-admins to lead dashboard with flash. Used in `leads/routes.py` and `admin/routes.py`.
- `role_required(*roles)` — defined locally in `contracts/routes.py` only; returns JSON 403 (contract routes are API-only).
- Do **not** re-define `admin_required` locally in route files — import from `app.decorators`.

### Activity Access Control
`_can_access(lead)` in `activities/routes.py`:
- Admin: always `True`
- Sales: only if `lead.assigned_user_id == current_user.id`
- Returns `False` → `abort(403)` in every activity route

### WIP Board
- WIP criterion: `lead.progress == 'In Progress'` (not a separate `wip` flag)
- Dashboard WIP section queries `Lead.progress == 'In Progress'`; main list excludes these leads
- Drag from lead list → WIP: sets `progress = 'In Progress'`, `wip = 1`, `wip_since = now()`
- Drag from WIP → lead list (or × button): clears `progress`, `wip = 0`, `wip_since = None`
- `wip_board.js` uses native HTML5 drag events (not SortableJS) — required because WIP is a `<div>` grid and the lead list is a `<tbody>`, which are incompatible container types for SortableJS physical element movement
- **Auto-reload:** page reloads 6 seconds after a successful drop (undo cancels the reload timer)

### Blueprint URL Prefixes
| Blueprint | Prefix |
|---|---|
| `auth_bp` | (none) |
| `leads_bp` | (none) |
| `admin_bp` | `/admin` |
| `proposals_bp` | `/proposals` |
| `contracts_bp` | `/contracts` |
| `activities_bp` | (none) — routes start with `/leads/<id>/activities/` or `/expenses/` |

### CSRF on AJAX
All AJAX POST/PATCH requests must include the header `X-CSRFToken`. Config has `WTF_CSRF_HEADERS = ['X-CSRFToken']`. Read token from `<meta name="csrf-token">` (set in `base.html`).

### Limiter
Flask-Limiter singleton defined in `app/extensions.py` (not `app/__init__.py`) to avoid circular imports. Key function uses `current_user.id` for authenticated users, falls back to IP.
- Proposals: 10 LLM calls/hour per user
- Contracts: 5 LLM calls/hour per user
- Agent Research: 20 calls/hour per user (plus daily token budget check via `system_config`)

### Logging
Two log files, always active regardless of debug mode:
- `logs/error.log` — ERROR+ only, 5 MB × 5 backups
- `logs/research.log` — INFO+ for all app logger calls, 5 MB × 3 backups (captures full agent research traces)

In debug mode, INFO+ also streams to console.

### PDF Generation
Use **ReportLab** only. Do not introduce WeasyPrint (requires GTK system libraries not available on GoDaddy shared hosting). Brand colors: Proposal = `#1F4E79` (blue), Contract = `#1A2F4A` (navy).

### Receipt File Uploads
- Stored at `uploads/receipts/{lead_id}/{entry_id}_{timestamp}.{ext}` — NEVER inside `app/static/`
- `UPLOAD_FOLDER` and `MAX_CONTENT_LENGTH = 5 MB` set in `config.py`
- Served exclusively via `activities.receipt` route (authenticated) using `send_file()`
- Server-side MIME validation via magic bytes (no python-magic dependency — stdlib only)
- Allowed types: `.jpg`, `.jpeg`, `.png`, `.pdf`

### Context Processor
`pending_expense_count` is injected into every template for authenticated admins via a context processor in `app/__init__.py`. Used to show the badge on the Expenses nav link. Queries `LeadActivity.status == 'Submitted'` count.

### Deployment Zip
Rebuild `comfortlighting_deploy.zip` after any change. Exclude: `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `.git/`. Include `logs/.gitkeep`, `logs/research.log` (empty), and `uploads/.gitkeep`.

```bash
python -c "
import zipfile, os
include = ['passenger_wsgi.py','app.py','config.py','requirements.txt','.htaccess',
           '.env.example','set_admin_password.py','sql/schema.sql',
           'sql/seed_clause_templates.sql','sql/migrate_add_legal_role.sql',
           'sql/seed_leads.sql','sql/migration_add_assigned_user.sql',
           'sql/migration_add_wip_columns.sql','sql/migration_system_config.sql',
           'sql/migration_create_lead_activities.sql','sql/migration_agent_research.sql']
app_files = []
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith(('.pyc','.pyo')): app_files.append(os.path.join(root, f))
with zipfile.ZipFile('comfortlighting_deploy.zip','w',zipfile.ZIP_DEFLATED) as zf:
    [zf.write(p) for p in include if os.path.exists(p)]
    [zf.write(p) for p in app_files]
    zf.writestr('logs/.gitkeep','')
    zf.writestr('logs/research.log','')
    zf.writestr('uploads/.gitkeep','')
"
```

## Features

### Lead Management
- CRUD for leads with 15 fields (including `assigned_user_id`)
- Filterable/sortable paginated list (25/page) — filters: search, action, progress, assigned user, date range
- Leads with `progress = 'In Progress'` are shown in the WIP board and excluded from the main list
- "Assigned To" column on list; sortable by username (outer join); filter by user or Unassigned
- CSV export with active filters (includes Assigned To column)
- Notes log with timestamp + username prefix
- Session timeout 30 min inactivity

### WIP Board (`/` — dashboard)
- Shows all leads where `progress = 'In Progress'` as draggable cards
- Drag a table row into the WIP section → sets `progress = 'In Progress'`
- Drag a WIP card into the table / click × → clears `progress`, removes from WIP
- Uses native HTML5 drag events; WIP URL generated via `data-toggle-url` attribute (not hardcoded)
- Toast notifications with 6-second undo window; page auto-reloads after undo window expires

### Lead User Assignment
- `assigned_user_id` nullable FK on `leads` → `users.id` (ON DELETE SET NULL)
- Dropdown on Add/Edit forms showing active users alphabetically; "— Unassigned —" default
- Server-side validation: submitted id must be active user or NULL
- Inactive assigned users shown as `username (inactive)` in muted/italic text on list and detail views
- `lead_context()` always injects `active_users` list into add/edit/view routes

### AI Proposal Generation (`/proposals/`)
- LLM: `claude-sonnet-4-6`, max_tokens=1024, timeout=30s
- 5 sections: GREETING, PROBLEM, SOLUTION, VALUE, NEXT STEP
- Stored in `proposals` table (one per lead, upsert on re-generate)
- Edit inline, export branded PDF, mark as sent (auto-sets ACTION → Proposal Sent)
- Rate limited: 10/hour per user

### AI Contract Generation (`/contracts/`)
- Legal/Admin role only (`role_required('admin', 'legal')` — returns JSON 403)
- LLM: `claude-sonnet-4-6`, max_tokens=4096, timeout=60s
- 15 sections sourced from `clause_templates` table (editable by Admin)
- LLM acts as clause assembly engine — populates `{{PLACEHOLDER}}` tokens, does not invent legal language
- Versioned: every save increments `version`, snapshots to `contract_versions`
- Approval gate: PDF export blocked until `approved=1`
- Sent to client: write-once except for Admin; auto-sets ACTION → Contract Sent
- Rate limited: 5/hour per user

### Clause Template Management (`/admin/clause-templates`)
- Admin only; 15 templates with `{{PLACEHOLDER}}` syntax
- Each update archives previous version (`active=0`), creates new active version
- Templates loaded at LLM call time (not hardcoded)

### Sales Activity & Expense Tracking (`/leads/<id>/activities/`)
- Access: admin (any lead) or sales rep (assigned leads only) — `_can_access()` in `activities/routes.py`
- **Entry fields:** date, category (9 top-level), subcategory (AJAX), activity type, outcome, destination, purpose, amount or miles, payment method, reimbursable, attendees (conditional), receipt upload, notes, next action
- **Mileage:** subcategory `is_mileage=1` hides Amount, shows Miles Driven; amount = miles × IRS rate; rate stored per-entry
- **Attendees:** shown when category/subcategory `requires_attendees=1` (Meals & Entertainment, Client Gifts)
- **Receipt:** required reminder for entries >$25; JPG/PNG/PDF up to 5 MB; stored in `uploads/receipts/{lead_id}/`; served via authenticated route
- **Status workflow:** Draft → Submitted → Approved → Reimbursed (or Rejected → resubmit once)
- Draft: rep edits all fields. Submitted: rep edits notes + receipt only. Approved/Reimbursed: admin-only with mandatory correction note
- Lead Detail page shows summary bar (total entries, total spend, pending, reimbursable) + last 5 entries
- Full paginated log at `/leads/<id>/activities` (sortable by date/amount/activity/outcome/status/destination)

### Admin Expense Queue (`/admin/expenses`)
- Filterable by status, rep, date range, lead ID
- Inline approve (✓), reject (requires review note, modal), reimburse (💰) actions
- IRS mileage rate editor (updates `system_config` table; affects new entries only)
- CSV export with 20 columns via `/admin/expenses/export`
- Pending Submitted count shown as badge on nav link and in `pending_expense_count` context variable

### AI Agent Lead Research (`/leads/research` — Add Lead page)
- Research bar card at top of Add Lead form: company name + optional city/state → Research button
- Button is disabled (with tooltip) if `SERPER_API_KEY` is not set in environment
- Calls `POST /leads/research` (rate-limited 20/hour; daily token budget from `system_config` key `agent_daily_token_budget`, default 2000000)
- Backend: `app/agent/research_agent.py` — Claude `claude-sonnet-4-6` agentic tool-use loop
  - Tools: `web_search` (Serper API), `fetch_url` (BeautifulSoup), `calculate_roi` (loads params from DB)
  - **MAX_ITERATIONS=6, TIMEOUT_SECS=25** — tuned for GoDaddy shared hosting (~30s request kill limit)
  - System prompt enforces **3 tool call max** then immediate JSON output (prevents timeout)
  - Writes audit record to `agent_research_log` table on every run
- Returns JSON with `fields` (10 form-fill keys), `extended` (8 extra intel items), `meta`, `run_id`
- Frontend (`agent_autofill.js`): populates form fields, renders confidence badges (High/Medium/Low)
- Confidence badge styles in `app.css`: `.confidence-high/medium/low/not-found`, `.agent-low-confidence`
- `agent_research_run_id` hidden field links the saved lead to the research run for audit
- Research Summary panel shows: contact title, employee count, locations, kWh savings, payback, website, LinkedIn, news
- Clear / Re-Research buttons on the form
- All research activity traced to `logs/research.log` (INFO level, always on in prod)
- Admin audit log at `/admin/research-log` (paginated, filterable by company/user/date)
- Detail view at `/admin/research-log/<run_id>` shows raw JSON response

### One-time Setup Route (`/setup`)
- Available only when admin user has invalid/empty Werkzeug hash
- Self-disables once valid password is stored

## ACTION_VALUES (pipeline stages in order)
New Lead → Call Scheduled → Contacted → Quote Requested → Follow-Up → Proposal Sent → Negotiation → Contract → Contract Sent → Closed Won / Closed Lost / On Hold

## Known Deployment Notes (GoDaddy cPanel)
- App lives at `https://colloquyai.com/comfortlighting/` — Passenger strips the `/comfortlighting/` prefix before passing to Flask
- All JS fetch() URLs must use `url_for(_external=True)` to generate absolute URLs; relative paths like `/leads/research` resolve to the server root and miss the app
- Static files: `.htaccess` rewrites `^static/(.*)$` → `app/static/$1` so Apache serves them directly (bypasses Passenger)
- **`app/static/.htaccess`** must exist with `Require all granted` — Apache checks for this file in every directory it serves from; without it, static assets (JS/CSS) return 403 and the page breaks silently
- After deploying zip, set directory permissions to **755** and file permissions to **644** on `app/static/` and all subdirectories/files via cPanel File Manager
- MySQL pool: `pool_pre_ping=True`, `pool_recycle=280` to handle cold-start stale connections
- After deploy, restart the app in cPanel Python App Manager
- `pip install anthropic reportlab Flask-Limiter requests beautifulsoup4 pymysql` required in cPanel virtual environment
- `uploads/` directory must be writable by the Passenger process — created automatically on first receipt save via `os.makedirs(exist_ok=True)`
- Agent research runs ~10–15s on GoDaddy; if "Daily token budget exceeded" appears, update `system_config` via phpMyAdmin
