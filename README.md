============================================================
# Project Description
============================================================

This is a Machine Learning Project made by 3 people : 
- Jason Nicholas Rahardjo - 2802411411
- Arnaldo Setiawan - 2802410232
- Antonius Steven - 2802415870

There are 2 ways to deploy the project
1. Through Local Deployment
2. Deployed through azure

The following are the guiding steps in order to deploy the project

Note for MLFlow code:
- Due to dependency conflicts, ML flow needs to be manually installed through the terminal ("pip install mlflow")
- The ML Flow code is stored inside duration_estimator.py, uncomment it if you want to run and produce the artifacts
- MLFlow artifacts are named ml_runs.zip and mlflow.db


============================================================
# Local Deployment Guide
============================================================

For local deployment, there are 2 things we need to do. 
- First is project intialization
- Second is API setup (Google calendar & Groq)

=============================
## Project Initialization
=============================

1. Create a virtual environment ( 'python -m venv .venv' )

2. Activate the virtual environment ( '.venv\Scripts\Activate.ps1' )

3. Install Python Dependencies ( 'pip install -r requirements.txt' )

4. Create the Environment File (.env) and paste the following template to it
- FLASK_SECRET_KEY=local_testing_secret_key
- FLASK_ENV=development
- GOOGLE_CLIENT_ID=
- GOOGLE_CLIENT_SECRET=
- GROQ_API_KEY=
(Note: Setting FLASK_ENV=development is mandatory locally so Google OAuth doesn't crash expecting an Azure HTTPS connection).

5. These .env fields will be filled in the API setup stage

6. Generate the preprocessed dataset ( 'python -m ml.preprocess' )

7. Train the duration estimation model ( 'python -m ml.duration_estimator' )

9. Run the Flask server ('python app.py')

10. Log in: Open http://localhost:8080 in your browser. Log in using the test Google account.

11. Test the Pipeline: Submit any project documents (Sample documents are already included in the .\TestDocuments folder).


=============================
## API Setup
=============================

### API Setup 1: Groq API Initialization (Replaces Ollama)

1. Go to the Groq Cloud Console (Link: https://console.groq.com/).

2. Create an account or log in.

3. On the left sidebar, go to API Keys.

4. Click Create API Key.

5. Copy the generated key and paste it next to GROQ_API_KEY= in your .env file.


### API Setup 2: Google OAuth Credentials

1. Go to Google Cloud Console (Link: https://console.cloud.google.com/home).

2. Next to the Google Cloud logo in the top left, select the project dropdown and Create a New Project.

3. Click the top left hamburger menu, go to APIs & Services > Library. Search for Google Calendar API and click Enable.

4. Go back to the top left menu, and select APIs & Services > OAuth consent screen.

4. After this, configure the Google Auth Platform by clicking Get Started.

5. Select External as the User Type and click Create.

6. Fill in the required app information (App name, support email, developer email) and click Save and Continue through the Scopes phase.

7. Next go to Audience and under the Test Users phase, click Add Users. Add the specific Gmail address you intend to test the app with, then click Save.

8. Now go to APIs & Services > Credentials on the left sidebar.

9. Click Create Credentials at the top, and select OAuth Client ID.

10. Under Application type, select Web application and name it "Flask Local Client".

11. Scroll down to Authorized redirect URIs, click Add URI, and paste this exact URL: http://localhost:8080/oauth2callback

12. Click Create.

13. Copy your Client ID and paste it next to GOOGLE_CLIENT_ID= in your .env file.

14. Copy your Client Secret and paste it next to GOOGLE_CLIENT_SECRET= in your .env file.







============================================================
# For online deployment, The project was run on Azure cloud
# ML Task-Scheduler: Azure Deployment Guide
============================================================
## 1. Provision the Azure Infrastructure

The application runs on a Linux container managed by Azure App Service.

Log into the Azure Portal. (https://portal.azure.com)

Create a new Web App with the following configuration:
- Publish: Code
- Runtime stack: Python 3.12
- Operating System: Linux
- Region: Select the region closest to the target user base (e.g., Southeast Asia).
- Pricing Plan: Select a plan that supports custom domains and continuous deployment (Basic/B1 or higher recommended for memory-intensive ML models).

=========================================================

## 2. Configure Environment Variables (App Settings)

Azure App Service injects environment variables securely through its App Settings panel. Do not commit .env files to the repository.

Navigate to your newly created Web App in the Azure Portal.

On the left sidebar, go to Settings > Environment variables.

Add the following key-value pairs:
- FLASK_SECRET_KEY: A secure, random string for Flask session management.
- FLASK_ENV: production
- GOOGLE_CLIENT_ID: The Client ID from your Google Cloud Console OAuth credentials.
- GOOGLE_CLIENT_SECRET: The Client Secret from your Google Cloud Console.
- GROQ_API_KEY: Your API key from the Groq Console.
Click Apply to save the settings.

=========================================================

## 3. Configure the Custom Startup Command

By default, Azure's load balancers may time out long-running AI inference requests. To prevent Gunicorn from prematurely dropping requests, a custom startup command is required.

On the left sidebar, navigate to Settings > Configuration > General Settings.

Locate the Startup Command field and enter the following:

Bash
gunicorn --bind=0.0.0.0 --timeout 600 app:app

Click Save.

=========================================================

## 4. Setup GitHub Integration & Deployment

Azure App Service features native integration with GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

On the left sidebar, navigate to Deployment > Deployment Center.

Under Source, select GitHub.

Authenticate your GitHub account if prompted.

Select the Organization, Repository, and the specific Branch you wish to deploy (e.g., azure-deployment).

Click Save.

=========================================================
