from functools import wraps

from flask import redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Restrict a view to admin users; redirects others to the lead dashboard."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('leads.index'))
        return f(*args, **kwargs)
    return decorated
