import json
import logging
import os

logger = logging.getLogger(__name__)

# --- Define culinary knowledge base for potential anomalies ---
SPICE_ANOMALY_THRESHOLDS = {
    "cayenne pepper": {"unit_keywords": ["tbsp", "tablespoon"], "amount_threshold": 0.5, "suggested_unit": "tsp"},
    "hot curry powder": {"unit_keywords": ["tbsp", "tablespoon"], "amount_threshold": 1.0, "suggested_unit": "tsp"},
    "chilli powder": {"unit_keywords": ["tbsp", "tablespoon"], "amount_threshold": 1.5, "suggested_unit": "tsp"},
    "saffron": {"unit_keywords": ["g", "gram", "ml", "cup", "tsp", "teaspoon", "tbsp", "tablespoon"], "amount_threshold": 0.5, "suggested_unit": "pinch"}, # Saffron is very potent/expensive
    # Add more spices/herbs and their max sensible amounts here
}
# --- END NEW ---


def check_ingredient_anomalies(recipe_data):
    """
    Checks for potentially anomalous ingredient amounts and returns a list of warning messages.
    """
    warnings = []
    
    if "steps" not in recipe_data:
        return warnings

    for step_index, step in enumerate(recipe_data["steps"]):
        if "ingredients" in step and step["ingredients"] is not None:
            for ing_index, ingredient in enumerate(step["ingredients"]):
                food_name = ingredient.get("food", {}).get("name", "").lower()
                unit_name = ingredient.get("unit", {}).get("name", "").lower()
                amount_str = ingredient.get("amount") # Amount is a string from LLM output

                if not food_name or not amount_str:
                    continue # Skip if essential info is missing

                try:
                    amount_val = float(amount_str) # Convert amount to float for comparison
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert amount '{amount_str}' to float for validation. Skipping anomaly check for this ingredient.")
                    continue

                for spice, thresholds in SPICE_ANOMALY_THRESHOLDS.items():
                    if spice in food_name: # Check if the spice name is part of the food name
                        is_unit_problematic = any(keyword in unit_name for keyword in thresholds["unit_keywords"])
                        
                        if is_unit_problematic and amount_val >= thresholds["amount_threshold"]:
                            warning_message = (
                                f"Possible anomaly in Step {step_index + 1}, Ingredient {ing_index + 1} ({food_name}): "
                                f"Amount '{amount_str} {unit_name}' seems unusually high. "
                                f"Consider if '{thresholds['suggested_unit']}' was intended."
                            )
                            warnings.append(warning_message)
                            logger.warning(warning_message)
                        break # Stop checking other spices for this ingredient once a match is found
    return warnings


def post_process_create_recipe_json(json_file_path, send_notification_func=None):
    """
    Reads the intermediate createRecipe JSON, modifies servings_text if needed,
    and checks for ingredient anomalies, sending notifications if provided.

    Args:
        json_file_path (str): Path to the JSON file to process.
        send_notification_func (callable, optional): A function to call to send notifications
                                                      (e.g., notifier.send_pushover_notification).
                                                      It should accept (message, title, priority).
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            recipe_data = json.load(f)

        recipe_name = recipe_data.get("name", "Unknown Recipe")

        # 1. Process servings_text for character limit
        if "servings_text" in recipe_data and recipe_data["servings_text"] is not None:
            original_servings_text = str(recipe_data["servings_text"])
            if len(original_servings_text) > 32:
                recipe_data["servings_text"] = "empty"
                logger.info(f"Servings text '{original_servings_text}' exceeded 32 chars. Set to 'empty' for {os.path.basename(json_file_path)}")
                if send_notification_func:
                    send_notification_func(
                        message=f"Servings text for '{recipe_name}' too long (>32 chars). Set to 'empty'.",
                        title="Recipe Anomaly: Servings Text",
                        priority=0
                    )
            else:
                logger.debug(f"Servings text '{original_servings_text}' is within limits.")
        else:
            logger.debug(f"No servings_text found or it's null for {os.path.basename(json_file_path)}")

        # 2. Check for ingredient anomalies
        anomalies = check_ingredient_anomalies(recipe_data)
        if anomalies:
            logger.warning(f"Detected {len(anomalies)} potential ingredient anomalies for {os.path.basename(json_file_path)}")
            if send_notification_func:
                anomaly_title = f"Recipe Anomaly: '{recipe_name}'"
                anomaly_message = f"Detected {len(anomalies)} potential ingredient anomaly(s) in:\n" + "\n".join(anomalies)
                send_notification_func(
                    message=anomaly_message,
                    title=anomaly_title,
                    priority=1 # High priority for potential recipe issues
                )
        else:
            logger.info(f"No ingredient anomalies detected for {os.path.basename(json_file_path)}")

        # --- IMPORTANT: We NO LONGER add 'warnings' field to JSON output ---
        # Save the modified JSON back to the same path
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(recipe_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Post-processing complete for {os.path.basename(json_file_path)}")
        return True

    except FileNotFoundError:
        logger.error(f"Post-processing failed: JSON file not found at {json_file_path}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Post-processing failed: Invalid JSON in {json_file_path}: {e}")
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during post-processing of {json_file_path}: {e}")
        return False
