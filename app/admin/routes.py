import csv
import io
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from ..models import db, User, LeadActivity, Lead, SystemConfig, AgentResearchLog
from ..decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users():
    errors: dict = {}

    if request.method == 'POST':
        action = request.form.get('form_action', '')

        # ── Create user ───────────────────────────────────────────────────────
        if action == 'create':
            username = request.form.get('username', '').strip()
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            role     = request.form.get('role', 'sales')

            if not username:
                errors['username'] = 'Username is required.'
            if not email or '@' not in email:
                errors['email'] = 'Valid email required.'
            if len(password) < 8:
                errors['password'] = 'Password must be at least 8 characters.'
            if role not in ('admin', 'sales', 'legal'):
                errors['role'] = 'Invalid role.'

            if not errors:
                user = User(username=username, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                try:
                    db.session.commit()
                    flash(f'User "{username}" created.', 'success')
                    return redirect(url_for('admin.users'))
                except IntegrityError:
                    db.session.rollback()
                    errors['username'] = 'Username or email already exists.'

        # ── Toggle active ─────────────────────────────────────────────────────
        elif action == 'toggle':
            uid = request.form.get('user_id', '').strip()
            if uid == current_user.id:
                flash('You cannot deactivate your own account.', 'danger')
            else:
                user = db.get_or_404(User, uid)
                user.active = not user.active
                db.session.commit()
                flash('User status updated.', 'success')
            return redirect(url_for('admin.users'))

        # ── Reset password ────────────────────────────────────────────────────
        elif action == 'reset_password':
            uid      = request.form.get('user_id', '').strip()
            new_pass = request.form.get('new_password', '')
            if len(new_pass) < 8:
                flash('New password must be at least 8 characters.', 'danger')
            else:
                user = db.get_or_404(User, uid)
                user.set_password(new_pass)
                db.session.commit()
                flash('Password reset successfully.', 'success')
            return redirect(url_for('admin.users'))

    all_users = User.query.order_by(User.id).all()
    return render_template('admin/users.html', all_users=all_users, errors=errors,
                           form_post=request.form)


# ── Clause Templates ─────────────────────────────────────────────────────────
from ..models import ClauseTemplate

@admin_bp.route('/clause-templates', methods=['GET'])
@login_required
@admin_required
def clause_templates():
    templates = ClauseTemplate.query.order_by(ClauseTemplate.clause_key).all()
    return render_template('admin/clause_templates.html', templates=templates)


# ── Expense Queue ─────────────────────────────────────────────────────────────

@admin_bp.route('/expenses')
@login_required
@admin_required
def expense_queue():
    f_status   = request.args.get('status', 'Submitted').strip()
    f_lead_id  = request.args.get('lead_id', '').strip()
    f_user_id  = request.args.get('user_id', '').strip()
    f_from     = request.args.get('date_from', '').strip()
    f_to       = request.args.get('date_to', '').strip()
    page       = max(1, int(request.args.get('page', 1) or 1))

    valid_statuses = ['Submitted', 'Approved', 'Rejected', 'Reimbursed', 'Draft', '']
    if f_status not in valid_statuses:
        f_status = 'Submitted'

    q = LeadActivity.query.join(Lead, LeadActivity.lead_id == Lead.id)
    if f_status:
        q = q.filter(LeadActivity.status == f_status)
    if f_lead_id:
        q = q.filter(LeadActivity.lead_id == f_lead_id)
    if f_user_id:
        q = q.filter(LeadActivity.user_id == f_user_id)
    if f_from:
        q = q.filter(LeadActivity.activity_date >= f_from)
    if f_to:
        q = q.filter(LeadActivity.activity_date <= f_to)

    q = q.order_by(LeadActivity.submitted_at.desc(),
                   LeadActivity.activity_date.desc())
    pagination = q.paginate(page=page, per_page=25, error_out=False)

    all_users = User.query.order_by(User.username).all()
    mileage_rate = float(SystemConfig.get('irs_mileage_rate', '0.6700'))

    return render_template(
        'admin/expense_queue.html',
        entries=pagination.items,
        pagination=pagination,
        all_users=all_users,
        f_status=f_status, f_lead_id=f_lead_id, f_user_id=f_user_id,
        f_from=f_from, f_to=f_to,
        mileage_rate=mileage_rate,
    )


@admin_bp.route('/expenses/approve', methods=['POST'])
@login_required
@admin_required
def expense_approve():
    entry_id = request.form.get('entry_id', '').strip()
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.status != 'Submitted':
        flash('Only Submitted entries can be approved.', 'warning')
    else:
        entry.status      = 'Approved'
        entry.reviewed_by = current_user.username
        entry.reviewed_at = datetime.utcnow()
        db.session.commit()
        flash('Entry approved.', 'success')
    return redirect(url_for('admin.expense_queue'))


@admin_bp.route('/expenses/reject', methods=['POST'])
@login_required
@admin_required
def expense_reject():
    entry_id     = request.form.get('entry_id', '').strip()
    review_notes = request.form.get('review_notes', '').strip()
    entry = db.get_or_404(LeadActivity, entry_id)
    if not review_notes:
        flash('Review notes are required when rejecting an entry.', 'danger')
        return redirect(url_for('admin.expense_queue'))
    if entry.status != 'Submitted':
        flash('Only Submitted entries can be rejected.', 'warning')
    else:
        entry.status       = 'Rejected'
        entry.reviewed_by  = current_user.username
        entry.reviewed_at  = datetime.utcnow()
        entry.review_notes = review_notes
        db.session.commit()
        flash('Entry rejected.', 'success')
    return redirect(url_for('admin.expense_queue'))


@admin_bp.route('/expenses/reimburse', methods=['POST'])
@login_required
@admin_required
def expense_reimburse():
    entry_id = request.form.get('entry_id', '').strip()
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.status != 'Approved':
        flash('Only Approved entries can be marked as Reimbursed.', 'warning')
    else:
        entry.status        = 'Reimbursed'
        entry.reimbursed_at = datetime.utcnow()
        db.session.commit()
        flash('Entry marked as Reimbursed.', 'success')
    return redirect(url_for('admin.expense_queue'))


@admin_bp.route('/expenses/export')
@login_required
@admin_required
def expense_export():
    f_lead_id = request.args.get('lead_id', '').strip()
    f_from    = request.args.get('date_from', '').strip()
    f_to      = request.args.get('date_to', '').strip()

    q = LeadActivity.query
    if f_lead_id:
        q = q.filter(LeadActivity.lead_id == f_lead_id)
    if f_from:
        q = q.filter(LeadActivity.activity_date >= f_from)
    if f_to:
        q = q.filter(LeadActivity.activity_date <= f_to)
    entries = q.order_by(LeadActivity.activity_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Date', 'Rep Username', 'Lead Company', 'Category', 'Sub-category',
        'Activity Type', 'Amount', 'Miles Driven', 'Mileage Rate',
        'Destination', 'Purpose', 'Attendees', 'Attendee Count',
        'Payment Method', 'Reimbursable', 'Status', 'Receipt',
        'Submitted At', 'Reviewed By', 'Review Notes',
    ])
    for e in entries:
        writer.writerow([
            e.activity_date,
            e.user.username if e.user else '',
            e.lead.company_name if e.lead else '',
            e.category.name if e.category else '',
            e.subcategory.name if e.subcategory else '',
            e.activity_type,
            e.amount or '',
            e.miles_driven or '',
            e.mileage_rate or '',
            e.destination,
            e.purpose,
            e.attendees or '',
            e.attendee_count or '',
            e.payment_method,
            'Yes' if e.reimbursable else 'No',
            e.status,
            'Yes' if e.receipt_attached else 'No',
            e.submitted_at or '',
            e.reviewed_by or '',
            e.review_notes or '',
        ])

    fname = f'expenses_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{fname}"'},
    )


