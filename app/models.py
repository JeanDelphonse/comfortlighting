from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from utils.id_gen import make_id

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.String(17), primary_key=True, default=make_id('users'))
    username   = db.Column(db.String(100), unique=True, nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False, comment='bcrypt hash')
    role       = db.Column(db.Enum('admin', 'sales', 'legal'), nullable=False, default='sales')
    active     = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    # Flask-Login: use the active column
    @property
    def is_active(self) -> bool:
        return self.active

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def is_legal(self) -> bool:
        return self.role in ('admin', 'legal')


class Lead(db.Model):
    __tablename__ = 'leads'

    id                     = db.Column(db.String(17), primary_key=True, default=make_id('leads'))
    created_at             = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at             = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                                       onupdate=datetime.utcnow)
    company_name           = db.Column(db.String(255), nullable=False, index=True)
    action                 = db.Column(db.String(100), nullable=False, index=True)
    contact                = db.Column(db.String(255), nullable=False)
    address                = db.Column(db.Text)
    number                 = db.Column(db.String(30), nullable=False)
    email                  = db.Column(db.String(255), nullable=False)
    notes                  = db.Column(db.Text)
    assigned_user_id       = db.Column(
        db.String(17),
        db.ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'),
        nullable=True,
        index=True,
    )
    sq_ft                  = db.Column(db.Integer)
    targets                = db.Column(db.Text)
    potential              = db.Column(db.Numeric(12, 2))
    progress               = db.Column(db.String(100), index=True)
    expected               = db.Column(db.Date, index=True)
    roi                    = db.Column(db.Numeric(5, 2))
    annual_sales_locations = db.Column(db.Text)
    wip                    = db.Column(db.SmallInteger, nullable=False, default=0, index=True)
    wip_since              = db.Column(db.DateTime, nullable=True)
    agent_research_run_id  = db.Column(db.String(36), nullable=True, index=True)
    previous_progress      = db.Column(db.String(100), nullable=True)
    stage_changed_at       = db.Column(db.DateTime, nullable=True)

    assigned_user = db.relationship(
        'User',
        backref=db.backref('assigned_leads', lazy='dynamic'),
        foreign_keys=[assigned_user_id],
    )

    stage_history = db.relationship('LeadStageHistory', backref='lead', lazy='dynamic',
                                      order_by='LeadStageHistory.changed_at.desc()')

    def days_in_stage(self) -> int:
        """Return days since the stage was last changed."""
        if self.stage_changed_at:
            return (datetime.utcnow() - self.stage_changed_at).days
        return 0


