"""
Run this script on the server once to set a valid Werkzeug password hash
for the admin user (or any user with a broken hash).

Usage:
    python set_admin_password.py <username> <new_password>

Example:
    python set_admin_password.py admin Admin1234!
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import db, User

def main():
    if len(sys.argv) != 3:
        print("Usage: python set_admin_password.py <username> <new_password>")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    if len(new_password) < 8:
        print("Error: password must be at least 8 characters.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: user '{username}' not found.")
            sys.exit(1)

        user.set_password(new_password)
        db.session.commit()
        print(f"Password updated for user '{username}'.")

if __name__ == '__main__':
    main()