@admin_bp.route('/settings/mileage-rate', methods=['POST'])
@login_required
@admin_required
def update_mileage_rate():
    rate_raw = request.form.get('irs_mileage_rate', '').strip()
    try:
        rate = float(rate_raw)
        if rate <= 0 or rate > 5:
            raise ValueError
    except ValueError:
        flash('Invalid mileage rate. Enter a value between 0.01 and 5.00.', 'danger')
        return redirect(url_for('admin.expense_queue'))

    row = SystemConfig.query.filter_by(config_key='irs_mileage_rate').first()
    if row:
        row.config_value = f'{rate:.4f}'
        row.updated_by   = current_user.username
    else:
        row = SystemConfig(config_key='irs_mileage_rate',
                           config_value=f'{rate:.4f}',
                           updated_by=current_user.username)
        db.session.add(row)
    db.session.commit()
    flash(f'IRS mileage rate updated to ${rate:.4f}/mile.', 'success')
    return redirect(url_for('admin.expense_queue'))


# ── Agent Research Log ─────────────────────────────────────────────────────────

@admin_bp.route('/research-log')
@login_required
@admin_required
def research_log():
    q          = request.args.get('q', '').strip()
    f_user     = request.args.get('user_id', '').strip()
    date_from  = request.args.get('date_from', '').strip()
    date_to    = request.args.get('date_to', '').strip()
    page       = max(1, int(request.args.get('page', 1) or 1))

    query = AgentResearchLog.query
    if q:
        query = query.filter(AgentResearchLog.company_searched.ilike(f'%{q}%'))
    if f_user:
        query = query.filter(AgentResearchLog.user_id == f_user)
    if date_from:
        query = query.filter(AgentResearchLog.created_at >= date_from)
    if date_to:
        query = query.filter(AgentResearchLog.created_at <= date_to + ' 23:59:59')

    query      = query.order_by(AgentResearchLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=25, error_out=False)
    users      = User.query.filter_by(active=True).order_by(User.username).all()

    return render_template(
        'admin/research_log.html',
        entries=pagination.items,
        pagination=pagination,
        users=users,
        q=q, f_user=f_user, date_from=date_from, date_to=date_to,
    )


