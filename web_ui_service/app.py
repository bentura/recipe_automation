import os
from flask import Flask, render_template, jsonify, request # Import request
import logging
from datetime import datetime # For unique filenames

app = Flask(__name__)

LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "recipe_processor.log")
INPUT_DIR = "/app/input" # Needs to be accessible by Flask for saving uploads

# Ensure directories exist (Flask app might also start first)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True) # Ensure input dir is created by web_ui as well

app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

@app.route('/')
def index():
    # Initial load of logs
    log_content = "No log file found yet."
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except Exception as e:
            app.logger.error(f"Error reading log file for initial load: {e}")
            log_content = f"Error loading logs: {e}"
    
    log_lines = log_content.splitlines()
    display_logs = [line for line in log_lines if line.strip()]
    display_logs.reverse() # Show newest first for initial load

    return render_template('index.html', logs=display_logs)

@app.route('/api/logs')
def get_logs_api():
    # ... (No change to this function, it's correct) ...
    # This function reads and combines content from the main log file and all rotated backup files.
    all_log_files = []
    
    # Add the current active log file first
    if os.path.exists(LOG_FILE):
        all_log_files.append(LOG_FILE)
    
    # Find all rotated log files (e.g., recipe_processor.log.1, recipe_processor.log.2)
    log_file_base = os.path.basename(LOG_FILE)
    # Corrected path for os.listdir if LOG_FILE is just a name
    log_dir_path = os.path.dirname(LOG_FILE) or LOG_DIR 
    import re # Ensure re is imported if not already globally
    
    for f_name in os.listdir(log_dir_path):
        if re.match(rf"^{re.escape(log_file_base)}\.\d+$", f_name): # Matches "filename.N"
            full_path = os.path.join(log_dir_path, f_name)
            all_log_files.append(full_path)
            
    # Sort files to ensure chronological order:
    def sort_key(path):
        match = re.search(r'\.(\d+)$', path)
        if match:
            return int(match.group(1)) # Sort backups by number
        return -1 # Ensure current log file (-1) comes after all backups (0, 1, 2...)

    all_log_files.sort(key=sort_key) 

    combined_content = []
    for log_path in all_log_files:
        if os.path.exists(log_path): 
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    combined_content.append(f.read())
            except Exception as e:
                app.logger.error(f"Error reading log file {log_path}: {e}")
    
    return jsonify(log_content="".join(combined_content))


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        app.logger.warning("No 'photo' file part in upload request.")
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['photo']
    if file.filename == '':
        app.logger.warning("No selected file in upload request.")
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        # Create a unique filename to avoid conflicts and ensure monitor picks it up
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Add microseconds for more uniqueness
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        
        # Limit filename length and sanitize
        safe_filename = "".join(c for c in os.path.splitext(original_filename)[0] if c.isalnum() or c in (' ', '.', '_')).rstrip()
        if len(safe_filename) > 50: # Limit base name length
            safe_filename = safe_filename[:50]
            
        unique_filename = f"webcam_recipe_{safe_filename}_{timestamp}{file_extension}"
        destination_path = os.path.join(INPUT_DIR, unique_filename)
        
        try:
            file.save(destination_path)
            app.logger.info(f"Received and saved uploaded photo: {destination_path}")
            # The monitor_service should automatically pick this up
            return jsonify({"status": "success", "message": "Photo uploaded successfully", "filename": unique_filename}), 200
        except Exception as e:
            app.logger.error(f"Error saving uploaded photo {destination_path}: {e}")
            return jsonify({"status": "error", "message": f"Failed to save photo: {e}"}), 500
    
    return jsonify({"status": "error", "message": "Unknown error during upload"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
