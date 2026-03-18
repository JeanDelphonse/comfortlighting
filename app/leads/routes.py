import csv
import io
import re
import sys
import uuid
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, session, Response, abort, jsonify,
                   current_app)
from flask_login import login_required, current_user

from ..models import db, Lead, User, AgentResearchLog, LeadStageHistory
from ..constants import ACTION_VALUES, PROGRESS_VALUES, ACTION_BADGE_CLASS, LEADS_PER_PAGE
from ..decorators import admin_required
from ..extensions import limiter


leads_bp = Blueprint('leads', __name__)

# Pipeline stages in order (On Hold is excluded — handled separately)
PIPELINE_STAGES = [
    'New Lead', 'Call Scheduled', 'Contacted', 'Quote Requested',
    'Proposal Sent', 'Follow-Up', 'Negotiation', 'Contract',
    'Contract Sent', 'Closed Won', 'Closed Lost',
]
STAGE_IDX = {s: i for i, s in enumerate(PIPELINE_STAGES)}


def _build_diagram_context(lead, stage_history):
    """Pre-process stage history into arrow data for the pipeline diagram template."""
    is_on_hold    = lead.action == 'On Hold'
    display_stage = (lead.previous_progress if is_on_hold and lead.previous_progress
                     else lead.action)
    display_idx   = STAGE_IDX.get(display_stage, -1)

    forward_arrows = []
    retreat_arrows = []
    stage_tooltips = {}   # stage_name -> {reached, days_spent}

    for h in sorted(stage_history, key=lambda h: h.changed_at):
        # Tooltip tracking: record when each stage was entered
        if h.to_stage and h.to_stage in STAGE_IDX:
            stage_tooltips[h.to_stage] = {'reached': h.changed_at, 'days_spent': None}
        if h.from_stage and h.from_stage in STAGE_IDX and h.days_in_stage is not None:
            if h.from_stage in stage_tooltips:
                stage_tooltips[h.from_stage]['days_spent'] = float(h.days_in_stage)

        if not h.from_stage:
            continue
        fi = STAGE_IDX.get(h.from_stage, -1)
        ti = STAGE_IDX.get(h.to_stage, -1)
        if fi < 0 or ti < 0:
            continue  # skip On Hold transitions

        if ti > fi:
            forward_arrows.append({
                'from_idx': fi, 'to_idx': ti,
                'from_stage': h.from_stage, 'to_stage': h.to_stage,
                'changed_at': h.changed_at, 'is_active': False,
            })
        elif ti < fi:
            retreat_arrows.append({
                'from_idx': fi, 'to_idx': ti,
                'from_stage': h.from_stage, 'to_stage': h.to_stage,
                'changed_at': h.changed_at,
            })

    if forward_arrows:
        forward_arrows[-1]['is_active'] = True

    days_in_stage = 0
    if lead.stage_changed_at:
        days_in_stage = (datetime.utcnow() - lead.stage_changed_at).days

    return dict(
        forward_arrows=forward_arrows,
        retreat_arrows=retreat_arrows,
        display_idx=display_idx,
        display_stage=display_stage,
        is_on_hold=is_on_hold,
        days_in_stage=days_in_stage,
        pipeline_stages=PIPELINE_STAGES,
        stage_tooltips=stage_tooltips,
    )


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

    uid_raw = form_data.get('assigned_user_id', '').strip()
    if uid_raw:
        try:
            uid = int(uid_raw)
            active_user = User.query.filter_by(id=uid, active=True).first()
            if not active_user:
                errors['assigned_user_id'] = 'Selected user is not valid.'
                data['assigned_user_id'] = None
            else:
                data['assigned_user_id'] = uid
        except ValueError:
            errors['assigned_user_id'] = 'Selected user is not valid.'
            data['assigned_user_id'] = None
    else:
        data['assigned_user_id'] = None

    return data, errors


# ── Context helper ────────────────────────────────────────────────────────────

