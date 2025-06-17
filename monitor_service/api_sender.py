import requests
import json
import logging
import os

logger = logging.getLogger(__name__)

def send_recipe_to_api(recipe_json_data, api_url, bearer_token, send_notification_func=None, original_file_name="Unknown"):
    """
    Sends the recipe JSON data as a POST request to a specified API endpoint with Bearer Token Authentication.

    Args:
        recipe_json_data (dict): The dictionary containing the recipe data.
        api_url (str): The URL of the API endpoint.
        bearer_token (str): The Bearer Token for authentication.
        send_notification_func (callable, optional): Function to send notifications (e.g., Pushover).
        original_file_name (str): The name of the original processed file for logging/notifications.

    Returns:
        bool: True if the request was successful (2xx status code), False otherwise.
    """
    if not api_url or not bearer_token:
        logger.error("API URL or Bearer Token is not configured for sending recipe data. Check .env.")
        if send_notification_func:
            send_notification_func(
                message=f"API Sender Config Error: API URL/Bearer Token missing for '{original_file_name}'. Check .env.",
                title="API Send Failed: Config",
                priority=1
            )
        return False

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json", # Request JSON response
        "Authorization": f"Bearer {bearer_token}" # Bearer Token header
    }
    
    try:
        # Convert dict to JSON string
        json_payload = json.dumps(recipe_json_data, indent=2)
        
        logger.info(f"Attempting to send recipe JSON for '{original_file_name}' to API: {api_url}")
        logger.debug(f"JSON Payload: {json_payload}")

        # --- IMPORTANT: Removed auth parameter for requests.post() ---
        response = requests.post(api_url, data=json_payload, headers=headers)
        response.raise_for_status() # Raises an HTTPError for 4xx/5xx responses

        logger.info(f"Successfully sent recipe JSON for '{original_file_name}'. Status: {response.status_code}")
        logger.debug(f"API Response: {response.text}")
        if send_notification_func:
            send_notification_func(
                message=f"'{original_file_name}' sent to API. Status: {response.status_code}",
                title="Recipe Sent to API",
                priority=-1
            )
        return True

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "N/A"
        response_text = e.response.text if e.response else "No response body"
        logger.error(f"HTTP Error sending recipe JSON for '{original_file_name}' to API: {e}. Status: {status_code}. Response: {response_text}")
        if send_notification_func:
            send_notification_func(
                message=f"API Send FAILED for '{original_file_name}'. HTTP Error {status_code}. Check logs.",
                title="API Send Failed: HTTP",
                priority=1
            )
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error sending recipe JSON for '{original_file_name}' to API: {e}. Is API running at {api_url}?")
        if send_notification_func:
            send_notification_func(
                message=f"API Send FAILED for '{original_file_name}'. Connection Error. Is API running?",
                title="API Send Failed: Connection",
                priority=2 # High priority for connection issues
            )
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error sending recipe JSON for '{original_file_name}' to API: {e}")
        if send_notification_func:
            send_notification_func(
                message=f"API Send FAILED for '{original_file_name}'. Timeout. Check API.",
                title="API Send Failed: Timeout",
                priority=1
            )
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred while sending recipe JSON for '{original_file_name}' to API: {e}")
        if send_notification_func:
            send_notification_func(
                message=f"API Send FAILED for '{original_file_name}'. Unexpected Error. Check logs.",
                title="API Send Failed: Unexpected",
                priority=2
            )
        return False
