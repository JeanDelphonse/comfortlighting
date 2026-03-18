import csv
import io
import os
from datetime import date, datetime

from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, abort, Response, send_file, jsonify, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from ..models import db, Lead, LeadActivity, ExpenseCategory, SystemConfig
from utils.id_gen import validate_id_param

activities_bp = Blueprint('activities', __name__)

# ── Constants ─────────────────────────────────────────────────────────────────

ACTIVITY_TYPES = [
    'Cold Call', 'Site Visit', 'Demo', 'Proposal Delivery',
    'Contract Review', 'Follow-Up', 'Phone Call', 'Email', 'Other',
]
OUTCOME_VALUES   = ['Positive', 'Neutral', 'Negative', 'No Response']
PAYMENT_METHODS  = ['Corporate Card', 'Personal Card', 'Cash', 'Mileage']
STATUS_BADGE     = {
    'Draft': 'secondary', 'Submitted': 'primary', 'Approved': 'success',
    'Rejected': 'danger', 'Reimbursed': 'info',
}
RECEIPT_ALLOWED  = {'.jpg', '.jpeg', '.png', '.pdf'}
RECEIPT_MAGIC    = {
    b'\xff\xd8\xff': '.jpg',
    b'\x89PNG':      '.png',
    b'%PDF':         '.pdf',
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _can_access(lead: Lead) -> bool:
    """Admins can access any lead's activities; sales reps only their assigned leads."""
    if current_user.is_admin:
        return True
    return lead.assigned_user_id == current_user.id


def _get_mileage_rate() -> float:
    val = SystemConfig.get('irs_mileage_rate', '0.6700')
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.67


def _activity_context() -> dict:
    top_cats = (ExpenseCategory.query
                .filter_by(parent_id=None, active=True)
                .order_by(ExpenseCategory.sort_order)
                .all())
    all_subs = (ExpenseCategory.query
                .filter(ExpenseCategory.parent_id.isnot(None),
                        ExpenseCategory.active == True)
                .order_by(ExpenseCategory.sort_order)
                .all())
    return dict(
        top_categories=top_cats,
        all_subcategories=[s.to_dict() for s in all_subs],
        activity_types=ACTIVITY_TYPES,
        outcome_values=OUTCOME_VALUES,
        payment_methods=PAYMENT_METHODS,
        status_badge=STATUS_BADGE,
        mileage_rate=_get_mileage_rate(),
    )


def _validate_activity(form_data: dict, files=None) -> tuple[dict, dict]:
    errors: dict = {}
    data:   dict = {}

    # Date
    date_raw = form_data.get('activity_date', '').strip()
    if not date_raw:
        errors['activity_date'] = 'Date is required.'
        data['activity_date'] = None
    else:
        try:
            parsed_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
            if parsed_date > date.today():
                errors['activity_date'] = 'Date cannot be in the future.'
            data['activity_date'] = parsed_date
        except ValueError:
            errors['activity_date'] = 'Invalid date.'
            data['activity_date'] = None

    # Subcategory (required) — derive parent category from it
    sub_raw = form_data.get('subcategory_id', '').strip()
    if not sub_raw:
        errors['subcategory_id'] = 'Sub-category is required.'
        data['subcategory_id'] = None
        data['_subcategory'] = None
        data['category_id'] = None
        data['_category'] = None
    else:
        sub = ExpenseCategory.query.filter_by(id=sub_raw, active=True).first()
        if not sub:
            errors['subcategory_id'] = 'Invalid sub-category.'
            data['subcategory_id'] = None
            data['_subcategory'] = None
            data['category_id'] = None
            data['_category'] = None
        else:
            data['subcategory_id'] = sub_raw
            data['_subcategory'] = sub
            # Derive category from subcategory's parent
            if sub.parent_id:
                cat = ExpenseCategory.query.filter_by(id=sub.parent_id, parent_id=None, active=True).first()
                data['category_id'] = sub.parent_id
                data['_category'] = cat
            else:
                # Subcategory is actually a top-level category
                data['category_id'] = sub_raw
                data['_category'] = sub

    # Activity type / outcome
    for field, values, label in [
        ('activity_type', ACTIVITY_TYPES, 'Activity type'),
        ('outcome',       OUTCOME_VALUES, 'Outcome'),
    ]:
        val = form_data.get(field, '').strip()
        if not val:
            errors[field] = f'{label} is required.'
        elif val not in values:
            errors[field] = f'Invalid {label}.'
        data[field] = val

    # Destination / Purpose
    for field, label in [('destination', 'Destination'), ('purpose', 'Purpose')]:
        val = form_data.get(field, '').strip()
        if not val:
            errors[field] = f'{label} is required.'
        data[field] = val or None

    # Payment method
    pm = form_data.get('payment_method', '').strip()
    if not pm:
        errors['payment_method'] = 'Payment method is required.'
    elif pm not in PAYMENT_METHODS:
        errors['payment_method'] = 'Invalid payment method.'
    data['payment_method'] = pm

    # Reimbursable
    data['reimbursable'] = form_data.get('reimbursable') in ('1', 'true', 'on', True)

    # Mileage vs. Amount
    sub_obj = data.get('_subcategory')
    is_mileage = sub_obj.is_mileage if sub_obj else (pm == 'Mileage')

    if is_mileage:
        miles_raw = form_data.get('miles_driven', '').strip()
        if not miles_raw:
            errors['miles_driven'] = 'Miles driven is required for mileage entries.'
            data['miles_driven'] = None
            data['amount'] = None
            data['mileage_rate'] = None
        else:
            try:
                miles = float(miles_raw)
                if miles <= 0:
                    raise ValueError
                rate = _get_mileage_rate()
                data['miles_driven'] = miles
                data['mileage_rate'] = rate
                data['amount'] = round(miles * rate, 2)
                data['payment_method'] = 'Mileage'
            except ValueError:
                errors['miles_driven'] = 'Enter a positive number of miles.'
                data['miles_driven'] = None
                data['amount'] = None
                data['mileage_rate'] = None
    else:
        data['miles_driven'] = None
        data['mileage_rate'] = None
        amt_raw = form_data.get('amount', '').strip()
        if not amt_raw:
            errors['amount'] = 'Amount is required.'
            data['amount'] = None
        else:
            try:
                amt = float(amt_raw)
                if amt < 0.01:
                    raise ValueError
                data['amount'] = round(amt, 2)
            except ValueError:
                errors['amount'] = 'Enter a valid amount (min $0.01).'
                data['amount'] = None

    # Attendees — required when category/subcategory requires_attendees
    cat_obj = data.get('_category')
    needs_attendees = (cat_obj and cat_obj.requires_attendees) or (sub_obj and sub_obj.requires_attendees)
    attendees = form_data.get('attendees', '').strip()
    if needs_attendees and not attendees:
        errors['attendees'] = 'Attendees are required for this category.'
    data['attendees'] = attendees or None

    count_raw = form_data.get('attendee_count', '').strip()
    if count_raw:
        try:
            data['attendee_count'] = max(1, int(count_raw))
        except ValueError:
            data['attendee_count'] = None
    else:
        data['attendee_count'] = None

    # Receipt
    data['receipt_attached'] = form_data.get('receipt_attached') in ('1', 'true', 'on', True)

    # Receipt file validation (returns filename or None; save is deferred)
    data['receipt_filename'] = None  # populated after DB commit if file provided
    if files:
        f = files.get('receipt_file')
        if f and f.filename:
            _, ext = os.path.splitext(f.filename.lower())
            if ext not in RECEIPT_ALLOWED:
                errors['receipt_file'] = 'Only JPG, PNG, and PDF files are allowed.'
            else:
                header = f.read(8)
                f.seek(0)
                valid = any(header[:len(magic)] == magic for magic in RECEIPT_MAGIC)
                if not valid:
                    errors['receipt_file'] = 'Invalid file — does not match declared type.'

    # Optional free-text fields
    data['next_action'] = form_data.get('next_action', '').strip() or None
    data['notes']       = form_data.get('notes', '').strip() or None

    return data, errors


def _save_receipt(file, lead_id, entry_id) -> str | None:
    """Save uploaded receipt file; returns stored filename."""
    if not file or not file.filename:
        return None
    _, ext = os.path.splitext(file.filename.lower())
    ts        = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename  = secure_filename(f'receipt_{entry_id}_{ts}{ext}')
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts', str(lead_id))
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))
    return filename