def lead_context() -> dict:
    active_users = User.query.filter_by(active=True).order_by(User.username.asc()).all()
    return dict(
        action_values=ACTION_VALUES,
        progress_values=PROGRESS_VALUES,
        action_badge_class=ACTION_BADGE_CLASS,
        active_users=active_users,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@leads_bp.route('/')
@login_required
def index():
    if request.args.get('export') == 'csv':
        return _export_csv()

    # WIP = all leads whose progress is 'In Progress'
    wip_leads = Lead.query.filter(Lead.progress == 'In Progress').order_by(Lead.wip_since.desc(), Lead.updated_at.desc()).all()
    wip_count = len(wip_leads)

    q            = request.args.get('q', '').strip()
    f_action     = request.args.get('action', '').strip()
    f_progress   = request.args.get('progress', '').strip()
    f_assigned   = request.args.get('assigned_user', '').strip()
    date_from    = request.args.get('date_from', '').strip()
    date_to      = request.args.get('date_to', '').strip()
    sort         = request.args.get('sort', 'created_at')
    direction    = request.args.get('dir', 'DESC').upper()
    page         = max(1, int(request.args.get('page', 1) or 1))

    allowed_sorts = {'id', 'company_name', 'action', 'contact', 'progress',
                     'expected', 'potential', 'created_at', 'updated_at',
                     'assigned_user'}
    if sort not in allowed_sorts:
        sort = 'created_at'
    if direction not in ('ASC', 'DESC'):
        direction = 'DESC'

    # Exclude 'In Progress' leads — they appear in the WIP section above
    query = Lead.query.filter(
        db.or_(Lead.progress != 'In Progress', Lead.progress.is_(None))
    )

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
    if f_assigned == 'unassigned':
        query = query.filter(Lead.assigned_user_id.is_(None))
    elif f_assigned and f_assigned.isdigit():
        query = query.filter(Lead.assigned_user_id == int(f_assigned))
    if date_from:
        query = query.filter(Lead.expected >= date_from)
    if date_to:
        query = query.filter(Lead.expected <= date_to)

    if sort == 'assigned_user':
        query = query.outerjoin(User, Lead.assigned_user_id == User.id)
        sort_expr = User.username.asc() if direction == 'ASC' else User.username.desc()
    else:
        sort_col = getattr(Lead, sort)
        sort_expr = sort_col.desc() if direction == 'DESC' else sort_col.asc()
    query = query.order_by(sort_expr)

    pagination = query.paginate(page=page, per_page=LEADS_PER_PAGE, error_out=False)

    return render_template(
        'leads/index.html',
        leads=pagination.items,
        pagination=pagination,
        wip_leads=wip_leads,
        wip_count=wip_count,
        now=datetime.utcnow(),
        q=q, f_action=f_action, f_progress=f_progress,
        f_assigned=f_assigned,
        date_from=date_from, date_to=date_to,
        sort=sort, direction=direction,
        **lead_context(),
    )


def _export_csv() -> Response:
    q          = request.args.get('q', '').strip()
    f_action   = request.args.get('action', '').strip()
    f_progress = request.args.get('progress', '').strip()
    f_assigned = request.args.get('assigned_user', '').strip()
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
    if f_assigned == 'unassigned':
        query = query.filter(Lead.assigned_user_id.is_(None))
    elif f_assigned and f_assigned.isdigit():
        query = query.filter(Lead.assigned_user_id == int(f_assigned))
    if date_from:  query = query.filter(Lead.expected >= date_from)
    if date_to:    query = query.filter(Lead.expected <= date_to)

    leads = query.order_by(Lead.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Created', 'Updated', 'Company Name', 'Action', 'Contact',
        'Address', 'Phone', 'Email', 'Notes', 'Assigned To', 'Sq Ft', 'Targets',
        'Potential', 'Progress', 'Expected', 'ROI', 'Annual Sales / Locations',
    ])
    for l in leads:
        writer.writerow([
            l.id, l.created_at, l.updated_at, l.company_name, l.action,
            l.contact, l.address, l.number, l.email, l.notes,
            l.assigned_user.username if l.assigned_user else '',
            l.sq_ft, l.targets, l.potential, l.progress, l.expected, l.roi,
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

            # Link to agent research run if form was populated by the agent
            agent_run_id = form_data.get('agent_research_run_id', '').strip() or None

            lead = Lead(
                company_name          = data['company_name'],
                action                = data['action'],
                contact               = data['contact'],
                address               = data['address'],
                number                = data['number'],
                email                 = data['email'],
                notes                 = notes,
                assigned_user_id      = data['assigned_user_id'],
                sq_ft                 = data['sq_ft'],
                targets               = data['targets'],
                potential             = data['potential'],
                progress              = data['progress'],
                expected              = data['expected'],
                roi                   = data['roi'],
                annual_sales_locations= data['annual_sales_locations'],
                agent_research_run_id = agent_run_id,
            )
            db.session.add(lead)
            db.session.flush()  # get lead.id

            # Back-fill lead_id on the research log row
            if agent_run_id:
                log = AgentResearchLog.query.filter_by(run_id=agent_run_id).first()
                if log:
                    log.lead_id = lead.id

            db.session.commit()
            session.pop('lead_draft', None)
            flash('Lead created successfully.', 'success')
            return redirect(url_for('leads.view', lead_id=lead.id))

    import os
    return render_template(
        'leads/add.html',
        form_data=form_data,
        errors=errors,
        research_enabled=bool(os.getenv('SERPER_API_KEY', '').strip()),
        **lead_context(),
    )


@leads_bp.route('/leads/<int:lead_id>')
@login_required
def view(lead_id: int):
    lead = db.get_or_404(Lead, lead_id)
    from ..models import Proposal, Contract, LeadActivity

    proposal = Proposal.query.filter_by(lead_id=lead_id).first()
    contract = Contract.query.filter_by(lead_id=lead_id).first()

    recent_activities = (LeadActivity.query
                         .filter_by(lead_id=lead_id)
                         .order_by(LeadActivity.activity_date.desc())
                         .limit(5).all())
    total_entries = LeadActivity.query.filter_by(lead_id=lead_id).count()
    total_spend   = (db.session.query(db.func.sum(LeadActivity.amount))
                     .filter_by(lead_id=lead_id).scalar() or 0)
    pending_count = LeadActivity.query.filter_by(lead_id=lead_id, status='Submitted').count()
    reimb_amt     = (db.session.query(db.func.sum(LeadActivity.amount))
                     .filter(LeadActivity.lead_id == lead_id,
                             LeadActivity.reimbursable == True,
                             LeadActivity.status.in_(['Submitted', 'Approved']))
                     .scalar() or 0)
    activity_stats = {
        'total_entries':    total_entries,
        'total_spend':      float(total_spend),
        'pending_count':    pending_count,
        'reimbursable_amt': float(reimb_amt),
    }

    stage_history = lead.stage_history.order_by(LeadStageHistory.changed_at.asc()).all()
    diagram_ctx   = _build_diagram_context(lead, stage_history)

    return render_template(
        'leads/view.html',
        lead=lead,
        proposal=proposal,
        contract=contract,
        recent_activities=recent_activities,
        activity_stats=activity_stats,
        stage_history=stage_history,
        now=datetime.utcnow(),
        **diagram_ctx,
        **lead_context(),
    )


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
            lead.assigned_user_id       = data['assigned_user_id']
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
            'assigned_user_id':       str(lead.assigned_user_id) if lead.assigned_user_id is not None else '',
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


@leads_bp.route('/leads/<int:lead_id>/wip', methods=['PATCH'])
@login_required
def toggle_wip(lead_id: int):
    """Toggle WIP status for a lead via drag-and-drop. Sets progress='In Progress' to add; clears to remove."""
    lead = db.get_or_404(Lead, lead_id)
    data = request.get_json()
    if not data or 'wip' not in data:
        return jsonify({'success': False, 'error': 'Missing wip field'}), 400

    new_wip = bool(data['wip'])
    currently_wip = (lead.progress == 'In Progress')

    # No change
    if currently_wip == new_wip:
        return jsonify({
            'success': True,
            'wip': currently_wip,
            'wip_since': lead.wip_since.isoformat() if lead.wip_since else None,
            'progress': lead.progress,
        })

    if new_wip:
        lead.progress = 'In Progress'
        lead.wip = 1
        lead.wip_since = datetime.utcnow()
    else:
        lead.progress = None
        lead.wip = 0
        lead.wip_since = None

    db.session.commit()

    return jsonify({
        'success': True,
        'wip': new_wip,
        'wip_since': lead.wip_since.isoformat() if lead.wip_since else None,
        'progress': lead.progress,
    })


@leads_bp.route('/leads/<int:lead_id>/progress', methods=['PATCH'])
@login_required
def change_progress(lead_id: int):
    """Change the pipeline stage for a lead via the workflow diagram."""
    lead = db.get_or_404(Lead, lead_id)
    data = request.get_json()
    if not data or 'progress' not in data:
        return jsonify({'success': False, 'error': 'Missing progress field'}), 400

    new_progress = data['progress'].strip()
    reason       = (data.get('reason') or '').strip() or None

    # Only the 11 main pipeline stages are accepted here; On Hold uses /hold
    if new_progress not in PIPELINE_STAGES:
        return jsonify({'success': False, 'error': 'Invalid progress value'}), 400

    # Terminal stage override requires admin + reason
    terminal_stages  = ('Closed Won', 'Closed Lost')
    is_terminal      = lead.action in terminal_stages
    becoming_terminal = new_progress in terminal_stages

    if is_terminal and not becoming_terminal and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Only admins can re-open closed leads'}), 403
    if is_terminal and not becoming_terminal and current_user.is_admin and not reason:
        return jsonify({'success': False, 'error': 'Reason required for terminal stage override'}), 400

    # Calculate days spent in the current stage before moving
    days_in_from = 0.0
    if lead.stage_changed_at:
        days_in_from = round(
            (datetime.utcnow() - lead.stage_changed_at).total_seconds() / 86400, 1
        )

    old_action = lead.action

    history = LeadStageHistory(
        lead_id=lead.id,
        from_stage=old_action,
        to_stage=new_progress,
        changed_by_id=current_user.id,
        reason=reason,
        days_in_stage=days_in_from,
    )
    db.session.add(history)

    lead.action          = new_progress
    lead.progress        = new_progress
    lead.stage_changed_at = datetime.utcnow()
    lead.previous_progress = None  # clear any On Hold bookmark

    # Sync WIP board: clear wip flag when leaving In Progress via diagram
    if lead.wip:
        lead.wip       = 0
        lead.wip_since = None

    db.session.commit()
    current_app.logger.info('Lead %s stage changed: %s -> %s', lead.id, old_action, new_progress)

    stage_history = lead.stage_history.order_by(LeadStageHistory.changed_at.asc()).all()
    diagram_ctx   = _build_diagram_context(lead, stage_history)
    diagram_html  = render_template(
        'leads/_progress_diagram.html',
        lead=lead, stage_history=stage_history, animate_active=True,
        **diagram_ctx,
    )
    return jsonify({'success': True, 'diagram_html': diagram_html,
                    'action': lead.action, 'progress': lead.progress})


@leads_bp.route('/leads/<int:lead_id>/hold', methods=['POST'])
@login_required
def hold(lead_id: int):
    """Place a lead On Hold, preserving current stage for later restore."""
    lead = db.get_or_404(Lead, lead_id)
    if lead.action == 'On Hold':
        return jsonify({'success': True, 'message': 'Already on hold'})

    days_in_from = 0.0
    if lead.stage_changed_at:
        days_in_from = round(
            (datetime.utcnow() - lead.stage_changed_at).total_seconds() / 86400, 1
        )

    reason = ((request.get_json(silent=True) or {}).get('reason') or '').strip() or None
    db.session.add(LeadStageHistory(
        lead_id=lead.id, from_stage=lead.action, to_stage='On Hold',
        changed_by_id=current_user.id, reason=reason, days_in_stage=days_in_from,
    ))

    lead.previous_progress = lead.action
    lead.action            = 'On Hold'
    lead.progress          = 'On Hold'
    lead.wip               = 0
    lead.wip_since         = None
    lead.stage_changed_at  = datetime.utcnow()
    db.session.commit()

    stage_history = lead.stage_history.order_by(LeadStageHistory.changed_at.asc()).all()
    diagram_ctx   = _build_diagram_context(lead, stage_history)
    diagram_html  = render_template(
        'leads/_progress_diagram.html',
        lead=lead, stage_history=stage_history, animate_active=False,
        **diagram_ctx,
    )
    return jsonify({'success': True, 'diagram_html': diagram_html})


@leads_bp.route('/leads/<int:lead_id>/unhold', methods=['POST'])
@login_required
def unhold(lead_id: int):
    """Remove On Hold status, restoring the previous stage."""
    lead = db.get_or_404(Lead, lead_id)
    if lead.action != 'On Hold':
        return jsonify({'success': True, 'message': 'Not on hold'})

    restore_stage = lead.previous_progress or 'New Lead'

    days_in_from = 0.0
    if lead.stage_changed_at:
        days_in_from = round(
            (datetime.utcnow() - lead.stage_changed_at).total_seconds() / 86400, 1
        )

    db.session.add(LeadStageHistory(
        lead_id=lead.id, from_stage='On Hold', to_stage=restore_stage,
        changed_by_id=current_user.id, days_in_stage=days_in_from,
    ))

    lead.action            = restore_stage
    lead.progress          = restore_stage
    lead.previous_progress = None
    lead.stage_changed_at  = datetime.utcnow()
    db.session.commit()

    stage_history = lead.stage_history.order_by(LeadStageHistory.changed_at.asc()).all()
    diagram_ctx   = _build_diagram_context(lead, stage_history)
    diagram_html  = render_template(
        'leads/_progress_diagram.html',
        lead=lead, stage_history=stage_history, animate_active=True,
        **diagram_ctx,
    )
    return jsonify({'success': True, 'diagram_html': diagram_html, 'action': lead.action})


@leads_bp.route('/leads/<int:lead_id>/stage-history')
@login_required
def stage_history_api(lead_id: int):
    """Return full stage history JSON for a lead."""
    lead = db.get_or_404(Lead, lead_id)
    history = lead.stage_history.order_by(LeadStageHistory.changed_at.asc()).all()
    return jsonify([{
        'id':           h.id,
        'from_stage':   h.from_stage,
        'to_stage':     h.to_stage,
        'changed_at':   h.changed_at.isoformat(),
        'changed_by':   h.changed_by.username if h.changed_by else None,
        'reason':       h.reason,
        'days_in_stage': float(h.days_in_stage) if h.days_in_stage is not None else None,
    } for h in history])


# ── AI Agent: company research ────────────────────────────────────────────────

@leads_bp.route('/leads/research', methods=['POST'])
@login_required
@limiter.limit('20 per hour')
def research_lead():
    """Run the AI research agent for a company name and return pre-fill data."""
    import os
    print('[research_lead] route hit', file=sys.stderr, flush=True)

    serper_key    = os.getenv('SERPER_API_KEY', '').strip()
    anthropic_key = current_app.config.get('ANTHROPIC_API_KEY', '').strip()
    print(f'[research_lead] SERPER_API_KEY present={bool(serper_key)} ANTHROPIC_API_KEY present={bool(anthropic_key)} len={len(anthropic_key)}',
          file=sys.stderr, flush=True)
    current_app.logger.info('research_lead: SERPER_API_KEY present=%s, ANTHROPIC_API_KEY present=%s',
                            bool(serper_key), bool(anthropic_key))

    if not serper_key:
        print('[research_lead] aborting — SERPER_API_KEY not set', file=sys.stderr, flush=True)
        current_app.logger.info('research_lead: aborting — SERPER_API_KEY not set')
        return jsonify({'error': 'Research is not available: SERPER_API_KEY is not configured.'}), 503

    data         = request.get_json(silent=True) or {}
    company_name = (data.get('company_name') or '').strip()
    location_hint= (data.get('location_hint') or '').strip()
    print(f'[research_lead] company_name={company_name!r} location_hint={location_hint!r}',
          file=sys.stderr, flush=True)
    current_app.logger.info('research_lead: company_name=%r location_hint=%r', company_name, location_hint)

    if not company_name:
        return jsonify({'error': 'Company name is required.'}), 400

    run_id = str(uuid.uuid4())
    print(f'[research_lead] starting run_id={run_id}', file=sys.stderr, flush=True)
    current_app.logger.info('research_lead: starting run_id=%s', run_id)

    try:
        from ..agent.research_agent import run_research_agent
        result = run_research_agent(
            company_name  = company_name,
            location_hint = location_hint,
            run_id        = run_id,
            user_id       = current_user.id,
        )
        populated = sum(1 for f in result.to_form_dict().values() if f.get('value'))
        print(f'[research_lead] completed run_id={run_id} status={result.status} fields={populated} tokens={result.tokens_used} duration={result.run_duration_sec}s',
              file=sys.stderr, flush=True)
        current_app.logger.info('research_lead: completed run_id=%s status=%s fields_populated=%s tokens=%s duration=%ss',
                                run_id, result.status, populated, result.tokens_used, result.run_duration_sec)
    except Exception as exc:
        print(f'[research_lead] EXCEPTION run_id={run_id}: {exc}', file=sys.stderr, flush=True)
        current_app.logger.error('research_lead failed [%s]: %s', run_id, exc, exc_info=True)
        return jsonify({'error': 'Research failed. Please try again.'}), 500

    return jsonify({
        'run_id':   run_id,
        'status':   result.status,
        'fields':   result.to_form_dict(),
        'extended': result.to_extended_dict(),
        'meta':     result.to_meta_dict(),
    }), 200
