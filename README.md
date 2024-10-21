# MelodyMaster
MelodyMaster: A feature-rich Discord bot integrating Spotify for music control, sharing, and interactive music experiences.

# MelodyMaster - Discord Spotify Bot

MelodyMaster is a powerful Discord bot that integrates with Spotify, allowing users to control their Spotify playback, share music, and enjoy various music-related features directly within Discord.

## Features

- **Spotify Authentication**: Securely connect your Spotify account to the bot.
- **Playback Control**: Play, pause, skip, and adjust volume of your Spotify playback.
- **Now Playing**: Display currently playing track with album art and details.
- **Music Recommendations**: Get personalized song recommendations based on your current track.
- **Lyrics**: Fetch and display lyrics for the currently playing song.
- **Music Trivia**: Play a fun music trivia game based on your listening history.
- **Share Music**: Easily share what you're listening to with your Discord friends.
- **User Stats**: View your top tracks and artists from Spotify.
- **Audio Features**: Analyze the audio features of the current track.

## Setup

1. Clone this repository.
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables in a `.env` file:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
   GENIUS_ACCESS_TOKEN=your_genius_access_token
   ```
4. Run the bot:
   ```
   python discord_spotify_bot.py
   ```

## Usage

Use the following commands in Discord:

- `/auth`: Authenticate with Spotify
- `/play <song>`: Play a song
- `/current`: Show the currently playing track
- `/recommend`: Get song recommendations
- `/lyrics`: Fetch lyrics for the current song
- `/share`: Share the current track
- `/trivia`: Play a music trivia game
- `/stats`: View your Spotify statistics
- `/features`: Analyze audio features of the current track

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
