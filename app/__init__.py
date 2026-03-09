import time
from flask import Flask, session, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from .models import db, User
from config import Config

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(admin_bp)

    return app
