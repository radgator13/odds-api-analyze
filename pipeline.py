import subprocess
import time
import os
import sys
import builtins
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import shutil
# === Load environment variables from .env ===
print("Loading .env file...")
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMS_ALERT = os.getenv("SMS_ALERT")

print(f"EMAIL_USER: {EMAIL_USER}")
print(f"EMAIL_PASS loaded: {'YES' if EMAIL_PASS else 'NO'}")
print(f"SMS_ALERT: {SMS_ALERT}")

if not EMAIL_USER or not EMAIL_PASS:
    print("[ERROR] EMAIL_USER or EMAIL_PASS not loaded. Check .env and load_dotenv().")
    sys.exit(1)

# === Email helper ===
TO_EMAILS = [EMAIL_USER]
if SMS_ALERT:
    TO_EMAILS.append(SMS_ALERT)

def send_email(subject, body):
    print(f"Sending email to: {', '.join(TO_EMAILS)}")
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = f"[Pipeline] {subject}"
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join(TO_EMAILS)

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("Email/SMS sent successfully.")
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
    print("[WARN] Terminal does not support UTF-8. Falling back.")

# === Script steps ===
steps = [
    ("[STEP] Scraping Stathead stats", "scrape_stathead_stats.py"),
    ("[STEP] Pulling sportsbook props", "run_odds_api.py"),
    ("[STEP] Training strikeout model", "Full_Training_Script.py"),
    ("[STEP] Generating predictions", "predict_props_with_model.py"),
    ("[STEP] Compare strikeouts to actuals", "compare_strikeout_picks_to_actual.py")
]

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
        error_msg = f"[ERROR] Script failed: {script}\n{result.stderr}"
        print(error_msg)
        send_email(f"Pipeline Failed: {script}", error_msg)
        pipeline_success = False
        break
    else:
        print(f"[OUTPUT] {script} completed.")
        print(result.stdout)

# === Git push ===
# === Git push ===
# === Git push (force local state to GitHub) ===
if pipeline_success:
    print("\n[STEP] Committing and force pushing to GitHub...")

    try:
        import subprocess, time, os, shutil

        def ensure_git_identity():
            name = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.strip()
            email = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()
            if not name:
                subprocess.run(["git", "config", "--global", "user.name", "Gator"], check=True)
            if not email:
                subprocess.run(["git", "config", "--global", "user.email", "a1d3r13@gmail.com"], check=True)

        ensure_git_identity()
        subprocess.run(["git", "config", "--global", "core.longpaths", "true"], check=True)

        # === Clean dangerous paths ===
        paths_to_clean = ["clean-repo", "new_data/archive"]
        for path in paths_to_clean:
            if os.path.exists(path):
                print(f"[CLEANUP] Removing tracked path: {path}")
                subprocess.run(["git", "rm", "--cached", "-r", path], check=False)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.isfile(path):
                    os.remove(path)
                with open(".gitignore", "a") as gi:
                    gi.write(f"\n{path}/\n")

        # Stage and commit
        print("[STEP] Staging and committing changes...")
        subprocess.run(["git", "add", "-u"], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        if status:
            msg = f"Auto push from pipeline at {time.strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(["git", "commit", "-m", msg], check=True)

        # Final force push
        print("[STEP] Force pushing local state to GitHub...")
        subprocess.run(["git", "push", "--force", "origin", "main"], check=True)
        print("✅ Force push successful.")

        send_email("Pipeline Success", "Force push completed successfully.")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git command failed: {e}")
        send_email("Git Push Failed", f"Git error:\n{e.stderr if hasattr(e, 'stderr') else str(e)}")












