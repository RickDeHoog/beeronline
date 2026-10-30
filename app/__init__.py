"""
app/__init__.py

Initializes the Flask application and registers its routes.
"""

from flask import Flask

# Create the Flask application
app = Flask(__name__)

# Import routes after creating app to avoid circular imports
from app import routes  # noqa: E402, F401