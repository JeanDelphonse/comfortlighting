import time
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from ..models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('leads.index'))

    error = None
    username_val = ''

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        username_val = username

        if not username or not password:
            error = 'Username and password are required.'
        else:
            user = User.query.filter_by(username=username).first()
            if user and user.active and user.check_password(password):
                login_user(user, remember=False)
                session['last_activity'] = time.time()
                return redirect(url_for('leads.index'))
            else:
                # Generic message to prevent user enumeration
                error = 'Invalid username or password.'

    return render_template(
        'auth/login.html',
        error=error,
        username_val=username_val,
        timeout=request.args.get('timeout'),
    )


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))