# ── AJAX: sub-categories ─────────────────────────────────────────────────────

@activities_bp.route('/expenses/subcategories')
@login_required
def subcategories():
    cat_id = request.args.get('category_id')
    subs = (ExpenseCategory.query
            .filter_by(parent_id=cat_id, active=True)
            .order_by(ExpenseCategory.sort_order)
            .all())
    return jsonify([s.to_dict() for s in subs])


# ── Activity log for a lead ───────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities')
@login_required
def log(lead_id: str):
    try:
        validate_id_param(lead_id, 'LED')
    except ValueError:
        abort(400, description='Invalid lead ID format')
    lead = db.get_or_404(Lead, lead_id)
    if not _can_access(lead):
        abort(403)

    sort      = request.args.get('sort', 'activity_date')
    direction = request.args.get('dir', 'DESC').upper()
    page      = max(1, int(request.args.get('page', 1) or 1))
    per_page  = 20

    allowed_sorts = {'activity_date', 'amount', 'activity_type', 'outcome', 'status', 'destination'}
    if sort not in allowed_sorts:
        sort = 'activity_date'
    if direction not in ('ASC', 'DESC'):
        direction = 'DESC'

    sort_col = getattr(LeadActivity, sort)
    q = (LeadActivity.query
         .filter_by(lead_id=lead_id)
         .order_by(sort_col.desc() if direction == 'DESC' else sort_col.asc()))
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    total_spend = (db.session.query(db.func.sum(LeadActivity.amount))
                   .filter_by(lead_id=lead_id).scalar() or 0)
    pending     = LeadActivity.query.filter_by(lead_id=lead_id, status='Submitted').count()
    reimb_amt   = (db.session.query(db.func.sum(LeadActivity.amount))
                   .filter(LeadActivity.lead_id == lead_id,
                           LeadActivity.reimbursable == True,
                           LeadActivity.status.in_(['Submitted', 'Approved'])).scalar() or 0)

    return render_template(
        'activities/log.html',
        lead=lead,
        entries=pagination.items,
        pagination=pagination,
        sort=sort, direction=direction,
        total_spend=float(total_spend),
        pending_count=pending,
        reimbursable_amt=float(reimb_amt),
        **_activity_context(),
    )


