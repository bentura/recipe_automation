import requests
import os
import logging

logger = logging.getLogger(__name__)

def send_pushover_notification(message, title="Recipe Automation Status", priority=0):
    """
    Sends a notification to Pushover.

    Args:
        message (str): The main message content.
        title (str): The title of the notification. Defaults to "Recipe Automation Status".
        priority (int): Notification priority (-2 to 2).
                        -2: lowest, -1: low, 0: normal, 1: high, 2: emergency.
                        Emergency (2) requires a 'retry' and 'expire' parameter.
    """
    user_key = os.getenv("PUSHOVER_USER_KEY")
    api_token = os.getenv("PUSHOVER_API_TOKEN")

    if not user_key or not api_token:
        logger.error("Pushover User Key or API Token is not set in environment variables.")
        return False

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": api_token,
        "user": user_key,
        "message": message,
        "title": title,
        "priority": priority
    }

    # For emergency priority (priority=2), you might add:
    # payload["retry"] = 30 # Retry every 30 seconds
    # payload["expire"] = 3600 # Expire after 1 hour if not acknowledged

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        
        result = response.json()
        if result.get("status") == 1:
            logger.info(f"Pushover notification sent successfully: '{message}'")
            return True
        else:
            logger.error(f"Pushover notification failed. Response: {result.get('errors', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Pushover notification: {e}")
        return False

if __name__ == '__main__':
    # --- Example Usage (for local testing) ---
    # In a real Docker setup, these would come from .env
    # import os
    # os.environ["PUSHOVER_USER_KEY"] = "YOUR_U_KEY"
    # os.environ["PUSHOVER_API_TOKEN"] = "YOUR_A_TOKEN"

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("Attempting to send test Pushover notification...")
    success = send_pushover_notification("Test notification from Recipe Automation!", "Test Message")
    if success:
        print("Notification sent!")
    else:
        print("Notification failed!")
