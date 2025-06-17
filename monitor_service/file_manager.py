# monitor_service/file_manager.py
import os
import shutil
import json
import logging

logger = logging.getLogger(__name__)

def save_json_file(json_data, output_path):
    """Saves a Python dictionary as a pretty-printed JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {output_path}: {e}")

def load_json_file(input_path):
    """Loads a JSON file from the given path and returns its content as a dictionary."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"JSON loaded from {input_path}")
        return data
    except FileNotFoundError:
        logger.error(f"JSON file not found at {input_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {input_path}: {e}")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading JSON from {input_path}: {e}")
        return None

def move_to_archive(source_path, archive_dir, success=True):
    """Moves a processed file to the archive directory, adding a status prefix."""
    file_name = os.path.basename(source_path)
    status_prefix = "SUCCESS_" if success else "FAILED_"
    destination_path = os.path.join(archive_dir, status_prefix + file_name)
    try:
        shutil.move(source_path, destination_path)
        logger.info(f"Moved {file_name} to archive: {destination_path}")
    except Exception as e:
        logger.error(f"Failed to move {file_name} to archive: {e}")
