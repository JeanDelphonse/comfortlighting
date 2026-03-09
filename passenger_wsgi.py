"""
GoDaddy cPanel Passenger WSGI entry point.
The variable must be named `application`.

cPanel setup:
  1. Set Python version to 3.11+ in the Python App manager
  2. Set Application startup file to: passenger_wsgi.py
  3. Set Application Entry point to: application
  4. Run `pip install -r requirements.txt` in the virtual env
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

application = create_app()
