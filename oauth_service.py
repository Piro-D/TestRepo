"""
Google OAuth service for handling authentication flow.
"""

from flask import session, url_for, redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import config


def get_authorization_url():
    """
    Generate the Google OAuth authorization URL.
    
    Returns:
        tuple: (authorization_url, state, code_verifier)
    """
    try:
        flow = Flow.from_client_secrets_file(config.CLIENT_SECRETS_FILE, scopes=config.SCOPES)
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url, state, flow.code_verifier
    except Exception as e:
        raise RuntimeError(f"Google OAuth Error: {str(e)}. Check your internet connection and credentials.json file.")


def handle_oauth_callback(authorization_response, state, code_verifier):
    """
    Handle the OAuth callback after user grants permission.
    
    Args:
        authorization_response: The full callback URL from Google
        state: The state parameter from the initial request
        code_verifier: The PKCE code verifier
        
    Returns:
        dict: Credentials dictionary to store in session
    """
    try:
        flow = Flow.from_client_secrets_file(config.CLIENT_SECRETS_FILE, scopes=config.SCOPES, state=state)
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        flow.code_verifier = code_verifier
        flow.fetch_token(authorization_response=authorization_response)
        return credentials_to_dict(flow.credentials)
    except Exception as e:
        raise RuntimeError(f"OAuth Callback Error: {str(e)}. Please try logging in again.")


def credentials_to_dict(credentials):
    """
    Convert Credentials object to dictionary for session storage.
    
    Args:
        credentials: Google Credentials object
        
    Returns:
        dict: Serializable credentials dictionary
    """
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def get_credentials_from_session():
    """
    Retrieve and refresh credentials from session if needed.
    
    Returns:
        Credentials: Google Credentials object
        
    Raises:
        RuntimeError: If credentials are not available
    """
    if 'credentials' not in session:
        raise RuntimeError("No credentials found in session. Please log in first.")
    
    return Credentials(**session['credentials'])
