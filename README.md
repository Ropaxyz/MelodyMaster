# MelodyMaster

A powerful Discord bot that integrates with Spotify, providing real-time music updates, playback controls, and personalized music recommendations. Created by Ross Paxton.

## Features

- 🎵 Real-time track updates in DMs
- 🎮 Interactive playback controls with buttons
- 📊 Personal listening statistics
- 🎯 Music recommendations based on listening history
- 📝 Custom playlist generation
- 🔊 Volume control
- 🔄 Automatic token refresh
- 🔒 Secure authentication flow

## Prerequisites

- Python 3.8+
- Discord Bot Token
- Spotify Developer Account
- ngrok account (free tier works fine)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Ropaxyz/MelodyMaster.git
cd MelodyMaster
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install and Set Up ngrok:
   - Sign up for a free account at [ngrok](https://ngrok.com)
   - Download ngrok for your operating system
   - Extract the ngrok executable to a location in your PATH
   - Copy your authtoken from the ngrok dashboard
   - Authenticate ngrok with your token:
     ```bash
     ngrok authtoken your_token_here
     ```

5. Create a `.env` file in the root directory:
```
DISCORD_BOT_TOKEN=your_discord_bot_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
CHANNEL_ID=your_discord_channel_id
```

Note: Don't set SPOTIFY_REDIRECT_URI in your .env file - it will be automatically managed by the ngrok script.

## Setup

1. Create a Discord Application and Bot:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Add a bot to your application
   - Enable necessary intents (Message Content, Server Members)
   - Copy the bot token to your `.env` file

2. Create a Spotify Application:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new application
   - Important: After starting the bot, it will provide you with an ngrok URL to add as your redirect URI
   - Copy Client ID and Client Secret to your `.env` file

## Running the Bot

Use the provided start script:
```bash
chmod +x start.sh
./start.sh
```

This will:
1. Start ngrok tunnel (creates a public URL for Spotify callbacks)
2. Launch the callback server (handles Spotify authentication)
3. Start the Discord bot
4. Display the ngrok URL that needs to be added to your Spotify Dashboard

Important: Every time you start the bot:
1. A new ngrok URL will be generated
2. The script will display the new callback URL
3. You MUST update this URL in your Spotify Dashboard:
   - Go to https://developer.spotify.com/dashboard
   - Select your app
   - Click 'Edit Settings'
   - Under 'Redirect URIs', remove old URLs and add the new one
   - Click 'Save'

The script creates separate screen sessions for each component. You can attach to them using:
```bash
screen -r [ngrok|callback|bot]
```

To detach from a screen session, press `Ctrl+A`, then `D`.

## Understanding the Components

- `musicboy.py` - Main Discord bot
- `callback_server.py` - Local server that handles Spotify authentication
- `manage_ngrok.py` - Creates and manages the ngrok tunnel, updates the redirect URI
- `start.sh` - Orchestrates all components

The authentication flow:
1. ngrok creates a secure tunnel to your local callback server
2. The bot uses this tunnel URL for Spotify authentication
3. When users authenticate, Spotify redirects to the ngrok URL
4. ngrok forwards the request to your local callback server
5. The callback server processes the authentication

## Commands

- `/nowplaying` - Show current track with playback controls
- `/stats` - View your listening statistics
- `/recommendations` - Get personalized music recommendations
- `/playlist` - Create custom playlists
- `/toggle_monitor` - Turn track notifications on/off

## Troubleshooting

Common issues:
- If authentication fails, ensure you've updated the redirect URI in your Spotify Dashboard
- If the bot stops responding, check all three screen sessions for errors
- If ngrok disconnects, restart the bot to get a new URL
- Make sure ports 8888 (callback server) and 4040 (ngrok) are available

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) © Ross Paxton

## Contact

Ross Paxton - [GitHub](https://github.com/Ropaxyz)

Project Link: [https://github.com/Ropaxyz/MelodyMaster](https://github.com/Ropaxyz/MelodyMaster)
