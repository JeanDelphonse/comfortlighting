"""
Development entry point.
Run: python app.py
Production (GoDaddy cPanel): passenger_wsgi.py is used instead.
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
