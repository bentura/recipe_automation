import os
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "recipe_processor.log")

# Ensure log directory exists (though monitor_service should create it)
os.makedirs(LOG_DIR, exist_ok=True)

@app.route('/')
def index():
    log_content = "No log file found yet."
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            log_content = f.read()
    
    # Simple parsing for display: split by lines and reverse to show latest first
    log_lines = log_content.splitlines()
    display_logs = [line for line in log_lines if line.strip()] # Filter empty lines
    display_logs.reverse() # Show newest first

    return render_template('index.html', logs=display_logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
