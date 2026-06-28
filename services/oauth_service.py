"""
Google OAuth service for handling authentication flow securely via Environment Variables.
"""
import json
import os
from pathlib import Path

from flask import session, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import config

OAUTH_STATE_FILE = config.RUNTIME_DIR / "oauth_state.json"
OAUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

LOCAL_REDIRECT_URI = "http://localhost:8080/oauth2callback"


def is_local_development():
    """Check if running in local development mode (not in Azure)."""
    # Azure App Service sets WEBSITE_SITE_NAME environment variable
    return not os.getenv("WEBSITE_SITE_NAME")


def get_client_config():
    """Builds the Google OAuth config dictionary dynamically from environment variables."""
    return {
        "web": {
            "client_id": config.CLIENT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": config.CLIENT_SECRET
        }
    }


def get_local_redirect_uri():
    return LOCAL_REDIRECT_URI


def save_oauth_state(state, code_verifier):
    data = {"state": state, "code_verifier": code_verifier}
    with OAUTH_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)


def load_oauth_state():
    if not OAUTH_STATE_FILE.exists():
        return None, None
    try:
        with OAUTH_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("state"), data.get("code_verifier")
    except (OSError, json.JSONDecodeError):
        return None, None


def clear_oauth_state():
    if OAUTH_STATE_FILE.exists():
        OAUTH_STATE_FILE.unlink()


def get_authorization_url():
    """Generates the secure login URL to send to Google."""
    try:
        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES)

        redirect_uri = get_local_redirect_uri() if is_local_development() else url_for('oauth2callback', _external=True).replace('http://', 'https://')
        flow.redirect_uri = redirect_uri

        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return authorization_url, state, flow.code_verifier
    except Exception as e:
        raise RuntimeError(f"Google OAuth Error: {str(e)}")


def handle_oauth_callback(authorization_response, state, code_verifier):
    """Handle the OAuth callback after user grants permission."""
    try:
        if not state or not code_verifier:
            raise RuntimeError("Missing OAuth state or code verifier. Check session/cookie persistence.")

        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES, state=state)
        flow.code_verifier = code_verifier

        redirect_uri = get_local_redirect_uri() if is_local_development() else url_for('oauth2callback', _external=True).replace('http://', 'https://')
        flow.redirect_uri = redirect_uri

        if is_local_development():
            flow.fetch_token(authorization_response=authorization_response)
        else:
            secure_response_url = authorization_response.replace('http://', 'https://')
            flow.fetch_token(authorization_response=secure_response_url)

        return credentials_to_dict(flow.credentials)
    except Exception as e:
        raise RuntimeError(f"OAuth Callback Error: {str(e)}")

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials_from_session():
    if 'credentials' not in session:
        raise RuntimeError("No credentials found in session. Please log in first.")
    return Credentials(**session['credentials'])