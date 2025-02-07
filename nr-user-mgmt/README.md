To accomplish this, we’ll create an Azure Function that is triggered by changes to an Azure AD Security Group. The function will be triggered whenever a user is added or removed from the “New Relic SSO” security group.

Steps:
	1.	Use an Event Grid Subscription to monitor changes in Azure AD Security Groups.
	2.	Create an Azure Function that listens for Event Grid events and runs a Python script.
	3.	Deploy the function to Azure and configure it to run when the group changes.

1. Prerequisites

Ensure you have:
	•	An Azure subscription.
	•	An Azure AD Security Group named “New Relic SSO”.
	•	Azure CLI installed and authenticated (az login).
	•	Azure Function Core Tools installed.
	•	Python 3.8+ installed.

2. Create the Azure Function

Here’s a Python script for an Azure Function that:
	•	Listens to Event Grid events related to the New Relic SSO security group.
	•	Executes a Python script when a user is added/removed.

Python Script (function_app.py)

```bash
import logging
import json
import azure.functions as func

def main(event: func.EventGridEvent):
    logging.info('Received an event: %s', event.get_json())

    event_data = event.get_json()

    # Check if this event is for the "New Relic SSO" Security Group
    if "New Relic SSO" in event_data.get("subject", ""):
        operation = event_data.get("data", {}).get("operationType", "")

        if operation == "AddMember":
            logging.info("User added to the Security Group: New Relic SSO")
            # Execute custom logic (e.g., call external API, update system)
        elif operation == "RemoveMember":
            logging.info("User removed from the Security Group: New Relic SSO")
            # Execute custom logic
        else:
            logging.info("Unhandled operation: %s", operation)

    return func.HttpResponse("Processed event successfully.", status_code=200)
```

3. Deploy the Function to Azure

Step 1: Create the Azure Function App

```bash
# Set environment variables
RESOURCE_GROUP="MyResourceGroup"
FUNCTION_APP_NAME="NewRelicGroupWatcher"
STORAGE_ACCOUNT_NAME="newrelicfuncstorage"
LOCATION="eastus"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a storage account
az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP --sku Standard_LRS

# Create the function app
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version 3.8 \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_ACCOUNT_NAME
```

4. Configure Event Grid to Monitor the Security Group

We need to subscribe the Azure Function to Azure AD Group change events.

Step 1: Get the Security Group ID

```bash
GROUP_NAME="New Relic SSO"
GROUP_ID=$(az ad group show --group "$GROUP_NAME" --query id -o tsv)
echo "Group ID: $GROUP_ID"
```

Step 2: Create the Event Grid Subscription

```bash
EVENT_GRID_SUB_NAME="NewRelicGroupEvents"

az eventgrid event-subscription create \
    --name $EVENT_GRID_SUB_NAME \
    --source-resource-id "/providers/Microsoft.Entra/groups/$GROUP_ID" \
    --endpoint-type azurefunction \
    --endpoint "/subscriptions/{subscriptionId}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME/functions/EventGridTrigger1"
```

5. Deploy the Code

```bash
# Initialize Function App locally
func init --worker-runtime python

# Add required dependencies
pip install azure-functions --target=".python_packages/lib/site-packages"

# Deploy function to Azure
func azure functionapp publish $FUNCTION_APP_NAME
```

6. Testing
	•	Add or remove a user from “New Relic SSO”.
	•	Check Azure Function logs:

```bash
az functionapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP
```


This setup ensures that whenever a user is added or removed from “New Relic SSO”, an Azure Function runs a Python script to process the event. 🚀