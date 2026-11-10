"""One-time: authorise Wekil's mailbox/calendar and store GOOGLE_REFRESH_TOKEN in backend/.env.

Run: uv run python scripts/google_auth.py   (prints the consent URL, waits on localhost:8765)
"""

import os
import pathlib
import re

from google_auth_oauthlib.flow import InstalledAppFlow

ENV = pathlib.Path(__file__).resolve().parents[1] / ".env"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/calendar.events"]

env = dict(re.findall(r"^(\w+)=(.*)$", ENV.read_text(), re.M))
config = {"installed": {"client_id": env["GOOGLE_CLIENT_ID"], "client_secret": env["GOOGLE_CLIENT_SECRET"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"}}
flow = InstalledAppFlow.from_client_config(config, SCOPES)
creds = flow.run_local_server(port=8765, open_browser=False, prompt="consent", access_type="offline",
                              authorization_prompt_message="Open this URL to authorise Wekil:\n{url}\n")
text = re.sub(r"^GOOGLE_REFRESH_TOKEN=.*\n?", "", ENV.read_text(), flags=re.M)
ENV.write_text(text + f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}\n")
os.chmod(ENV, 0o600)
print("Saved GOOGLE_REFRESH_TOKEN")
