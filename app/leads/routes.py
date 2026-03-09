import csv
import io
import re
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, session, Response, abort)
from flask_login import login_required, current_user

from ..models import db, Lead
from ..constants import ACTION_VALUES, PROGRESS_VALUES, ACTION_BADGE_CLASS, LEADS_PER_PAGE

leads_bp = Blueprint('leads', __name__)


# ── Decorators ────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('leads.index'))
        return f(*args, **kwargs)
    return decorated


# ── Validation ────────────────────────────────────────────────────────────────

def validate_lead(form_data: dict) -> tuple[dict, dict]:
    errors: dict = {}
    data: dict = {}

    for field in ('company_name', 'contact', 'number'):
        val = form_data.get(field, '').strip()
        if not val:
            errors[field] = 'This field is required.'
        data[field] = val

    action = form_data.get('action', '').strip()
    if not action:
        errors['action'] = 'Please select an action.'
    elif action not in ACTION_VALUES:
        errors['action'] = 'Invalid action value.'
    data['action'] = action

    email = form_data.get('email', '').strip()
    if not email:
        errors['email'] = 'Email is required.'
    elif not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        errors['email'] = 'Please enter a valid email address.'
    data['email'] = email

    progress = form_data.get('progress', '').strip()
    if progress and progress not in PROGRESS_VALUES:
        errors['progress'] = 'Invalid progress value.'
    data['progress'] = progress or None

    for field in ('address', 'targets', 'annual_sales_locations'):
        val = form_data.get(field, '').strip()
        data[field] = val or None

    sq_ft_raw = form_data.get('sq_ft', '').strip()
    if sq_ft_raw:
        try:
            data['sq_ft'] = int(sq_ft_raw)
            if data['sq_ft'] < 0:
                raise ValueError
        except ValueError:
            errors['sq_ft'] = 'Must be a whole number.'
            data['sq_ft'] = None
    else:
        data['sq_ft'] = None

    for field in ('potential', 'roi'):
        raw = form_data.get(field, '').strip()
        if raw:
            try:
                val = float(raw)
                if val < 0:
                    raise ValueError
                data[field] = val
            except ValueError:
                errors[field] = 'Must be a positive number.'
                data[field] = None
        else:
            data[field] = None

    expected_raw = form_data.get('expected', '').strip()
    if expected_raw:
        try:
            data['expected'] = datetime.strptime(expected_raw, '%Y-%m-%d').date()
        except ValueError:
            errors['expected'] = 'Invalid date format.'
            data['expected'] = None
    else:
        data['expected'] = None

    return data, errors


# ── Context helper ────────────────────────────────────────────────────────────

def lead_context() -> dict:
    return dict(
        action_values=ACTION_VALUES,
        progress_values=PROGRESS_VALUES,
        action_badge_class=ACTION_BADGE_CLASS,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@leads_bp.route('/')
@login_required
def index():
    if request.args.get('export') == 'csv':
        return _export_csv()

    q          = request.args.get('q', '').strip()
    f_action   = request.args.get('action', '').strip()
    f_progress = request.args.get('progress', '').strip()
    date_from  = request.args.get('date_from', '').strip()
    date_to    = request.args.get('date_to', '').strip()
    sort       = request.args.get('sort', 'created_at')
    direction  = request.args.get('dir', 'DESC').upper()
    page       = max(1, int(request.args.get('page', 1) or 1))

    allowed_sorts = {'id', 'company_name', 'action', 'contact', 'progress',
                     'expected', 'potential', 'created_at', 'updated_at'}
    if sort not in allowed_sorts:
        sort = 'created_at'
    if direction not in ('ASC', 'DESC'):
        direction = 'DESC'

    query = Lead.query

    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Lead.company_name.ilike(like),
                Lead.contact.ilike(like),
                Lead.email.ilike(like),
            )
        )
    if f_action:
        query = query.filter(Lead.action == f_action)
    if f_progress:
        query = query.filter(Lead.progress == f_progress)
    if date_from:
        query = query.filter(Lead.expected >= date_from)
    if date_to:
        query = query.filter(Lead.expected <= date_to)

    sort_col = getattr(Lead, sort)
    query = query.order_by(sort_col.desc() if direction == 'DESC' else sort_col.asc())

    pagination = query.paginate(page=page, per_page=LEADS_PER_PAGE, error_out=False)

    return render_template(
        'leads/index.html',
        leads=pagination.items,
        pagination=pagination,
        q=q, f_action=f_action, f_progress=f_progress,
        date_from=date_from, date_to=date_to,
        sort=sort, direction=direction,
        **lead_context(),
    )