# ── Add entry ─────────────────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/add', methods=['GET', 'POST'])
@login_required
def add(lead_id: str):
    try:
        validate_id_param(lead_id, 'LED')
    except ValueError:
        abort(400, description='Invalid lead ID format')
    lead = db.get_or_404(Lead, lead_id)
    if not _can_access(lead):
        abort(403)

    errors:    dict = {}
    form_data: dict = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        data, errors = _validate_activity(form_data, files=request.files)

        if not errors:
            entry = LeadActivity(
                lead_id        = lead_id,
                user_id        = current_user.id,
                activity_date  = data['activity_date'],
                category_id    = data['category_id'],
                subcategory_id = data['subcategory_id'],
                activity_type  = data['activity_type'],
                amount         = data['amount'],
                miles_driven   = data['miles_driven'],
                mileage_rate   = data['mileage_rate'],
                destination    = data['destination'],
                purpose        = data['purpose'],
                attendees      = data['attendees'],
                attendee_count = data['attendee_count'],
                outcome        = data['outcome'],
                next_action    = data['next_action'],
                payment_method = data['payment_method'],
                reimbursable   = data['reimbursable'],
                receipt_attached = data['receipt_attached'],
                notes          = data['notes'],
                status         = 'Draft',
            )
            db.session.add(entry)
            db.session.flush()  # get entry.id

            receipt_file = request.files.get('receipt_file')
            if receipt_file and receipt_file.filename:
                fname = _save_receipt(receipt_file, lead_id, entry.id)
                entry.receipt_filename = fname
                entry.receipt_attached = True

            db.session.commit()
            flash('Activity entry saved as Draft.', 'success')
            return redirect(url_for('activities.view_entry',
                                    lead_id=lead_id, entry_id=entry.id))

    if not form_data:
        form_data = {'activity_date': date.today().isoformat()}

    return render_template(
        'activities/form.html',
        lead=lead, entry=None,
        form_data=form_data, errors=errors, mode='add',
        **_activity_context(),
    )


