To create an Azure Function App that listens for an event when a user is removed from the “New Relic SSO” security group in Entra ID (Azure AD) and then removes that user from New Relic via GraphQL, follow these steps:

Architecture Overview
1.	Trigger: The function is triggered by an Azure Event Grid event when a user is removed from the “New Relic SSO” security group in Entra ID.
2.	Processing: The function extracts the user’s Object ID (UUID) and looks up the corresponding email from Azure AD.
3.	GraphQL Execution: The function makes a GraphQL request to remove the user from New Relic.

Steps to Set Up in Azure
1.	Enable Azure Event Grid for security group changes in Entra ID.
2.	Deploy the function app to Azure using Python.
3.	Set environment variables in Azure Functions for:
  -	NEW_RELIC_API_KEY
  -	TENANT_ID
  -	CLIENT_ID
  -	CLIENT_SECRET

Python Code for the Azure Function

This function:
-	Is triggered by an Event Grid event.
-	Queries Microsoft Graph API to get the user’s email.
-	Calls New Relic GraphQL API to delete the user.

Create a new function (remove_new_relic_user.py)

```python
import os
import json
import logging
import requests
import azure.functions as func
from msal import ConfidentialClientApplication

# Environment variables (Set these in Azure Function App Configuration)
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_API_KEY")
GRAPHQL_URL = "https://api.newrelic.com/graphql"

# Microsoft Graph API URL
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

def get_graph_api_token():
    """Authenticate with Microsoft Graph API using client credentials"""
    app = ConfidentialClientApplication(
        CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in token_response:
        return token_response["access_token"]
    else:
        logging.error(f"Error obtaining Graph API token: {token_response.get('error_description')}")
        return None

def get_user_email(user_id, access_token):
    """Fetch the user's email address from Entra ID (Azure AD)"""
    url = f"{GRAPH_API_BASE}/users/{user_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("mail")
    else:
        logging.error(f"Failed to get user email: {response.text}")
        return None

def remove_user_from_new_relic(email):
    """GraphQL mutation to remove the user from New Relic"""
    query = """
    mutation {
      userManagementDeleteUser(email: "%s") {
        success
        error {
          message
        }
      }
    }
    """ % email

    headers = {
        "Content-Type": "application/json",
        "API-Key": NEW_RELIC_API_KEY
    }
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)
    data = response.json()
    
    if "errors" in data:
        logging.error(f"GraphQL Error: {data['errors']}")
        return False
    else:
        result = data.get("data", {}).get("userManagementDeleteUser", {})
        if result.get("success"):
            logging.info(f"User {email} successfully removed from New Relic.")
            return True
        else:
            logging.error(f"Failed to remove user: {result.get('error', {}).get('message', 'Unknown error')}")
            return False

def main(event: func.EventGridEvent):
    """Azure Function triggered when a user is removed from the 'New Relic SSO' group"""
    logging.info("Received event: %s", event.get_json())
    
    data = event.get_json()
    user_id = data.get("subject").split("/")[-1]  # Extract user ID from the event payload
    
    if not user_id:
        logging.error("No user ID found in the event payload.")
        return func.HttpResponse("Invalid event format", status_code=400)

    # Get Access Token for Microsoft Graph API
    access_token = get_graph_api_token()
    if not access_token:
        return func.HttpResponse("Failed to authenticate with Microsoft Graph API", status_code=500)

    # Retrieve the user's email from Entra ID
    email = get_user_email(user_id, access_token)
    if not email:
        return func.HttpResponse("Failed to fetch user email", status_code=500)

    # Remove the user from New Relic
    if remove_user_from_new_relic(email):
        return func.HttpResponse(f"User {email} removed from New Relic.", status_code=200)
    else:
        return func.HttpResponse(f"Failed to remove user {email} from New Relic.", status_code=500)
```

How This Works
1.	Triggered by an Event Grid event when a user is removed from the “New Relic SSO” security group.
2.	Extracts user ID from the event.
3.	Gets user’s email from Azure AD using the Microsoft Graph API.
4.	Calls New Relic GraphQL API to remove the user.
5.	Logs success or failure.

Deployment Steps
1.	Create an Azure Function App in Python.
2.	Set up an Event Grid Subscription for Entra ID group membership changes.
3.	Configure App Settings with:
  -	TENANT_ID
  -	CLIENT_ID
  -	CLIENT_SECRET
  -	NEW_RELIC_API_KEY
4.	Deploy the function using Azure CLI or VS Code.

Testing
1.	Remove a user from the New Relic SSO group in Entra ID.
2.	Check the function logs in Azure Monitor.
3.	Verify that the user is removed from New Relic.

Next Steps
-	Enhance error handling for edge cases.
-	Log failures to Azure Application Insights for tracking.
-	Optionally notify an admin via email when a removal fails.

This function ensures that when a user loses access to New Relic SSO, they are also removed from New Relic, maintaining security compliance. 🚀