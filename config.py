import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-before-deploying')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://comfort:@localhost/comfortlighting'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TIMEOUT = 1800          # 30 minutes inactivity
    LEADS_PER_PAGE = 25
    WTF_CSRF_ENABLED = True
    # Keep sessions server-side (signed cookies) – do not make permanent
    SESSION_PERMANENT = False
