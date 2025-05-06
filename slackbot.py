import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Regular expression pattern for license plates (customize based on your region's format)
# This is a general pattern - you might want to adjust for specific formats
LICENSE_PLATE_PATTERN = r'[A-Z0-9]{2,8}'

@app.event("app_mention")
def handle_app_mentions(body, say):
    say("Upload an image with a license plate, and I'll extract the plate number for you!")

@app.event("message")
def handle_message_events(body, say, client):
    # Check if the message contains a file
    if "files" in body["event"]:
        for file in body["event"]["files"]:
            # Check if file is an image
            if file["mimetype"].startswith("image/"):
                channel_id = body["event"]["channel"]
                thread_ts = body["event"].get("thread_ts", body["event"]["ts"])
                
                # Process image to extract license plate
                try:
                    say(text="Processing your image...", thread_ts=thread_ts)
                    license_plate = process_image(file["url_private"], client.token)
                    
                    if license_plate:
                        say(text=f"Found license plate: `{license_plate}`", thread_ts=thread_ts)
                    else:
                        say(text="Sorry, I couldn't detect any license plate in this image.", thread_ts=thread_ts)
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    say(text="Sorry, I encountered an error while processing your image.", thread_ts=thread_ts)

def process_image(image_url, token):
    """Download the image and extract license plate text using OCR"""
    # Download image
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(image_url, headers=headers)
    image = Image.open(BytesIO(response.content))
    
    # Preprocess image if needed (you can add more preprocessing steps here)
    # image = image.convert('L')  # Convert to grayscale
    
    # Extract text using OCR
    text = pytesseract.image_to_string(image)
    
    # Find license plate patterns
    matches = re.findall(LICENSE_PLATE_PATTERN, text)
    
    # Return the first match, or None if no matches
    return matches[0] if matches else None

if __name__ == "__main__":
    # Start the app using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    logger.info("⚡️ License Plate OCR Bot is running!")
    handler.start()
