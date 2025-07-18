from flask import Flask, request, redirect
import requests
import os

app = Flask(__name__)

# Get these from your Slack app settings
CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "your-client-id-here")
CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "your-client-secret-here")

@app.route("/")
def index():
    return "Hello! This is your Slack OAuth redirect handler."

@app.route("/slack/oauth_redirect")
def oauth_redirect():
    code = request.args.get("code")
    if not code:
        return "No code provided!", 400

    # Exchange code for an access token
    token_url = "https://slack.com/api/oauth.v2.access"
    params = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(token_url, params=params)
    data = response.json()

    if not data.get("ok"):
        return f"Error: {data.get('error', 'unknown error')}", 400

    # Success: you now have tokens
    access_token = data["access_token"]
    bot_user_id = data["bot_user_id"]
    team_name = data["team"]["name"]

    # Save these tokens securely!
    print(f"Access Token: {access_token}")
    print(f"Bot User ID: {bot_user_id}")
    print(f"Team: {team_name}")

    return f"Slack app installed to workspace: {team_name}. Bot user: {bot_user_id}"

if __name__ == "__main__":
    app.run(port=5055, debug=True)
