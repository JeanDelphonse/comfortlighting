from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from ..models import db, User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('leads.index'))
        return f(*args, **kwargs)
    return decorated


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
            if role not in ('admin', 'sales'):
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
            uid = int(request.form.get('user_id', 0))
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
            uid      = int(request.form.get('user_id', 0))
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
