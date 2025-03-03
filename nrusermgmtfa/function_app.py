import logging
import json
import azure.functions as func

def main(event: func.EventGridEvent):
    """Azure Function triggered by an Event Grid event when users are added or removed from the 'NrSSO' group."""
    logging.info("Received Event Grid event: %s", event.get_json())
    
    # Extract data from the event
    data = event.get_json()
    event_type = data.get("eventType", "")
    user_display_name = data.get("subject", "Unknown User").split("/")[-1]  # Extract user name from subject
    group_name = data.get("data", {}).get("groupName", "")
    
    # Check if the event is related to 'NrSSO' security group
    if group_name == "NrSSO":
        if "UserAddedToGroup" in event_type:
            logging.info(f"{user_display_name} was added to NrSSO group")
        elif "UserRemovedFromGroup" in event_type:
            logging.info(f"{user_display_name} was removed from NrSSO group")
        else:
            logging.warning(f"Unhandled event type: {event_type}")
    else:
        logging.info("Event is not related to NrSSO group, ignoring.")