# ── View single entry ─────────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/<string:entry_id>')
@login_required
def view_entry(lead_id: str, entry_id: str):
    try:
        validate_id_param(lead_id, 'LED')
        validate_id_param(entry_id, 'ACT')
    except ValueError:
        abort(400, description='Invalid ID format')
    lead  = db.get_or_404(Lead, lead_id)
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.lead_id != lead_id or not _can_access(lead):
        abort(403)
    return render_template(
        'activities/view_entry.html',
        lead=lead, entry=entry,
        status_badge=STATUS_BADGE,
    )


# ── Edit entry ────────────────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/<string:entry_id>/edit',
                     methods=['GET', 'POST'])
@login_required
def edit(lead_id: str, entry_id: str):
    try:
        validate_id_param(lead_id, 'LED')
        validate_id_param(entry_id, 'ACT')
    except ValueError:
        abort(400, description='Invalid ID format')
    lead  = db.get_or_404(Lead, lead_id)
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.lead_id != lead_id or not _can_access(lead):
        abort(403)

    # Approved/Reimbursed: only admin may edit
    if entry.status in ('Approved', 'Reimbursed') and not current_user.is_admin:
        flash('This entry has been approved and is read-only.', 'warning')
        return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))

    errors:    dict = {}
    form_data: dict = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()

        # Submitted: rep can only update notes + receipt
        if entry.status == 'Submitted' and not current_user.is_admin:
            entry.notes = form_data.get('notes', '').strip() or None
            receipt_file = request.files.get('receipt_file')
            if receipt_file and receipt_file.filename:
                _, ext = os.path.splitext(receipt_file.filename.lower())
                if ext in RECEIPT_ALLOWED:
                    fname = _save_receipt(receipt_file, lead_id, entry.id)
                    entry.receipt_filename = fname
                    entry.receipt_attached = True
            db.session.commit()
            flash('Notes updated.', 'success')
            return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))

        # Approved/Reimbursed: admin must provide correction note
        if entry.status in ('Approved', 'Reimbursed') and current_user.is_admin:
            correction = form_data.get('admin_correction_note', '').strip()
            if not correction:
                errors['admin_correction_note'] = 'A correction reason is required.'

        data, val_errors = _validate_activity(form_data, files=request.files)
        errors.update(val_errors)

        if not errors:
            entry.activity_date  = data['activity_date']
            entry.category_id    = data['category_id']
            entry.subcategory_id = data['subcategory_id']
            entry.activity_type  = data['activity_type']
            entry.amount         = data['amount']
            entry.miles_driven   = data['miles_driven']
            entry.mileage_rate   = data['mileage_rate']
            entry.destination    = data['destination']
            entry.purpose        = data['purpose']
            entry.attendees      = data['attendees']
            entry.attendee_count = data['attendee_count']
            entry.outcome        = data['outcome']
            entry.next_action    = data['next_action']
            entry.payment_method = data['payment_method']
            entry.reimbursable   = data['reimbursable']
            entry.receipt_attached = data['receipt_attached']
            entry.notes          = data['notes']

            if entry.status in ('Approved', 'Reimbursed'):
                correction = form_data.get('admin_correction_note', '').strip()
                existing   = entry.review_notes or ''
                stamp      = f'[Admin correction by {current_user.username} on {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] {correction}'
                entry.review_notes = stamp + ('\n' + existing if existing else '')

            receipt_file = request.files.get('receipt_file')
            if receipt_file and receipt_file.filename:
                fname = _save_receipt(receipt_file, lead_id, entry.id)
                entry.receipt_filename = fname
                entry.receipt_attached = True

            db.session.commit()
            flash('Activity entry updated.', 'success')
            return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))

    if not form_data:
        form_data = {
            'activity_date':  entry.activity_date.isoformat() if entry.activity_date else '',
            'category_id':    str(entry.category_id) if entry.category_id else '',
            'subcategory_id': str(entry.subcategory_id) if entry.subcategory_id else '',
            'activity_type':  entry.activity_type or '',
            'amount':         str(entry.amount) if entry.amount is not None else '',
            'miles_driven':   str(entry.miles_driven) if entry.miles_driven is not None else '',
            'destination':    entry.destination or '',
            'purpose':        entry.purpose or '',
            'attendees':      entry.attendees or '',
            'attendee_count': str(entry.attendee_count) if entry.attendee_count else '',
            'outcome':        entry.outcome or '',
            'next_action':    entry.next_action or '',
            'payment_method': entry.payment_method or '',
            'reimbursable':   '1' if entry.reimbursable else '',
            'receipt_attached': '1' if entry.receipt_attached else '',
            'notes':          entry.notes or '',
        }

    return render_template(
        'activities/form.html',
        lead=lead, entry=entry,
        form_data=form_data, errors=errors, mode='edit',
        **_activity_context(),
    )


