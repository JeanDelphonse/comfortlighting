import logging
import os
import time
from logging.handlers import RotatingFileHandler

from flask import Flask, session, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from .models import db, User
from .extensions import limiter
from config import Config

login_manager = LoginManager()
csrf = CSRFProtect()


def _configure_logging(app: Flask) -> None:
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    fmt = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')

    # error.log — ERROR and above, always on
    error_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'error.log'),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    app.logger.addHandler(error_handler)

    # research.log — INFO and above, always on (used to debug agent research)
    research_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'research.log'),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8',
    )
    research_handler.setLevel(logging.INFO)
    research_handler.setFormatter(fmt)
    app.logger.addHandler(research_handler)
    app.logger.setLevel(logging.INFO)

    # In debug mode also stream INFO+ to the console
    if app.debug:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        app.logger.addHandler(console)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    _configure_logging(app)

    # ── Error handler ─────────────────────────────────────────────────────────
    import traceback
    from flask import request as _flask_req

    @app.errorhandler(Exception)
    def handle_exception(exc):
        from werkzeug.exceptions import HTTPException
        # Let Flask handle HTTP exceptions (404, 403, etc.) normally
        if isinstance(exc, HTTPException):
            return exc
        app.logger.error(
            'Unhandled exception on %s %s\n%s',
            _flask_req.method,
            _flask_req.url,
            traceback.format_exc(),
        )
        return 'An internal error occurred.', 500

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, user_id)

    # ── Session timeout ───────────────────────────────────────────────────────
    @app.before_request
    def check_session_timeout():
        if current_user.is_authenticated:
            last = session.get('last_activity', 0)
            if time.time() - last > app.config['SESSION_TIMEOUT']:
                from flask_login import logout_user
                logout_user()
                session.clear()
                return redirect(url_for('auth.login', timeout=1))
            session['last_activity'] = time.time()

    # ── Template globals ──────────────────────────────────────────────────────
    from flask import request as _req

    @app.template_global()
    def sort_url(col: str, current_sort: str, current_dir: str) -> str:
        args = _req.args.to_dict()
        args['sort'] = col
        args['page'] = '1'
        if current_sort == col:
            args['dir'] = 'ASC' if current_dir.upper() == 'DESC' else 'DESC'
        else:
            args['dir'] = 'ASC'
        return url_for('leads.index', **args)

    @app.template_global()
    def page_url(p: int) -> str:
        args = _req.args.to_dict()
        args['page'] = str(p)
        return url_for('leads.index', **args)

    @app.template_global()
    def export_url() -> str:
        args = _req.args.to_dict()
        args['export'] = 'csv'
        return url_for('leads.index', **args)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth.routes import auth_bp
    from .leads.routes import leads_bp
    from .admin.routes import admin_bp
    from .proposals.routes import proposals_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(proposals_bp)
    from .contracts.routes import contracts_bp
    app.register_blueprint(contracts_bp)
    from .activities.routes import activities_bp
    app.register_blueprint(activities_bp)

    # ── Context processor ─────────────────────────────────────────────────────
    @app.context_processor
    def inject_pending_expenses():
        if current_user.is_authenticated and current_user.is_admin:
            from .models import LeadActivity
            try:
                count = LeadActivity.query.filter_by(status='Submitted').count()
            except Exception:
                count = 0
            return {'pending_expense_count': count}
        return {'pending_expense_count': 0}

    # ── One-time setup route ──────────────────────────────────────────────────
    # Accessible only when the admin user's password is not a valid Werkzeug
    # hash (e.g. after fresh DB seed with PHP bcrypt hash or placeholder).
    # Self-disables once a valid password is stored.
    from flask import request as _setup_req, render_template_string
    from werkzeug.security import generate_password_hash

    _SETUP_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Initial Setup – ComfortLighting</title>
  <style>
    body { font-family: sans-serif; max-width: 420px; margin: 80px auto; padding: 0 1rem; }
    h1 { font-size: 1.4rem; margin-bottom: 1.5rem; }
    label { display: block; margin-bottom: .25rem; font-size: .9rem; font-weight: 600; }
    input { width: 100%; padding: .5rem; margin-bottom: 1rem; box-sizing: border-box;
            border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
    button { width: 100%; padding: .6rem; background: #1a73e8; color: #fff;
             border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
    .error { color: #c00; margin-bottom: 1rem; font-size: .9rem; }
    .info  { color: #555; font-size: .85rem; margin-bottom: 1.5rem; }
  </style>
</head>
<body>
  <h1>ComfortLighting — Initial Setup</h1>
  <p class="info">Set the password for the <strong>admin</strong> account.
     This page is only available while no valid password is set.</p>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  <form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label for="pw">New password (min 8 characters)</label>
    <input type="password" id="pw" name="password" required minlength="8" autofocus>
    <label for="pw2">Confirm password</label>
    <input type="password" id="pw2" name="password2" required minlength="8">
    <button type="submit">Set password &amp; go to login</button>
  </form>
</body>
</html>
"""

    def _admin_needs_setup() -> bool:
        """Return True when the admin user exists with an invalid Werkzeug hash."""
        try:
            admin = User.query.filter_by(username='admin').first()
            if admin is None:
                return False
            h = admin.password or ''
            # Werkzeug hashes start with 'pbkdf2:', 'scrypt:', or 'bcrypt:'
            return not any(h.startswith(p) for p in ('pbkdf2:', 'scrypt:', 'bcrypt:'))
        except Exception:
            return False

    @app.route('/setup', methods=['GET', 'POST'])
    def setup():
        if not _admin_needs_setup():
            return redirect(url_for('auth.login'))

        error = None
        if _setup_req.method == 'POST':
            pw  = _setup_req.form.get('password', '')
            pw2 = _setup_req.form.get('password2', '')
            if len(pw) < 8:
                error = 'Password must be at least 8 characters.'
            elif pw != pw2:
                error = 'Passwords do not match.'
            else:
                admin = User.query.filter_by(username='admin').first()
                admin.set_password(pw)
                db.session.commit()
                return redirect(url_for('auth.login'))

        return render_template_string(_SETUP_TEMPLATE, error=error)

    return app
