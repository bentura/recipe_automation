import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from datetime import datetime

import ocr_utils
import llm_processor
import file_manager
import post_processor
import notifier
import api_sender 

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"
ARCHIVE_DIR = "/app/archive"
LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "recipe_processor.log")

# Log Rotation Configuration
MAX_LOG_SIZE_MB = 5  # Max size of each log file in MB
BACKUP_LOG_COUNT = 3 # Number of backup log files to keep

# API Configuration (will be read from .env)
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://192.168.68.62:8002/api/recipe/") # Default or override in .env
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN") # NEW: Bearer Token

# Ensure directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Logging Setup ---
print(f"DEBUG: Attempting to configure logging to file: {LOG_FILE} with rotation.")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # Use RotatingFileHandler instead of FileHandler
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024, # Convert MB to bytes
            backupCount=BACKUP_LOG_COUNT,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RecipeFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        file_name = os.path.basename(file_path)
        logger.info(f"Detected new file: {file_name}")

        time.sleep(2) # Give file time to fully copy

        try:
            # 1. Extract Text (using Vision AI now)
            if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raw_text = ocr_utils.extract_text_from_image(file_path)
            elif file_name.lower().endswith('.pdf'):
                raw_text = ocr_utils.extract_text_from_pdf(file_path)
            else:
                logger.warning(f"Skipping unsupported file type: {file_name}")
                file_manager.move_to_archive(file_path, ARCHIVE_DIR, success=False)
                return

            if not raw_text.strip():
                logger.error(f"No text extracted from {file_name}. Skipping LLM processing.")
                file_manager.move_to_archive(file_path, ARCHIVE_DIR, success=False)
                return

            logger.info(f"Text extracted from {file_name}. Proceeding to LLM conversion(s)...")

            # --- Create timestamped output subfolder ---
            now_bst = datetime.now() 
            timestamp_folder_name = now_bst.strftime("%Y-%m-%d_%H%M%S")
            
            current_output_sub_dir = os.path.join(OUTPUT_DIR, timestamp_folder_name)
            os.makedirs(current_output_sub_dir, exist_ok=True)
            logger.info(f"Created output subfolder: {current_output_sub_dir}")
            # --- End timestamped subfolder setup ---

            # Save raw OCR text for debugging (now goes into the timestamped folder)
            raw_text_output_file = os.path.join(current_output_sub_dir, os.path.splitext(file_name)[0] + "_raw_ocr.txt")
            logger.debug(f"Attempting to save raw OCR text to: {raw_text_output_file}")
            with open(raw_text_output_file, 'w', encoding='utf-8') as f:
                f.write(raw_text)
            logger.info(f"Raw OCR text saved to: {raw_text_output_file}")


            # Flag to track if API send was attempted and successful
            api_send_successful = False # Initialize to False

            # 2. Process with LLM for Schema.org
            logger.info("Generating Schema.org JSON...")
            schema_org_json_output = llm_processor.get_schema_org_json(raw_text)
            
            if schema_org_json_output:
                schema_org_output_path = os.path.join(current_output_sub_dir, "schema_org_recipe.json")
                file_manager.save_json_file(schema_org_json_output, schema_org_output_path)
                logger.info(f"Successfully generated and saved Schema.org JSON.")
            else:
                logger.error("Failed to generate Schema.org JSON.")
                notifier.send_pushover_notification(f"ERROR: Failed to generate Schema.org JSON for '{file_name}'", title="Recipe Conversion Failed", priority=1)


            # 3. Process with LLM for createRecipe (Intermediate)
            logger.info("Generating createRecipe (intermediate) JSON...")
            create_recipe_intermediate_json_output = llm_processor.get_create_recipe_json_intermediate(raw_text)

            create_recipe_output_path = os.path.join(current_output_sub_dir, "create_recipe_intermediate.json")
            if create_recipe_intermediate_json_output:
                file_manager.save_json_file(create_recipe_intermediate_json_output, create_recipe_output_path)
                logger.info(f"Successfully generated and saved createRecipe (intermediate) JSON.")
                
                # --- CALL POST-PROCESSING HERE, PASSING NOTIFIER ---
                logger.info("Starting post-processing for createRecipe JSON and anomaly checks...")
                post_process_success = post_processor.post_process_create_recipe_json(
                    create_recipe_output_path,
                    send_notification_func=notifier.send_pushover_notification # Pass the Pushover function
                )
                if post_process_success:
                    logger.info("createRecipe JSON post-processing completed successfully.")
                    
                    # --- NEW: Send to External API after post-processing ---
                    logger.info("Attempting to send processed createRecipe JSON to external API...")
                    # Load the JSON from disk again to ensure post-processing changes are included
                    loaded_processed_json = file_manager.load_json_file(create_recipe_output_path) 
                    if loaded_processed_json: # Ensure file was loaded correctly
                        api_send_successful = api_sender.send_recipe_to_api(
                            recipe_json_data=loaded_processed_json, 
                            api_url=API_ENDPOINT,
                            bearer_token=API_BEARER_TOKEN, # Pass Bearer Token
                            send_notification_func=notifier.send_pushover_notification,
                            original_file_name=file_name
                        )
                    else:
                        api_send_successful = False # Set to False if loading failed
                        logger.error(f"Could not load post-processed JSON for '{file_name}' to send to API. API send skipped.")
                        notifier.send_pushover_notification(f"ERROR: Could not load post-processed JSON for '{file_name}' to send to API.", title="API Send Skipped", priority=1)

                    if api_send_successful:
                        logger.info(f"Successfully sent '{file_name}' to external API.")
                    else:
                        logger.error(f"Failed to send '{file_name}' to external API. Check logs/Pushover for details.")
                    # --- END NEW ---

                else:
                    logger.warning("createRecipe JSON post-processing encountered issues. Check logs for details.")
                    notifier.send_pushover_notification(f"WARNING: Post-processing issues for '{file_name}'. Check logs!", title="Recipe Post-Processing Issue", priority=1)
            else:
                logger.error(f"Failed to generate createRecipe (intermediate) JSON.")
                notifier.send_pushover_notification(f"ERROR: Failed to generate createRecipe JSON for '{file_name}'", title="Recipe Conversion Failed", priority=1)


            # 4. Move original file to archive
            # Decide overall success based on at least one JSON being generated AND API send success (if attempted for createRecipe)
            overall_success = bool(schema_org_json_output or (create_recipe_intermediate_json_output and api_send_successful)) 
            file_manager.move_to_archive(file_path, ARCHIVE_DIR, success=overall_success)
            if overall_success:
                notifier.send_pushover_notification(f"'{file_name}' processed (JSONs generated & API sent).", title="Recipe Processed Successfully", priority=-1) # Low priority success
            else:
                 notifier.send_pushover_notification(f"CRITICAL: Failed to process '{file_name}'. Check logs!", title="Recipe Processing Failed CRITICAL", priority=2) # Emergency priority for full failure


        except Exception as e:
            logger.exception(f"CRITICAL SYSTEM ERROR during processing of '{file_name}': {e}")
            notifier.send_pushover_notification(f"CRITICAL SYSTEM ERROR: Processing '{file_name}' failed. Details in logs!", title="Recipe Processing Critical Error", priority=2)
            file_manager.move_to_archive(file_path, ARCHIVE_DIR, success=False)

if __name__ == "__main__":
    logger.info(f"Starting recipe monitor for {INPUT_DIR}...")
    event_handler = RecipeFileHandler()
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    logger.info("Recipe monitor stopped.")