# ── Delete entry ──────────────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/<string:entry_id>/delete',
                     methods=['POST'])
@login_required
def delete(lead_id: str, entry_id: str):
    try:
        validate_id_param(lead_id, 'LED')
        validate_id_param(entry_id, 'ACT')
    except ValueError:
        abort(400, description='Invalid ID format')
    lead  = db.get_or_404(Lead, lead_id)
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.lead_id != lead_id or not _can_access(lead):
        abort(403)
    if entry.status != 'Draft' and not current_user.is_admin:
        flash('Only Draft entries can be deleted.', 'danger')
        return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))

    if entry.receipt_filename:
        try:
            fpath = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                 'receipts', str(lead_id), entry.receipt_filename)
            if os.path.exists(fpath):
                os.remove(fpath)
        except OSError:
            pass

    db.session.delete(entry)
    db.session.commit()
    flash('Activity entry deleted.', 'success')
    return redirect(url_for('activities.log', lead_id=lead_id))


# ── Submit for approval ───────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/<string:entry_id>/submit',
                     methods=['POST'])
@login_required
def submit(lead_id: str, entry_id: str):
    try:
        validate_id_param(lead_id, 'LED')
        validate_id_param(entry_id, 'ACT')
    except ValueError:
        abort(400, description='Invalid ID format')
    lead  = db.get_or_404(Lead, lead_id)
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.lead_id != lead_id or not _can_access(lead):
        abort(403)
    if entry.status != 'Draft':
        flash('Only Draft entries can be submitted.', 'warning')
        return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))

    entry.status       = 'Submitted'
    entry.submitted_at = datetime.utcnow()
    db.session.commit()
    flash('Entry submitted for approval.', 'success')
    return redirect(url_for('activities.view_entry', lead_id=lead_id, entry_id=entry_id))


# ── Receipt download ──────────────────────────────────────────────────────────

@activities_bp.route('/leads/<string:lead_id>/activities/receipt/<string:entry_id>')
@login_required
def receipt(lead_id: str, entry_id: str):
    try:
        validate_id_param(lead_id, 'LED')
        validate_id_param(entry_id, 'ACT')
    except ValueError:
        abort(400, description='Invalid ID format')
    lead  = db.get_or_404(Lead, lead_id)
    entry = db.get_or_404(LeadActivity, entry_id)
    if entry.lead_id != lead_id or not _can_access(lead):
        abort(403)
    if not entry.receipt_filename:
        abort(404)

    fpath = os.path.join(current_app.config['UPLOAD_FOLDER'],
                         'receipts', str(lead_id), entry.receipt_filename)
    if not os.path.exists(fpath):
        abort(404)
    return send_file(fpath, as_attachment=False)