class LeadStageHistory(db.Model):
    __tablename__ = 'lead_stage_history'

    id            = db.Column(db.String(17), primary_key=True, default=make_id('lead_stage_history'))
    lead_id       = db.Column(
        db.String(17),
        db.ForeignKey('leads.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    from_stage    = db.Column(db.String(100), nullable=True)
    to_stage      = db.Column(db.String(100), nullable=False)
    changed_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    changed_by_id = db.Column(
        db.String(17),
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )
    reason        = db.Column(db.String(500), nullable=True)
    days_in_stage = db.Column(db.Numeric(7, 1), nullable=True)

    changed_by = db.relationship('User', backref='stage_changes')


class Proposal(db.Model):
    __tablename__ = 'proposals'

    id               = db.Column(db.String(17), primary_key=True, default=make_id('proposals'))
    lead_id          = db.Column(
        db.String(17),
        db.ForeignKey('leads.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
    )
    raw_llm_text     = db.Column(db.Text, nullable=True)
    greeting         = db.Column(db.Text, nullable=True)
    problem          = db.Column(db.Text, nullable=True)
    solution         = db.Column(db.Text, nullable=True)
    value_prop       = db.Column(db.Text, nullable=True)
    next_step        = db.Column(db.Text, nullable=True)
    edited_by        = db.Column(db.String(100), nullable=True)
    proposal_sent    = db.Column(db.SmallInteger, nullable=False, default=0)
    sent_at          = db.Column(db.DateTime, nullable=True)
    pdf_generated_at = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    lead = db.relationship('Lead', backref=db.backref('proposal', uselist=False))

    def to_dict(self) -> dict:
        return {
            'id':               self.id,
            'lead_id':          self.lead_id,
            'raw_llm_text':     self.raw_llm_text,
            'greeting':         self.greeting,
            'problem':          self.problem,
            'solution':         self.solution,
            'value_prop':       self.value_prop,
            'next_step':        self.next_step,
            'edited_by':        self.edited_by,
            'proposal_sent':    int(self.proposal_sent) if self.proposal_sent is not None else 0,
            'sent_at':          self.sent_at.isoformat() if self.sent_at else None,
            'pdf_generated_at': self.pdf_generated_at.isoformat() if self.pdf_generated_at else None,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
            'updated_at':       self.updated_at.isoformat() if self.updated_at else None,
        }


class Contract(db.Model):
    __tablename__ = 'contracts'

    id                   = db.Column(db.String(17), primary_key=True, default=make_id('contracts'))
    lead_id              = db.Column(
        db.String(17),
        db.ForeignKey('leads.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
    )
    version              = db.Column(db.Integer, nullable=False, default=1)
    raw_llm_text         = db.Column(db.Text, nullable=True)

    # Contract sections
    section_parties          = db.Column(db.Text, nullable=True)
    section_recitals         = db.Column(db.Text, nullable=True)
    section_scope            = db.Column(db.Text, nullable=True)
    section_compensation     = db.Column(db.Text, nullable=True)
    section_timeline         = db.Column(db.Text, nullable=True)
    section_warranties       = db.Column(db.Text, nullable=True)
    section_performance      = db.Column(db.Text, nullable=True)
    section_indemnification  = db.Column(db.Text, nullable=True)
    section_liability        = db.Column(db.Text, nullable=True)
    section_termination      = db.Column(db.Text, nullable=True)
    section_dispute          = db.Column(db.Text, nullable=True)
    section_governing_law    = db.Column(db.Text, nullable=True)
    section_notices          = db.Column(db.Text, nullable=True)
    section_entire_agreement = db.Column(db.Text, nullable=True)
    section_signatures       = db.Column(db.Text, nullable=True)

    generated_by     = db.Column(db.String(100), nullable=False)
    edited_by        = db.Column(db.String(100), nullable=True)
    approved         = db.Column(db.SmallInteger, nullable=False, default=0)
    approved_by      = db.Column(
        db.String(17),
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )
    approved_at      = db.Column(db.DateTime, nullable=True)
    contract_sent    = db.Column(db.SmallInteger, nullable=False, default=0)
    sent_by          = db.Column(db.String(100), nullable=True)
    sent_at          = db.Column(db.DateTime, nullable=True)
    pdf_exported_at  = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    lead             = db.relationship('Lead', backref=db.backref('contract', uselist=False))
    approved_by_user = db.relationship('User', foreign_keys=[approved_by],
                                       backref='approved_contracts')

    def to_dict(self) -> dict:
        return {
            'id':                    self.id,
            'lead_id':               self.lead_id,
            'version':               int(self.version) if self.version is not None else 1,
            'raw_llm_text':          self.raw_llm_text,
            'section_parties':       self.section_parties,
            'section_recitals':      self.section_recitals,
            'section_scope':         self.section_scope,
            'section_compensation':  self.section_compensation,
            'section_timeline':      self.section_timeline,
            'section_warranties':    self.section_warranties,
            'section_performance':   self.section_performance,
            'section_indemnification': self.section_indemnification,
            'section_liability':     self.section_liability,
            'section_termination':   self.section_termination,
            'section_dispute':       self.section_dispute,
            'section_governing_law': self.section_governing_law,
            'section_notices':       self.section_notices,
            'section_entire_agreement': self.section_entire_agreement,
            'section_signatures':    self.section_signatures,
            'generated_by':          self.generated_by,
            'edited_by':             self.edited_by,
            'approved':              int(self.approved) if self.approved is not None else 0,
            'approved_by':           (self.approved_by_user.username
                                      if self.approved_by_user else self.approved_by),
            'approved_at':           self.approved_at.isoformat() if self.approved_at else None,
            'contract_sent':         int(self.contract_sent) if self.contract_sent is not None else 0,
            'sent_by':               self.sent_by,
            'sent_at':               self.sent_at.isoformat() if self.sent_at else None,
            'pdf_exported_at':       self.pdf_exported_at.isoformat() if self.pdf_exported_at else None,
            'created_at':            self.created_at.isoformat() if self.created_at else None,
            'updated_at':            self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractVersion(db.Model):
    __tablename__ = 'contract_versions'

    id                  = db.Column(db.String(17), primary_key=True, default=make_id('contract_versions'))
    contract_id         = db.Column(
        db.String(17),
        db.ForeignKey('contracts.id', ondelete='CASCADE'),
        nullable=False,
    )
    version_number      = db.Column(db.Integer, nullable=False)
    full_text_snapshot  = db.Column(db.Text, nullable=False)
    saved_by            = db.Column(db.String(100), nullable=False)
    saved_at            = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':                 self.id,
            'contract_id':        self.contract_id,
            'version_number':     self.version_number,
            'full_text_snapshot': self.full_text_snapshot,
            'saved_by':           self.saved_by,
            'saved_at':           self.saved_at.isoformat() if self.saved_at else None,
        }


class SystemConfig(db.Model):
    __tablename__ = 'system_config'

    id           = db.Column(db.String(17), primary_key=True, default=make_id('system_config'))
    config_key   = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.String(500), nullable=False)
    updated_by   = db.Column(db.String(100), nullable=True)
    updated_at   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    @staticmethod
    def get(key: str, default=None):
        row = SystemConfig.query.filter_by(config_key=key).first()
        return row.config_value if row else default


class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'

    id                     = db.Column(db.String(17), primary_key=True,
                                       default=make_id('expense_categories'))
    parent_id              = db.Column(
        db.String(17),
        db.ForeignKey('expense_categories.id', ondelete='SET NULL'),
        nullable=True,
    )
    name                   = db.Column(db.String(100), nullable=False)
    requires_attendees     = db.Column(db.Boolean, nullable=False, default=False)
    requires_receipt_above = db.Column(db.Numeric(10, 2), nullable=True)
    is_mileage             = db.Column(db.Boolean, nullable=False, default=False)
    active                 = db.Column(db.Boolean, nullable=False, default=True)
    sort_order             = db.Column(db.Integer, nullable=False, default=0)

    parent = db.relationship('ExpenseCategory', remote_side='ExpenseCategory.id',
                             backref=db.backref('children', lazy='dynamic'))

    def to_dict(self) -> dict:
        return {
            'id':                self.id,
            'parent_id':         self.parent_id,
            'name':              self.name,
            'requires_attendees': bool(self.requires_attendees),
            'is_mileage':        bool(self.is_mileage),
        }


class LeadActivity(db.Model):
    __tablename__ = 'lead_activities'

    id               = db.Column(db.String(17), primary_key=True, default=make_id('lead_activities'))
    lead_id          = db.Column(
        db.String(17),
        db.ForeignKey('leads.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    user_id          = db.Column(
        db.String(17),
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    activity_date    = db.Column(db.Date, nullable=False, index=True)
    category_id      = db.Column(
        db.String(17),
        db.ForeignKey('expense_categories.id'),
        nullable=False,
    )
    subcategory_id   = db.Column(
        db.String(17),
        db.ForeignKey('expense_categories.id'),
        nullable=True,
    )
    activity_type    = db.Column(db.String(50), nullable=False)
    amount           = db.Column(db.Numeric(10, 2), nullable=True)
    miles_driven     = db.Column(db.Numeric(7, 1), nullable=True)
    mileage_rate     = db.Column(db.Numeric(5, 4), nullable=True)
    destination      = db.Column(db.String(255), nullable=False)
    purpose          = db.Column(db.String(500), nullable=False)
    attendees        = db.Column(db.Text, nullable=True)
    attendee_count   = db.Column(db.Integer, nullable=True)
    outcome          = db.Column(db.String(50), nullable=False)
    next_action      = db.Column(db.String(500), nullable=True)
    payment_method   = db.Column(db.String(50), nullable=False)
    reimbursable     = db.Column(db.Boolean, nullable=False, default=False)
    receipt_attached = db.Column(db.Boolean, nullable=False, default=False)
    receipt_filename = db.Column(db.String(255), nullable=True)
    notes            = db.Column(db.Text, nullable=True)
    status           = db.Column(
        db.Enum('Draft', 'Submitted', 'Approved', 'Rejected', 'Reimbursed'),
        nullable=False,
        default='Draft',
        index=True,
    )
    submitted_at     = db.Column(db.DateTime, nullable=True)
    reviewed_by      = db.Column(db.String(100), nullable=True)
    reviewed_at      = db.Column(db.DateTime, nullable=True)
    review_notes     = db.Column(db.Text, nullable=True)
    reimbursed_at    = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    lead        = db.relationship('Lead', backref=db.backref('activities', lazy='dynamic'))
    user        = db.relationship('User', backref=db.backref('activities', lazy='dynamic'),
                                  foreign_keys=[user_id])
    category    = db.relationship('ExpenseCategory', foreign_keys=[category_id])
    subcategory = db.relationship('ExpenseCategory', foreign_keys=[subcategory_id])


class AgentResearchLog(db.Model):
    __tablename__ = 'agent_research_log'

    id               = db.Column(db.String(17), primary_key=True,
                                 default=make_id('agent_research_log'))
    lead_id          = db.Column(
        db.String(17),
        db.ForeignKey('leads.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    run_id           = db.Column(db.String(36), nullable=False, unique=True)
    company_searched = db.Column(db.String(255), nullable=False)
    user_id          = db.Column(
        db.String(17),
        db.ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    fields_populated = db.Column(db.Integer, nullable=False, default=0)
    fields_not_found = db.Column(db.Integer, nullable=False, default=0)
    tokens_used      = db.Column(db.Integer, nullable=False, default=0)
    run_duration_sec = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    search_count     = db.Column(db.Integer, nullable=False, default=0)
    urls_fetched     = db.Column(db.Integer, nullable=False, default=0)
    raw_json         = db.Column(db.Text, nullable=False, default='{}')
    status           = db.Column(db.String(20), nullable=False, default='success')
    error_message    = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                                 index=True)

    user = db.relationship('User', backref=db.backref('research_runs', lazy='dynamic'),
                           foreign_keys=[user_id])
    lead = db.relationship('Lead', backref=db.backref('research_logs', lazy='dynamic'))


class ClauseTemplate(db.Model):
    __tablename__ = 'clause_templates'

    id                 = db.Column(db.String(17), primary_key=True,
                                   default=make_id('clause_templates'))
    clause_key         = db.Column(db.String(100), nullable=False)
    clause_text        = db.Column(db.Text, nullable=False)
    version            = db.Column(db.Integer, nullable=False, default=1)
    active             = db.Column(db.SmallInteger, nullable=False, default=1)
    approved_by_legal  = db.Column(db.String(100), nullable=True)
    created_at         = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':                self.id,
            'clause_key':        self.clause_key,
            'clause_text':       self.clause_text,
            'version':           self.version,
            'active':            int(self.active) if self.active is not None else 1,
            'approved_by_legal': self.approved_by_legal,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
        }
