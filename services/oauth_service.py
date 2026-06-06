"""
Google OAuth service for handling authentication flow securely via Environment Variables.
"""
from flask import session, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import config

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

def get_authorization_url():
    try:
        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES)
        flow.redirect_uri = url_for('oauth2callback', _external=True).replace('http://', 'https://')
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        return authorization_url, state, flow.code_verifier
    except Exception as e:
        raise RuntimeError(f"Google OAuth Error: {str(e)}")

def handle_oauth_callback(authorization_response, state, code_verifier):
    """
    Handle the OAuth callback after user grants permission.
    """
    try:
        # 🌟 THE BAIT AND SWITCH: Force the incoming Azure URL to be HTTPS
        secure_response_url = authorization_response.replace('http://', 'https://')

        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES, state=state)
        # Force the outgoing redirect URI to HTTPS
        flow.redirect_uri = url_for('oauth2callback', _external=True).replace('http://', 'https://')
        flow.code_verifier = code_verifier
        
        # Feed the secured URL to the Google library
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