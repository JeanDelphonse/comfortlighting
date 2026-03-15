import io
from datetime import datetime
from functools import wraps

import anthropic
from flask import (Blueprint, request, jsonify, abort, current_app,
                   send_file, render_template, redirect, url_for, flash)
from flask_login import login_required, current_user

from ..models import db, Lead, Contract, ContractVersion, ClauseTemplate
from ..extensions import limiter
from . import llm as contract_llm
from .pdf import render_pdf

contracts_bp = Blueprint('contracts', __name__, url_prefix='/contracts')


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                return jsonify({'error': 'Contract management requires Legal or Admin role.'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def _load_templates() -> dict:
    """Return dict of {clause_key: clause_text} for all active templates."""
    rows = ClauseTemplate.query.filter_by(active=1).all()
    return {r.clause_key: r.clause_text for r in rows}


# POST /contracts/generate
@contracts_bp.route('/generate', methods=['POST'])
@login_required
@role_required('admin', 'legal')
@limiter.limit('5 per hour')
def generate():
    data = request.get_json() or {}
    lead_id = data.get('lead_id')
    if not isinstance(lead_id, int) or lead_id < 1:
        return jsonify({'error': 'Invalid lead_id'}), 400

    lead = db.get_or_404(Lead, lead_id)

    # Block re-generate if already sent (requires admin to clear)
    existing = Contract.query.filter_by(lead_id=lead_id).first()
    if existing and existing.contract_sent and current_user.role != 'admin':
        return jsonify({'error': 'Contract already sent to client. Only Admin can re-generate.'}), 403

    templates = _load_templates()
    if not templates:
        return jsonify({'error': 'Contract template configuration error — contact Admin.'}), 500

    try:
        raw_text = contract_llm.generate(lead, templates)
    except anthropic.APITimeoutError:
        return jsonify({'error': 'Generation timed out. Please try again.'}), 408
    except Exception as e:
        current_app.logger.error('Contract LLM error lead %s: %s', lead_id, e)
        return jsonify({'error': 'Generation failed. Please try again.'}), 500

    sections = contract_llm.parse_contract_sections(raw_text)

    if existing:
        existing.raw_llm_text = raw_text
        existing.generated_by = current_user.username
        existing.edited_by = None
        existing.approved = 0
        existing.approved_by = None
        existing.approved_at = None
        existing.version = (existing.version or 1) + 1
        for col, val in sections.items():
            setattr(existing, col, val)
        contract = existing
    else:
        contract = Contract(
            lead_id=lead_id,
            raw_llm_text=raw_text,
            generated_by=current_user.username,
            version=1,
            **sections,
        )
        db.session.add(contract)

    db.session.flush()
    # Audit snapshot
    snapshot = '\n\n'.join(f'{k.upper()}:\n{v}' for k, v in sections.items())
    db.session.add(ContractVersion(
        contract_id=contract.id,
        version_number=contract.version,
        full_text_snapshot=snapshot,
        saved_by=current_user.username,
    ))
    db.session.commit()
    return jsonify(contract.to_dict()), 200


# GET /contracts/<lead_id>  — returns current contract JSON
@contracts_bp.route('/<int:lead_id>', methods=['GET'])
@login_required
@role_required('admin', 'legal')
def get_contract(lead_id: int):
    contract = Contract.query.filter_by(lead_id=lead_id).first()
    if not contract:
        return jsonify({}), 200
    return jsonify(contract.to_dict()), 200


# POST /contracts/<contract_id>/save
@contracts_bp.route('/<int:contract_id>/save', methods=['POST'])
@login_required
@role_required('admin', 'legal')
def save(contract_id: int):
    contract = db.get_or_404(Contract, contract_id)
    data = request.get_json() or {}

    section_cols = [col for _, col in contract_llm.SECTION_MAP]
    for col in section_cols:
        if col in data:
            setattr(contract, col, data[col].strip())

    contract.edited_by = current_user.username
    contract.version = (contract.version or 1) + 1
    contract.approved = 0
    contract.approved_by = None
    contract.approved_at = None
    contract.updated_at = datetime.utcnow()

    db.session.flush()
    snapshot = '\n\n'.join(
        f'{h}:\n{getattr(contract, col) or ""}' for h, col in contract_llm.SECTION_MAP
    )
    db.session.add(ContractVersion(
        contract_id=contract.id,
        version_number=contract.version,
        full_text_snapshot=snapshot,
        saved_by=current_user.username,
    ))
    db.session.commit()
    return jsonify(contract.to_dict()), 200


# POST /contracts/<contract_id>/approve
@contracts_bp.route('/<int:contract_id>/approve', methods=['POST'])
@login_required
@role_required('admin', 'legal')
def approve(contract_id: int):
    contract = db.get_or_404(Contract, contract_id)
    data = request.get_json() or {}
    approve_flag = data.get('approved', True)

    contract.approved = 1 if approve_flag else 0
    contract.approved_by = current_user.username if approve_flag else None
    contract.approved_at = datetime.utcnow() if approve_flag else None
    db.session.commit()
    return jsonify({
        'approved': contract.approved,
        'approved_by': contract.approved_by,
        'approved_at': contract.approved_at.isoformat() if contract.approved_at else None,
    }), 200


# GET /contracts/<lead_id>/pdf
@contracts_bp.route('/<int:lead_id>/pdf', methods=['GET'])
@login_required
@role_required('admin', 'legal')
def pdf(lead_id: int):
    lead = db.get_or_404(Lead, lead_id)
    contract = Contract.query.filter_by(lead_id=lead_id).first()
    if not contract:
        abort(404)
    if not contract.approved:
        flash('Legal approval required before exporting PDF.', 'warning')
        return redirect(url_for('leads.view', lead_id=lead_id))

    pdf_bytes = render_pdf(lead, contract)
    contract.pdf_exported_at = datetime.utcnow()
    db.session.commit()

    safe = ''.join(c if c.isalnum() else '_' for c in lead.company_name)[:40]
    filename = f'ComfortLighting_Contract_{safe}_{datetime.now().strftime("%Y-%m-%d")}_v{contract.version}.pdf'
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


# POST /contracts/<contract_id>/mark_sent
@contracts_bp.route('/<int:contract_id>/mark_sent', methods=['POST'])
@login_required
@role_required('admin', 'legal')
def mark_sent(contract_id: int):
    contract = db.get_or_404(Contract, contract_id)
    data = request.get_json() or {}
    sent = data.get('sent', True)

    # Write-once: only admin can clear
    if not sent and current_user.role != 'admin':
        return jsonify({'error': 'Only Admin can clear sent status.'}), 403

    contract.contract_sent = 1 if sent else 0
    contract.sent_by = current_user.username if sent else None
    contract.sent_at = datetime.utcnow() if sent else None

    if sent:
        lead = db.session.get(Lead, contract.lead_id)
        if lead and lead.action != 'Contract Sent':
            lead.action = 'Contract Sent'

    db.session.commit()
    return jsonify({
        'contract_sent': contract.contract_sent,
        'sent_by': contract.sent_by,
        'sent_at': contract.sent_at.isoformat() if contract.sent_at else None,
    }), 200


# GET /contracts/<contract_id>/versions
@contracts_bp.route('/<int:contract_id>/versions', methods=['GET'])
@login_required
@role_required('admin', 'legal')
def versions(contract_id: int):
    db.get_or_404(Contract, contract_id)
    rows = ContractVersion.query.filter_by(contract_id=contract_id).order_by(ContractVersion.version_number.desc()).all()
    return jsonify([r.to_dict() for r in rows]), 200
