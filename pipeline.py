import subprocess
import time
import os
import sys
import builtins
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

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
if pipeline_success:
    print("\n[STEP] Committing and pushing to GitHub...")

    try:
        import subprocess, time

        def ensure_git_identity():
            name = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.strip()
            email = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()

            if not name:
                subprocess.run(["git", "config", "--global", "user.name", "Gator"], check=True)
            if not email:
                subprocess.run(["git", "config", "--global", "user.email", "a1d3r13@gmail.com"], check=True)

        ensure_git_identity()

        # Support long paths (Windows)
        subprocess.run(["git", "config", "--global", "core.longpaths", "true"], check=True)

        # Check for any unstaged local changes
        print("[STEP] Checking for local changes...")
        status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        has_changes = bool(status_result.stdout.strip())

        if has_changes:
            print("[STEP] Staging and pre-committing changes before pull...")
            subprocess.run(["git", "add", "."], check=True)
            pre_pull_msg = f"Auto pre-pull commit at {time.strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(["git", "commit", "-m", pre_pull_msg], check=True)
        else:
            print("[INFO] Working directory is clean.")

        print("[STEP] Pulling latest changes (rebase)...")
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)

        # Stage any new changes after pull
        print("[STEP] Staging post-pull changes...")
        subprocess.run(["git", "add", "."], check=True)

        print("[STEP] Checking for post-pull changes...")
        diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"])

        if diff_result.returncode == 0:
            print("[INFO] No new changes to commit.")
        else:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            commit_message = f"Auto push from run_odds_api at {timestamp}"

            print("[STEP] Committing new changes...")
            subprocess.run(["git", "commit", "-m", commit_message], check=True)

            print("[STEP] Pushing to GitHub...")
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("✅ Git push successful.")

        send_email("Pipeline Success", f"Auto push from run_odds_api completed at {time.strftime('%Y%m%d_%H%M%S')}.")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git command failed: {e}")
        send_email("Git Push Failed", f"Git error:\n{e.stderr if hasattr(e, 'stderr') else str(e)}")





