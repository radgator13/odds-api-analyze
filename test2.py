import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMS_ALERT = os.getenv("SMS_ALERT")

print(f"EMAIL_USER: {EMAIL_USER}")
print(f"EMAIL_PASS loaded: {'YES' if EMAIL_PASS else 'NO'}")
print(f"SMS_ALERT: {SMS_ALERT}")

if not EMAIL_USER or not EMAIL_PASS:
    print("[ERROR] Missing EMAIL_USER or EMAIL_PASS.")
    exit(1)

try:
    msg = EmailMessage()
    msg.set_content("This is a test message from PythonAnywhere.")
    msg["Subject"] = "Test Email Login"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(filter(None, [EMAIL_USER, SMS_ALERT]))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.set_debuglevel(1)
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

    print("Test email/SMS sent successfully.")

except Exception as e:
    print(f"[ERROR] Email failed: {e}")
