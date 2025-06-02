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
if pipeline_success:
    print("\n[STEP] Committing and pushing to GitHub...")

    try:
        import subprocess, time, os

        def ensure_git_identity():
            name = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.strip()
            email = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()
            if not name:
                subprocess.run(["git", "config", "--global", "user.name", "Gator"], check=True)
            if not email:
                subprocess.run(["git", "config", "--global", "user.email", "a1d3r13@gmail.com"], check=True)

        ensure_git_identity()

        subprocess.run(["git", "config", "--global", "core.longpaths", "true"], check=True)

        # === Clean up dangerous folders before pull ===
        import shutil

        if os.path.exists("clean-repo"):
            print("[CLEANUP] Removing accidentally included 'clean-repo' directory...")
            subprocess.run(["git", "rm", "--cached", "-r", "clean-repo"], check=False)
            shutil.rmtree("clean-repo", ignore_errors=True)  # Windows-safe deletion
            with open(".gitignore", "a") as gi:
                gi.write("\nclean-repo/\n")


        # === Clean up archive if needed ===
        if os.path.exists("new_data/archive"):
            subprocess.run(["git", "rm", "--cached", "-r", "new_data/archive"], check=False)
            with open(".gitignore", "a") as gi:
                gi.write("\nnew_data/archive/\n")

        # Stage only tracked changes, not untracked files
        print("[STEP] Staging tracked file changes only...")
        subprocess.run(["git", "add", "-u"], check=True)

        # Pre-pull commit if necessary
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status.strip():
            msg = f"Auto pre-pull commit at {time.strftime('%Y%m%d_%H%M%S')}"
            print("[STEP] Committing local changes before pull...")
            subprocess.run(["git", "commit", "-m", msg], check=True)
        else:
            print("[INFO] No local changes to commit.")

        print("[STEP] Pulling latest changes with rebase...")
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)

        # Stage and push final changes (if any)
        subprocess.run(["git", "add", "-u"], check=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff.returncode != 0:
            msg = f"Auto push from run_odds_api at {time.strftime('%Y%m%d_%H%M%S')}"
            print("[STEP] Committing final changes...")
            subprocess.run(["git", "commit", "-m", msg], check=True)
            print("[STEP] Pushing to GitHub...")
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("✅ Git push successful.")
        else:
            print("[INFO] No new changes to push.")

        send_email("Pipeline Success", "Git push completed successfully.")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git command failed: {e}")
        send_email("Git Push Failed", f"Git error:\n{e.stderr if hasattr(e, 'stderr') else str(e)}")







