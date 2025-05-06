import os
import re
import time
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import pytesseract
from PIL import Image
import requests
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Regular expression pattern for license plates (customize based on your region's format)
LICENSE_PLATE_PATTERN = r'[A-Z0-9]{2,8}'

@app.command("/carproblem")
def open_car_problem_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    
    # Open a modal for the user to submit their car image
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "car_problem_modal",
                "title": {"type": "plain_text", "text": "Car Problem"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Upload a photo of your car to extract the license plate number"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "car_image_block",
                        "element": {
                            "type": "file_input",
                            "action_id": "car_image",
                            "filetypes": ["jpg", "jpeg", "png"]
                        },
                        "label": {"type": "plain_text", "text": "Car Image"}
                    },
                    {
                        "type": "input",
                        "block_id": "description_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "description",
                            "placeholder": {"type": "plain_text", "text": "Add any additional details here..."}
                        },
                        "label": {"type": "plain_text", "text": "Additional Details"}
                    }
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error opening modal: {e}")

@app.view("car_problem_modal")
def handle_car_problem_submission(ack, body, client, view):
    # Acknowledge the view submission
    ack()
    
    user_id = body["user"]["id"]
    
    # Check if a file was uploaded
    file_id = None
    try:
        # Extract the uploaded file ID
        uploaded_files = view["state"]["values"]["car_image_block"]["car_image"]["files"]
        if uploaded_files:
            file_id = uploaded_files[0]
    except KeyError:
        pass
    
    # Get additional description if provided
    description = ""
    try:
        description = view["state"]["values"]["description_block"]["description"]["value"] or ""
    except KeyError:
        pass
    
    if file_id:
        # Send a loading message first
        message = send_loading_message(client, user_id)
        
        # Process the file
        process_uploaded_file(client, user_id, file_id, description, message["ts"])
    else:
        # Send a message if no file was uploaded
        client.chat_postMessage(
            channel=user_id,
            text="No image was uploaded. Please try again with a car image."
        )

def send_loading_message(client, user_id):
    """Send a message with loading indicator"""
    return client.chat_postMessage(
        channel=user_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":hourglass_flowing_sand: *Processing your car image...*"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "This may take a few moments. I'm analyzing the image to extract the license plate number."
                    }
                ]
            }
        ],
        text="Processing your car image..." # Fallback text
    )

def process_uploaded_file(client, user_id, file_id, description, message_ts):
    """Process the uploaded file and extract license plate"""
    try:
        # Get file info
        file_info = client.files_info(file=file_id)
        file_url = file_info["file"]["url_private"]
        
        # Process image to extract license plate (add a small delay to show loading state)
        license_plate = process_image(file_url, client.token)
        
        # Update the message with the results
        if license_plate:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":white_check_mark: *License Plate Detected:* `{license_plate}`"
                    }
                }
            ]
            
            # Add image thumbnail if possible
            try:
                image_url = file_info["file"]["thumb_480"]
                if image_url:
                    blocks.append({
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": "Car image"
                    })
            except (KeyError, TypeError):
                pass
            
            # Add description if provided
            if description:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Additional details:*\n{description}"
                    }
                })
            
            # Add footer
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Processed at {time.strftime('%H:%M:%S')}"
                    }
                ]
            })
            
            client.chat_update(
                channel=user_id,
                ts=message_ts,
                blocks=blocks,
                text=f"License plate detected: {license_plate}"
            )
        else:
            client.chat_update(
                channel=user_id,
                ts=message_ts,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":x: *Sorry, I couldn't detect any license plate in this image.*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please try again with a clearer image of the license plate."
                        }
                    }
                ],
                text="No license plate detected"
            )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        client.chat_update(
            channel=user_id,
            ts=message_ts,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":warning: *Error Processing Image*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"I encountered an error while processing your image: `{str(e)[:100]}`"
                    }
                }
            ],
            text="Error processing image"
        )

def process_image(image_url, token):
    """Download the image and extract license plate text using OCR"""
    # Download image
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(image_url, headers=headers)
    image = Image.open(BytesIO(response.content))
    
    # Simulate processing time to show loading state (remove in production)
    time.sleep(2)
    
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
