import requests
import time
import threading
import os
import datetime
import signal
import sys
import logging

# --- Configuration ---

# Directory where images will be saved. Subdirectories will be created for each camera.
SAVE_DIR = "camera_images"

# List of cameras to poll. Each camera is a dictionary with:
# 'name': A unique name for the camera (used for directory and filenames).
# 'url': The full URL to fetch the static image from.
# 'interval': The polling interval in seconds (how often to fetch the image).
CAMERAS = [
    {
        'name': 'Front Door',
        'url': 'https://example.com/FrontDoor.JPG', # Replace with actual URL
        'interval': 60  # Poll every 60 seconds
    },
    {
        'name': 'Pool',
        'url': 'https://example.com/Pool.jpg', # Replace with actual URL
        'interval': 30  # Poll every 30 seconds
    },
    # --- Add more cameras here ---
    # {
    #     'name': 'Garage',
    #     'url': 'http://garage_cam/img/snapshot.cgi',
    #     'interval': 90
    # },
]

# Timeout for network requests in seconds
REQUEST_TIMEOUT = 15

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(threadName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Global flag for graceful shutdown ---
shutdown_event = threading.Event()

# --- Functions ---

def setup_directories():
    """Creates the main save directory and subdirectories for each camera."""
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        logging.info(f"Main save directory: '{SAVE_DIR}'")
        for cam in CAMERAS:
            cam_dir = os.path.join(SAVE_DIR, cam['name'])
            os.makedirs(cam_dir, exist_ok=True)
            logging.info(f"Ensured directory exists for camera '{cam['name']}': '{cam_dir}'")
    except OSError as e:
        logging.error(f"Error creating directories: {e}")
        sys.exit(1) # Exit if we can't create directories

def get_file_extension(response):
    """Attempts to determine the file extension from the Content-Type header."""
    content_type = response.headers.get('content-type')
    if content_type:
        if 'image/jpeg' in content_type.lower():
            return '.jpg'
        elif 'image/png' in content_type.lower():
            return '.png'
        elif 'image/gif' in content_type.lower():
            return '.gif'
        elif 'image/bmp' in content_type.lower():
            return '.bmp'
    # Default if unknown or header is missing
    logging.warning("Could not determine image type from headers, defaulting to .jpg")
    return '.jpg'

def fetch_and_save(camera_config):
    """Fetches image from a camera URL and saves it."""
    name = camera_config['name']
    url = camera_config['url']
    interval = camera_config['interval']
    cam_dir = os.path.join(SAVE_DIR, name)

    logging.info(f"Starting polling for camera: '{name}' (Interval: {interval}s)")

    while not shutdown_event.is_set():
        next_fetch_time = time.monotonic() + interval
        try:
            logging.debug(f"[{name}] Fetching image from {url}")
            response = requests.get(url, timeout=REQUEST_TIMEOUT, stream=False)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            # Determine filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = get_file_extension(response)
            filename = f"{name}_{timestamp}{extension}"
            filepath = os.path.join(cam_dir, filename)

            # Save image content
            with open(filepath, 'wb') as f:
                f.write(response.content)
            logging.info(f"[{name}] Saved image to {filepath}")

        except requests.exceptions.Timeout:
            logging.error(f"[{name}] Timeout error fetching image from {url}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[{name}] Error fetching image from {url}: {e}")
        except OSError as e:
            logging.error(f"[{name}] Error saving image to {filepath}: {e}")
        except Exception as e:
            logging.error(f"[{name}] An unexpected error occurred: {e}")

        # Wait until the next scheduled fetch time, accounting for download/save time
        # Use shutdown_event.wait for interruptible sleep
        sleep_duration = max(0, next_fetch_time - time.monotonic())
        logging.debug(f"[{name}] Sleeping for {sleep_duration:.2f} seconds...")
        shutdown_event.wait(sleep_duration) # Wait here, but break if shutdown is signaled

    logging.info(f"Polling stopped for camera: '{name}'")


def signal_handler(sig, frame):
    """Handles termination signals like Ctrl+C."""
    logging.warning(f"Signal {sig} received. Initiating shutdown...")
    shutdown_event.set() # Signal all threads to stop

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting camera polling script...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Handle termination signals

    setup_directories()

    threads = []
    for cam_info in CAMERAS:
        # Create and start a thread for each camera
        # Pass the camera config dictionary to the target function
        thread = threading.Thread(
            target=fetch_and_save,
            args=(cam_info,),
            name=f"CamThread-{cam_info['name']}", # Give threads meaningful names
            daemon=False # Important: Non-daemon threads keep main alive until they finish
        )
        threads.append(thread)
        thread.start()

    logging.info(f"Started {len(threads)} camera polling threads.")

    # Keep the main thread alive while worker threads run
    # The main thread will exit when all non-daemon threads complete
    # Or wait for the shutdown signal
    try:
        # Optional: Check thread health periodically (can be complex)
        while not shutdown_event.is_set():
           time.sleep(1) # Keep main thread responsive to signals

    except Exception as e:
       logging.error(f"Error in main loop: {e}")
    finally:
       logging.info("Shutdown signal received. Waiting for threads to complete...")
       # Wait for all threads to finish their current loop iteration and exit
       for thread in threads:
           thread.join() # Wait for each thread to finish
       logging.info("All camera threads finished. Exiting.")
       sys.exit(0)
