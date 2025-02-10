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