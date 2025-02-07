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