def _export_csv() -> Response:
    q          = request.args.get('q', '').strip()
    f_action   = request.args.get('action', '').strip()
    f_progress = request.args.get('progress', '').strip()
    date_from  = request.args.get('date_from', '').strip()
    date_to    = request.args.get('date_to', '').strip()

    query = Lead.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(Lead.company_name.ilike(like),
                   Lead.contact.ilike(like),
                   Lead.email.ilike(like))
        )
    if f_action:   query = query.filter(Lead.action == f_action)
    if f_progress: query = query.filter(Lead.progress == f_progress)
    if date_from:  query = query.filter(Lead.expected >= date_from)
    if date_to:    query = query.filter(Lead.expected <= date_to)

    leads = query.order_by(Lead.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Created', 'Updated', 'Company Name', 'Action', 'Contact',
        'Address', 'Phone', 'Email', 'Notes', 'Sq Ft', 'Targets',
        'Potential', 'Progress', 'Expected', 'ROI', 'Annual Sales / Locations',
    ])
    for l in leads:
        writer.writerow([
            l.id, l.created_at, l.updated_at, l.company_name, l.action,
            l.contact, l.address, l.number, l.email, l.notes, l.sq_ft,
            l.targets, l.potential, l.progress, l.expected, l.roi,
            l.annual_sales_locations,
        ])

    filename = f'comfortlighting_leads_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@leads_bp.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add():
    errors: dict = {}
    form_data: dict = session.pop('lead_draft', {})

    if request.method == 'POST':
        if request.form.get('action_type') == 'cancel':
            session.pop('lead_draft', None)
            return redirect(url_for('leads.index'))

        form_data = request.form.to_dict()
        session['lead_draft'] = form_data

        data, errors = validate_lead(form_data)

        if not errors:
            new_note = form_data.get('new_note', '').strip()
            notes = None
            if new_note:
                notes = f'[{datetime.now().strftime("%Y-%m-%d %H:%M")} \u2013 {current_user.username}] {new_note}'

            lead = Lead(
                company_name=data['company_name'],
                action=data['action'],
                contact=data['contact'],
                address=data['address'],
                number=data['number'],
                email=data['email'],
                notes=notes,
                sq_ft=data['sq_ft'],
                targets=data['targets'],
                potential=data['potential'],
                progress=data['progress'],
                expected=data['expected'],
                roi=data['roi'],
                annual_sales_locations=data['annual_sales_locations'],
            )
            db.session.add(lead)
            db.session.commit()
            session.pop('lead_draft', None)
            flash('Lead created successfully.', 'success')
            return redirect(url_for('leads.view', lead_id=lead.id))

    return render_template(
        'leads/add.html',
        form_data=form_data,
        errors=errors,
        **lead_context(),
    )


@leads_bp.route('/leads/<int:lead_id>')
@login_required
def view(lead_id: int):
    lead = db.get_or_404(Lead, lead_id)
    return render_template('leads/view.html', lead=lead, **lead_context())


@leads_bp.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(lead_id: int):
    lead = db.get_or_404(Lead, lead_id)
    errors: dict = {}
    form_data: dict = {}

    if request.method == 'POST':
        if request.form.get('action_type') == 'cancel':
            return redirect(url_for('leads.view', lead_id=lead_id))

        form_data = request.form.to_dict()
        data, errors = validate_lead(form_data)

        if not errors:
            new_note = form_data.get('new_note', '').strip()
            existing = lead.notes or ''
            if new_note:
                entry = f'[{datetime.now().strftime("%Y-%m-%d %H:%M")} \u2013 {current_user.username}] {new_note}'
                lead.notes = entry + ('\n' + existing if existing else '')
            # else: preserve notes as-is

            lead.company_name           = data['company_name']
            lead.action                 = data['action']
            lead.contact                = data['contact']
            lead.address                = data['address']
            lead.number                 = data['number']
            lead.email                  = data['email']
            lead.sq_ft                  = data['sq_ft']
            lead.targets                = data['targets']
            lead.potential              = data['potential']
            lead.progress               = data['progress']
            lead.expected               = data['expected']
            lead.roi                    = data['roi']
            lead.annual_sales_locations = data['annual_sales_locations']

            db.session.commit()
            flash('Lead updated successfully.', 'success')
            return redirect(url_for('leads.view', lead_id=lead_id))

    # Populate form_data from lead on GET, or from POST on validation error
    if not form_data:
        form_data = {
            'company_name':           lead.company_name,
            'action':                 lead.action,
            'contact':                lead.contact,
            'address':                lead.address or '',
            'number':                 lead.number,
            'email':                  lead.email,
            'sq_ft':                  str(lead.sq_ft) if lead.sq_ft is not None else '',
            'targets':                lead.targets or '',
            'potential':              str(lead.potential) if lead.potential is not None else '',
            'progress':               lead.progress or '',
            'expected':               lead.expected.isoformat() if lead.expected else '',
            'roi':                    str(lead.roi) if lead.roi is not None else '',
            'annual_sales_locations': lead.annual_sales_locations or '',
        }

    return render_template(
        'leads/edit.html',
        lead=lead,
        form_data=form_data,
        errors=errors,
        **lead_context(),
    )


@leads_bp.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(lead_id: int):
    lead = db.get_or_404(Lead, lead_id)
    name = lead.company_name
    db.session.delete(lead)
    db.session.commit()
    flash(f'Lead "{name}" has been deleted.', 'success')
    return redirect(url_for('leads.index'))
