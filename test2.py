import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch credentials and numbers
sid = os.getenv("TWILIO_SID")
token = os.getenv("TWILIO_TOKEN")
from_number = os.getenv("TWILIO_FROM")
to_number = os.getenv("TWILIO_TO")

# Debug print (optional — remove in production)
print("TWILIO_SID:", sid)
print("TWILIO_TOKEN:", "✓" if token else "Missing")
print("TWILIO_FROM:", from_number)
print("TWILIO_TO:", to_number)

# Check for missing environment variables
if not all([sid, token, from_number, to_number]):
    print("❌ Missing one or more required environment variables.")
    exit(1)

try:
    # Initialize Twilio client
    client = Client(sid, token)

    # Send SMS
    message = client.messages.create(
        body="✅ Twilio is now live from PythonAnywhere to your verified number.",
        from_=from_number,
        to=to_number
    )

    print("✅ Success! Message SID:", message.sid)

except Exception as e:
    print("❌ SMS failed:", e)
