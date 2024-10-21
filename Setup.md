# Setup Guide for MelodyMaster - Spotify Discord Bot

This guide will walk you through the process of setting up the MelodyMaster Spotify Discord Bot on your own server.

## Prerequisites

Before you begin, make sure you have the following:

1. Python 3.8 or higher installed on your system
2. A Discord account and the ability to create a bot
3. A Spotify Developer account
4. A Genius Developer account (for lyrics functionality)
5. Git installed on your system (optional, for cloning the repository)

## Step 1: Clone the Repository

1. Open a terminal or command prompt.
2. Navigate to the directory where you want to install the bot.
3. Run the following command:
   ```
   git clone https://github.com/your-username/MelodyMaster.git
   ```
   (Replace `your-username` with the actual GitHub username where the repository is hosted)

If you don't have Git, you can download the code as a ZIP file from the GitHub repository and extract it.

## Step 2: Set Up a Virtual Environment (Optional but Recommended)

1. Navigate into the project directory:
   ```
   cd MelodyMaster
   ```
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

## Step 3: Install Dependencies

In the project directory, run:
```
pip install -r requirements.txt
```

## Step 4: Set Up Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click "New Application" and give it a name.
3. Go to the "Bot" tab and click "Add Bot".
4. Under the bot's username, click "Copy" to copy your bot's token.
5. Enable the following Privileged Gateway Intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

## Step 5: Set Up Spotify API

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. Click "Create an App" and fill in the details.
3. Once created, you'll see your Client ID and Client Secret.
4. Click "Edit Settings" and add a Redirect URI (e.g., `http://localhost:8888/callback`).

## Step 6: Set Up Genius API

1. Go to the [Genius API Clients page](https://genius.com/api-clients).
2. Click "New API Client" and fill in the details.
3. Once created, you'll receive a Client Access Token.

## Step 7: Configure Environment Variables

1. In the project directory, create a file named `.env`.
2. Add the following lines to the file, replacing the placeholders with your actual values:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
   GENIUS_ACCESS_TOKEN=your_genius_access_token
   ```

## Step 8: Run the Bot

1. In the project directory, run:
   ```
   python discord_spotify_bot.py
   ```
2. You should see a message indicating that the bot has connected to Discord.

## Step 9: Invite the Bot to Your Server

1. Go back to the Discord Developer Portal, to your application's page.
2. Go to the "OAuth2" tab, then "URL Generator".
3. Under "Scopes", select "bot" and "applications.commands".
4. Under "Bot Permissions", select the permissions your bot needs (at minimum: Read Messages/View Channels, Send Messages, Use Slash Commands).
5. Copy the generated URL and open it in a new browser tab.
6. Select the server you want to add the bot to and click "Authorize".

## Step 10: Use the Bot

1. In your Discord server, type `/auth` to start the Spotify authentication process.
2. Follow the prompts to link your Spotify account.
3. Once authenticated, you can use commands like `/play`, `/current`, `/recommend`, etc.

## Troubleshooting

- If you encounter any errors, check the `discord_spotify_bot.log` file in the project directory for more details.
- Ensure all the required environment variables are set correctly in the `.env` file.
- Make sure your Discord bot has the necessary permissions in your server.

For more help, refer to the project's GitHub issues page or contact the maintainer.

Enjoy using MelodyMaster!