@admin_bp.route('/research-log/<run_id>')
@login_required
@admin_required
def research_log_detail(run_id: str):
    import json as _json
    entry = AgentResearchLog.query.filter_by(run_id=run_id).first_or_404()
    try:
        raw = _json.loads(entry.raw_json or '{}')
        pretty_json = _json.dumps(raw, indent=2)
    except Exception:
        pretty_json = entry.raw_json or '{}'
    return render_template(
        'admin/research_log.html',
        detail=entry,
        pretty_json=pretty_json,
    )


# ── Clause Templates ─────────────────────────────────────────────────────────

@admin_bp.route('/clause-templates/<clause_key>', methods=['POST'])
@login_required
@admin_required
def update_clause_template(clause_key: str):
    tmpl = ClauseTemplate.query.filter_by(clause_key=clause_key, active=1).first()
    new_text = request.form.get('clause_text', '').strip()
    if not new_text:
        flash('Clause text cannot be empty.', 'danger')
        return redirect(url_for('admin.clause_templates'))
    if tmpl:
        # Archive current
        tmpl.active = 0
        db.session.flush()
        # Create new active version
        new_version = tmpl.version + 1
    else:
        new_version = 1
    new_tmpl = ClauseTemplate(
        clause_key=clause_key,
        clause_text=new_text,
        version=new_version,
        active=1,
        approved_by_legal=current_user.username,
    )
    db.session.add(new_tmpl)
    db.session.commit()
    flash(f'Template "{clause_key}" updated to v{new_version}.', 'success')
    return redirect(url_for('admin.clause_templates'))
