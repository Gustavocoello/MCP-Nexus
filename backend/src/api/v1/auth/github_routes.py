from flask import Blueprint
from src.services.auth.github.github_auth import github_login, github_callback

github_auth_bp = Blueprint('github_auth', __name__, url_prefix='/api/v1/auth/github')

# Login
github_auth_bp.add_url_rule('/login', view_func=github_login, methods=['GET'])

# Callback
github_auth_bp.add_url_rule('/callback', view_func=github_callback, methods=['GET'])
