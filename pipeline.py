import subprocess
import time
import os
import sys
import builtins
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# === Load environment variables from .env ===
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# === Email helper ===
TO_EMAILS = [
    os.getenv("EMAIL_USER"),           # your Gmail
    os.getenv("SMS_ALERT")             # your phone via T-Mobile
]

def send_email(subject, body):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join([email for email in TO_EMAILS if email])

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print(f"[ERROR] Failed to send email/SMS: {e}")


# === Force UTF-8 output ===
os.environ["PYTHONIOENCODING"] = "utf-8"

# === Safe print override ===
original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)
builtins.print = safe_print

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === CONFIG ===
steps = [
    ("[STEP] Scraping Stathead stats", "scrape_stathead_stats.py"),
    ("[STEP] Pulling sportsbook props", "run_odds_api.py"),
    ("[STEP] Training strikeout model", "Full_Training_Script.py"),
    ("[STEP] Generating predictions", "predict_props_with_model.py"),
    ("[STEP] Compare strikeouts to actuals", "compare_strikeout_picks_to_actual.py")
]

# === RUN STEPS ===
pipeline_success = True
for label, script in steps:
    print(f"\n{label}")
    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        error_msg = f"❌ Error running {script}:\n{result.stderr}"
        print(error_msg)
        send_email(f"❌ Pipeline Failed: {script}", error_msg)
        pipeline_success = False
        break
    else:
        print(result.stdout)

if pipeline_success:
    # === GIT PUSH ===
    print("\n📦 Committing and pushing to GitHub...")
    try:
        # Set Git identity if missing
        def ensure_git_identity():
            name = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.strip()
            email = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()

            if not name:
                subprocess.run(["git", "config", "--global", "user.name", "Gator"], check=True)
                print("🔧 Set git user.name = Gator")
            if not email:
                subprocess.run(["git", "config", "--global", "user.email", "a1d3r13@gmail.com"], check=True)
                print("🔧 Set git user.email = a1d3r13@gmail.com")

        ensure_git_identity()

        subprocess.run(["git", "add", "."], check=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        commit_message = f"Auto push from run_pipeline at {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "master"], check=True)
        print("✅ Git push successful.")
        send_email("✅ Pipeline Success", f"Pipeline ran and pushed at {timestamp}.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")
        send_email("❌ Git Push Failed", str(e))



