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

Azure will automatically generate a GitHub Actions workflow file (.yml) and commit it to your selected branch, triggering the first build and deployment sequence.
