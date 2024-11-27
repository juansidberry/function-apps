import os
import subprocess
import json
import logging
import requests
import azure.functions as func

# Step 1: Describe Kafka consumer group
def describe_consumer_group(group_name, bootstrap_servers, kafka_path):
    command = f"{kafka_path}/bin/kafka-consumer-groups.sh --bootstrap-server {bootstrap_servers} --describe --group {group_name}"
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        with open("/tmp/consumer_group_status.txt", "w") as file:
            file.write(output)
        logging.info("Consumer group description saved to /tmp/consumer_group_status.txt")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running kafka-consumer-groups.sh: {e.output}")
        raise

# Step 2: Parse consumer_group_status.txt and extract CONSUMER-ID
def extract_consumer_ids(file_path):
    consumer_ids = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "CONSUMER-ID" in line:
                    continue  # Skip header
                parts = line.split()
                if len(parts) > 0:
                    consumer_ids.append(parts[0])  # Assuming CONSUMER-ID is the first column
        logging.info(f"Extracted CONSUMER-ID values: {consumer_ids}")
        return consumer_ids
    except FileNotFoundError:
        logging.error("File not found. Please ensure the file path is correct.")
        raise

# Step 3: Send CONSUMER-ID values to New Relic
def send_to_new_relic(consumer_ids, api_key, account_id):
    url = f"https://insights-collector.newrelic.com/v1/accounts/{account_id}/events"
    headers = {
        "Content-Type": "application/json",
        "X-Insert-Key": api_key,
    }

    payload = [
        {
            "eventType": "KafkaConsumerID",
            "consumer_id": consumer_id,
        }
        for consumer_id in consumer_ids
    ]

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            logging.info("Successfully sent consumer IDs to New Relic.")
        else:
            logging.error(f"Failed to send data to New Relic: {response.status_code} {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error sending data to New Relic: {e}")
        raise

# Azure Function Entry Point
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request...")

    try:
        # Environment variables for configuration
        kafka_path = os.getenv("KAFKA_PATH", "/home/site/wwwroot/kafka-binaries")
        group_name = os.getenv("KAFKA_GROUP_NAME", "default_group")
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        new_relic_api_key = os.getenv("NEW_RELIC_API_KEY", "")
        new_relic_account_id = os.getenv("NEW_RELIC_ACCOUNT_ID", "")

        if not new_relic_api_key or not new_relic_account_id:
            return func.HttpResponse("New Relic API Key and Account ID must be set.", status_code=500)

        # Step 1: Describe consumer group
        describe_consumer_group(group_name, bootstrap_servers, kafka_path)

        # Step 2: Extract CONSUMER-ID values
        consumer_ids = extract_consumer_ids("/tmp/consumer_group_status.txt")

        # Step 3: Send to New Relic
        if consumer_ids:
            send_to_new_relic(consumer_ids, new_relic_api_key, new_relic_account_id)
            return func.HttpResponse(f"Successfully sent {len(consumer_ids)} CONSUMER-ID values to New Relic.", status_code=200)
        else:
            return func.HttpResponse("No CONSUMER-ID values found.", status_code=404)

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
