import io
import re
from datetime import datetime

import anthropic
from flask import Blueprint, request, jsonify, abort, current_app, send_file
from flask_login import login_required, current_user

from ..models import db, Lead, Proposal
from ..extensions import limiter
from . import llm
from .pdf import render_pdf

proposals_bp = Blueprint('proposals', __name__, url_prefix='/proposals')


def _validate_lead_id(data: dict):
    """Return (lead_id, error_response) — error_response is None on success."""
    try:
        lead_id = int(data.get('lead_id', 0))
        if lead_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return None, (jsonify({'error': 'Invalid lead_id.'}), 400)
    return lead_id, None


# ── Generate ──────────────────────────────────────────────────────────────────

@proposals_bp.route('/generate', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def generate():
    data = request.get_json(silent=True) or {}
    lead_id, err = _validate_lead_id(data)
    if err:
        return err

    lead = db.get_or_404(Lead, lead_id)

    try:
        raw_text = llm.generate(lead)
    except anthropic.APITimeoutError:
        return jsonify({'error': 'Generation timed out. Please try again.'}), 408
    except Exception as exc:
        current_app.logger.error('Proposal generation failed for lead %s: %s', lead_id, exc)
        return jsonify({'error': 'Generation failed. Please try again.'}), 500

    sections = llm.parse_sections(raw_text)

    proposal = Proposal.query.filter_by(lead_id=lead_id).first()
    if proposal:
        proposal.raw_llm_text = raw_text
        proposal.greeting    = sections['greeting']
        proposal.problem     = sections['problem']
        proposal.solution    = sections['solution']
        proposal.value_prop  = sections['value_prop']
        proposal.next_step   = sections['next_step']
        proposal.updated_at  = datetime.utcnow()
    else:
        proposal = Proposal(
            lead_id=lead_id,
            raw_llm_text=raw_text,
            greeting=sections['greeting'],
            problem=sections['problem'],
            solution=sections['solution'],
            value_prop=sections['value_prop'],
            next_step=sections['next_step'],
        )
        db.session.add(proposal)

    db.session.commit()
    return jsonify(proposal.to_dict()), 200


# ── Save ──────────────────────────────────────────────────────────────────────

@proposals_bp.route('/save', methods=['POST'])
@login_required
def save():
    data = request.get_json(silent=True) or {}
    lead_id, err = _validate_lead_id(data)
    if err:
        return err

    proposal = Proposal.query.filter_by(lead_id=lead_id).first_or_404()

    proposal.greeting   = (data.get('greeting')   or '').strip()
    proposal.problem    = (data.get('problem')    or '').strip()
    proposal.solution   = (data.get('solution')   or '').strip()
    proposal.value_prop = (data.get('value_prop') or '').strip()
    proposal.next_step  = (data.get('next_step')  or '').strip()
    proposal.edited_by  = current_user.username
    proposal.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(proposal.to_dict()), 200


# ── PDF ───────────────────────────────────────────────────────────────────────

@proposals_bp.route('/<int:lead_id>/pdf', methods=['GET'])
@login_required
def pdf(lead_id: int):
    lead     = db.get_or_404(Lead, lead_id)
    proposal = Proposal.query.filter_by(lead_id=lead_id).first_or_404()

    pdf_bytes = render_pdf(lead, proposal)

    proposal.pdf_generated_at = datetime.utcnow()
    db.session.commit()

    safe_name = re.sub(r'[^A-Za-z0-9_]', '_', lead.company_name or '')[:40]
    filename  = f'ComfortLighting_Proposal_{safe_name}_{datetime.now().strftime("%Y-%m-%d")}.pdf'

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


# ── Mark sent ─────────────────────────────────────────────────────────────────

@proposals_bp.route('/mark_sent', methods=['POST'])
@login_required
def mark_sent():
    data = request.get_json(silent=True) or {}
    lead_id, err = _validate_lead_id(data)
    if err:
        return err

    proposal = Proposal.query.filter_by(lead_id=lead_id).first_or_404()
    lead     = db.get_or_404(Lead, lead_id)

    sent = data.get('sent', True)
    proposal.proposal_sent = 1 if sent else 0
    proposal.sent_at       = datetime.utcnow() if sent else None

    if sent and lead.action != 'Proposal Sent':
        lead.action = 'Proposal Sent'

    db.session.commit()

    return jsonify({
        'proposal_sent': proposal.proposal_sent,
        'sent_at': proposal.sent_at.isoformat() if proposal.sent_at else None,
    }), 200
