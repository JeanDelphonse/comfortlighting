import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-before-deploying')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://comfort:@localhost/comfortlighting'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,   # test connection before use; reconnects if stale
        'pool_recycle': 280,     # recycle connections after ~4.5 min (MySQL default wait_timeout is 8h but cPanel may be lower)
    }
    SESSION_TIMEOUT = 1800          # 30 minutes inactivity
    LEADS_PER_PAGE = 25
    WTF_CSRF_ENABLED = True
    WTF_CSRF_HEADERS = ['X-CSRFToken']
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    # Keep sessions server-side (signed cookies) – do not make permanent
    SESSION_PERMANENT = False
    # Receipt file uploads — stored outside app/static/ so Apache cannot serve directly
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
