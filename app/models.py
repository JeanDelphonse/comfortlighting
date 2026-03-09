from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(100), unique=True, nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False, comment='bcrypt hash')
    role       = db.Column(db.Enum('admin', 'sales'), nullable=False, default='sales')
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


class Lead(db.Model):
    __tablename__ = 'leads'

    id                     = db.Column(db.Integer, primary_key=True)
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
    sq_ft                  = db.Column(db.Integer)
    targets                = db.Column(db.Text)
    potential              = db.Column(db.Numeric(12, 2))
    progress               = db.Column(db.String(100), index=True)
    expected               = db.Column(db.Date, index=True)
    roi                    = db.Column(db.Numeric(5, 2))
    annual_sales_locations = db.Column(db.Text)
