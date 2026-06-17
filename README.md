The project was run on Azure cloud

ML Task-Scheduler: Azure Deployment Guide

1. Provision the Azure Infrastructure
The application runs on a Linux container managed by Azure App Service.

Log into the Azure Portal. (https://portal.azure.com)

Create a new Web App with the following configuration:

Publish: Code

Runtime stack: Python 3.12

Operating System: Linux

Region: Select the region closest to the target user base (e.g., Southeast Asia).

Pricing Plan: Select a plan that supports custom domains and continuous deployment (Basic/B1 or higher recommended for memory-intensive ML models).

2. Configure Environment Variables (App Settings)
Azure App Service injects environment variables securely through its App Settings panel. Do not commit .env files to the repository.

Navigate to your newly created Web App in the Azure Portal.

On the left sidebar, go to Settings > Environment variables.

Add the following key-value pairs:

FLASK_SECRET_KEY: A secure, random string for Flask session management.

FLASK_ENV: production

GOOGLE_CLIENT_ID: The Client ID from your Google Cloud Console OAuth credentials.

GOOGLE_CLIENT_SECRET: The Client Secret from your Google Cloud Console.

GROQ_API_KEY: Your API key from the Groq Console.

Click Apply to save the settings.

3. Configure the Custom Startup Command
By default, Azure's load balancers may time out long-running AI inference requests. To prevent Gunicorn from prematurely dropping requests, a custom startup command is required.

On the left sidebar, navigate to Settings > Configuration > General Settings.

Locate the Startup Command field and enter the following:

Bash
gunicorn --bind=0.0.0.0 --timeout 600 app:app
Click Save.

4. Setup GitHub Integration & Deployment
Azure App Service features native integration with GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

On the left sidebar, navigate to Deployment > Deployment Center.

Under Source, select GitHub.

Authenticate your GitHub account if prompted.

Select the Organization, Repository, and the specific Branch you wish to deploy (e.g., azure-deployment).

Click Save.

=================================================================================================================

Initialization Steps (Cloud-Architecture Local Setup)
Create a virtual environment: python -m venv .venv

Activate the virtual environment: Windows: .venv\Scripts\Activate.ps1
Mac/Linux: source .venv/bin/activate

Install Python Dependencies: pip install -r requirements.txt

Create the Environment File (.env):
Create a new file named exactly .env in the root folder of the project. Copy and paste this template into it:

Code snippet
FLASK_SECRET_KEY=local_testing_secret_key
FLASK_ENV=development
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GROQ_API_KEY=
(Note: Setting FLASK_ENV=development is mandatory locally so Google OAuth doesn't crash expecting an Azure HTTPS connection).

Get API Keys: Fill in the .env variables (Explained in the API sections below).

Generate the preprocessed dataset: python -m ml.preprocess

Train the duration estimation model: python -m ml.duration_estimator

Run the Flask server: python app.py

Log in: Open http://localhost:8080 in your browser. Log in using the test Google account.

Test the Pipeline: Submit any project documents (Sample documents are already included in the .\TestDocuments folder).

API Setup 1: Groq API Initialization (Replaces Ollama)
Since we moved to a cloud-native architecture, local LLMs like Ollama have been replaced with the lightning-fast Groq Cloud API.

Go to the Groq Cloud Console (Link: https://console.groq.com/).

Create an account or log in.

On the left sidebar, go to API Keys.

Click Create API Key.

Copy the generated key and paste it next to GROQ_API_KEY= in your .env file.

=================================================================================================================

API Setup 2: Google OAuth Credentials
Go to Google Cloud Console (Link: https://console.cloud.google.com/home).

Next to the Google Cloud logo in the top left, select the project dropdown and Create a New Project.

Click the top left hamburger menu, go to APIs & Services > Library. Search for Google Calendar API and click Enable.

Go back to the top left menu, and select APIs & Services > OAuth consent screen.

Select External as the User Type and click Create.

Fill in the required app information (App name, support email, developer email) and click Save and Continue through the Scopes phase.

Under the Test Users phase, click Add Users. Add the specific Gmail address you intend to test the app with, then click Save.

Now go to APIs & Services > Credentials on the left sidebar.

Click Create Credentials at the top, and select OAuth Client ID.

Under Application type, select Web application and name it "Flask Local Client".

Scroll down to Authorized redirect URIs, click Add URI, and paste this exact URL:
http://localhost:8080/oauth2callback

Click Create.

IMPORTANT DEPLOYMENT CHANGE: A popup will appear with your keys. Do NOT download the JSON file. Instead:

Copy your Client ID and paste it next to GOOGLE_CLIENT_ID= in your .env file.

Copy your Client Secret and paste it next to GOOGLE_CLIENT_SECRET= in your .env file.

Azure will automatically generate a GitHub Actions workflow file (.yml) and commit it to your selected branch, triggering the first build and deployment sequence.
