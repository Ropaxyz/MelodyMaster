import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import asyncio
import random
import lyricsgenius
import json
import time

# Load environment variables
load_dotenv()

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'discord_spotify_bot.log'
log_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Get tokens from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Genius client
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)

# Dictionary to store user-specific Spotify clients and token info
user_spotify_data = {}

class SpotifyAuthView(discord.ui.View):
    def __init__(self, auth_url):
        super().__init__()
        self.add_item(discord.ui.Button(label="Authenticate with Spotify", url=auth_url, style=discord.ButtonStyle.url))

class SpotifyView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.primary)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        try:
            sp = await get_spotify_client(self.user_id)
            current_playback = sp.current_playback()
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                await interaction.response.send_message("Playback paused.", ephemeral=True)
            else:
                sp.start_playback()
                await interaction.response.send_message("Playback resumed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        try:
            sp = await get_spotify_client(self.user_id)
            sp.next_track()
            await interaction.response.send_message("Skipped to next track.", ephemeral=True)
            await update_now_playing(interaction.user)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        try:
            sp = await get_spotify_client(self.user_id)
            sp.previous_track()
            await interaction.response.send_message("Returned to previous track.", ephemeral=True)
            await update_now_playing(interaction.user)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Volume Up", style=discord.ButtonStyle.secondary)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        try:
            sp = await get_spotify_client(self.user_id)
            current_volume = sp.current_playback()['device']['volume_percent']
            new_volume = min(current_volume + 10, 100)
            sp.volume(new_volume)
            await interaction.response.send_message(f"Volume increased to {new_volume}%", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Volume Down", style=discord.ButtonStyle.secondary)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        try:
            sp = await get_spotify_client(self.user_id)
            current_volume = sp.current_playback()['device']['volume_percent']
            new_volume = max(current_volume - 10, 0)
            sp.volume(new_volume)
            await interaction.response.send_message(f"Volume decreased to {new_volume}%", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

async def get_spotify_client(user_id):
    if user_id in user_spotify_data:
        sp_oauth, token_info = user_spotify_data[user_id]
        
        # Check if token is expired and refresh if necessary
        if sp_oauth.is_token_expired(token_info):
            try:
                token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                sp = spotipy.Spotify(auth=token_info['access_token'])
                user_spotify_data[user_id] = (sp_oauth, token_info)
                
                # Save the refreshed token
                with open(f'.spotify_cache_{user_id}', 'w') as f:
                    json.dump(token_info, f)
                
                logger.info(f"Refreshed token for user {user_id}")
            except Exception as e:
                logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
                raise Exception("Failed to refresh Spotify token. Please re-authenticate.")
        else:
            sp = spotipy.Spotify(auth=token_info['access_token'])
        
        return sp
    
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                            client_secret=SPOTIFY_CLIENT_SECRET,
                            redirect_uri=SPOTIFY_REDIRECT_URI,
                            scope="user-modify-playback-state user-read-playback-state user-read-currently-playing user-top-read",
                            cache_path=f'.spotify_cache_{user_id}')
    
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        raise Exception(f"No token found. Please authenticate: {auth_url}")
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_spotify_data[user_id] = (sp_oauth, token_info)
    return sp

async def update_now_playing(user):
    try:
        sp = await get_spotify_client(user.id)
        track = sp.current_user_playing_track()
        if track is not None and track['item'] is not None:
            embed = discord.Embed(title="Now Playing", color=discord.Color.green())
            embed.add_field(name="Track", value=track['item']['name'], inline=False)
            embed.add_field(name="Artist", value=track['item']['artists'][0]['name'], inline=False)
            embed.add_field(name="Album", value=track['item']['album']['name'], inline=False)
            
            if track['item']['album']['images']:
                embed.set_thumbnail(url=track['item']['album']['images'][0]['url'])
            
            await user.send(embed=embed, view=SpotifyView(user.id))
    except Exception as e:
        logger.error(f"Error in update_now_playing for user {user.id}: {str(e)}")

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
        refresh_all_tokens.start()
        logger.info("Started refresh_all_tokens background task")
    except Exception as e:
        logger.error(f"Error during bot startup: {str(e)}")

@bot.tree.command(name="auth")
async def auth(interaction: discord.Interaction):
    try:
        sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                client_secret=SPOTIFY_CLIENT_SECRET,
                                redirect_uri=SPOTIFY_REDIRECT_URI,
                                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing user-top-read",
                                cache_path=f'.spotify_cache_{interaction.user.id}')
        
        auth_url = sp_oauth.get_authorize_url()
        view = SpotifyAuthView(auth_url)
        await interaction.response.send_message("Click the button below to authenticate with Spotify:", view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error during authentication: {str(e)}", ephemeral=True)

@bot.tree.command(name="complete_auth")
@app_commands.describe(auth_url="The URL you were redirected to after authenticating")
async def complete_auth(interaction: discord.Interaction, auth_url: str):
    try:
        sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                client_secret=SPOTIFY_CLIENT_SECRET,
                                redirect_uri=SPOTIFY_REDIRECT_URI,
                                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing user-top-read",
                                cache_path=f'.spotify_cache_{interaction.user.id}')
        
        code = sp_oauth.parse_response_code(auth_url)
        
        # Use get_access_token without as_dict=True
        token_info = sp_oauth.get_access_token(code, as_dict=False)
        
        # If token_info is a string (access token), we need to get the full token info
        if isinstance(token_info, str):
            token_info = sp_oauth.get_cached_token()
        
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_spotify_data[interaction.user.id] = (sp_oauth, token_info)
        
        # Save the token info
        with open(f'.spotify_cache_{interaction.user.id}', 'w') as f:
            json.dump(token_info, f)
        
        await interaction.response.send_message("Authentication successful! You can now use Spotify commands.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error completing authentication: {str(e)}", ephemeral=True)

@bot.tree.command(name="play")
@app_commands.describe(query="The song you want to play")
async def play(interaction: discord.Interaction, query: str):
    try:
        sp = await get_spotify_client(interaction.user.id)
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            sp.start_playback(uris=[track['uri']])
            await interaction.response.send_message(f"Now playing: {track['name']} by {track['artists'][0]['name']}")
            await update_now_playing(interaction.user)
        else:
            await interaction.response.send_message("No tracks found.")
    except Exception as e:
        await interaction.response.send_message(str(e), ephemeral=True)

@bot.tree.command(name="current")
async def current(interaction: discord.Interaction):
    await interaction.response.defer()
    await update_now_playing(interaction.user)

@bot.tree.command(name="recommend")
async def recommend(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        current_track = sp.current_user_playing_track()
        if current_track and current_track['item']:
            recommendations = sp.recommendations(seed_tracks=[current_track['item']['id']], limit=5)
            embed = discord.Embed(title="Recommended Tracks", color=discord.Color.blue())
            for track in recommendations['tracks']:
                embed.add_field(name=track['name'], value=f"by {track['artists'][0]['name']}", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No track is currently playing.")
    except Exception as e:
        await interaction.response.send_message(str(e), ephemeral=True)

@bot.tree.command(name="lyrics")
async def lyrics(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        current_track = sp.current_user_playing_track()
        if current_track and current_track['item']:
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            song = genius.search_song(track_name, artist_name)
            if song:
                lyrics = song.lyrics
                # Split lyrics into chunks of 1024 characters (Discord's embed field value limit)
                chunks = [lyrics[i:i+1024] for i in range(0, len(lyrics), 1024)]
                embed = discord.Embed(title=f"Lyrics for {track_name} by {artist_name}", color=discord.Color.green())
                for i, chunk in enumerate(chunks):
                    embed.add_field(name='\u200b' if i > 0 else 'Lyrics', value=chunk, inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("Lyrics not found.")
        else:
            await interaction.response.send_message("No track is currently playing.")
    except Exception as e:
        await interaction.response.send_message(f"Error fetching lyrics: {str(e)}", ephemeral=True)

# [Previous code remains the same...]

@bot.tree.command(name="share")
async def share(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        current_track = sp.current_user_playing_track()
        if current_track and current_track['item']:
            track = current_track['item']
            embed = discord.Embed(title="Check out what I'm listening to!", color=discord.Color.green())
            embed.add_field(name="Track", value=track['name'], inline=False)
            embed.add_field(name="Artist", value=track['artists'][0]['name'], inline=False)
            embed.add_field(name="Album", value=track['album']['name'], inline=False)
            embed.add_field(name="Listen on Spotify", value=track['external_urls']['spotify'], inline=False)
            if track['album']['images']:
                embed.set_thumbnail(url=track['album']['images'][0]['url'])
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No track is currently playing.")
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="trivia")
async def trivia(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        top_tracks = sp.current_user_top_tracks(limit=50, time_range='medium_term')
        track = random.choice(top_tracks['items'])
        artist = track['artists'][0]['name']
        correct_title = track['name']
        
        # Get three random incorrect titles
        incorrect_titles = [t['name'] for t in random.sample(top_tracks['items'], 3) if t['name'] != correct_title]
        
        # Combine all titles and shuffle
        all_titles = [correct_title] + incorrect_titles
        random.shuffle(all_titles)
        
        embed = discord.Embed(title="Music Trivia", description=f"Which of these is a song by {artist}?", color=discord.Color.blue())
        for i, title in enumerate(all_titles):
            embed.add_field(name=f"Option {i+1}", value=title, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        def check(m):
            return m.author.id == interaction.user.id and m.content.isdigit() and 1 <= int(m.content) <= 4
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if all_titles[int(msg.content) - 1] == correct_title:
                await interaction.followup.send("Correct! Well done!")
            else:
                await interaction.followup.send(f"Sorry, that's incorrect. The correct answer was: {correct_title}")
        except asyncio.TimeoutError:
            await interaction.followup.send(f"Time's up! The correct answer was: {correct_title}")
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="stats")
async def stats(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        top_tracks = sp.current_user_top_tracks(limit=5, time_range='short_term')
        top_artists = sp.current_user_top_artists(limit=5, time_range='short_term')
        
        embed = discord.Embed(title="Your Spotify Statistics", color=discord.Color.purple())
        
        track_list = "\n".join([f"{i+1}. {track['name']} by {track['artists'][0]['name']}" for i, track in enumerate(top_tracks['items'])])
        embed.add_field(name="Top 5 Tracks (Last 4 Weeks)", value=track_list, inline=False)
        
        artist_list = "\n".join([f"{i+1}. {artist['name']}" for i, artist in enumerate(top_artists['items'])])
        embed.add_field(name="Top 5 Artists (Last 4 Weeks)", value=artist_list, inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="features")
async def features(interaction: discord.Interaction):
    try:
        sp = await get_spotify_client(interaction.user.id)
        current_track = sp.current_user_playing_track()
        if current_track and current_track['item']:
            track_id = current_track['item']['id']
            features = sp.audio_features(track_id)[0]
            
            embed = discord.Embed(title=f"Audio Features for {current_track['item']['name']}", color=discord.Color.orange())
            embed.add_field(name="Danceability", value=f"{features['danceability']:.2f}", inline=True)
            embed.add_field(name="Energy", value=f"{features['energy']:.2f}", inline=True)
            embed.add_field(name="Valence", value=f"{features['valence']:.2f}", inline=True)
            embed.add_field(name="Tempo", value=f"{features['tempo']:.0f} BPM", inline=True)
            embed.add_field(name="Loudness", value=f"{features['loudness']:.2f} dB", inline=True)
            embed.add_field(name="Acousticness", value=f"{features['acousticness']:.2f}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No track is currently playing.")
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

@tasks.loop(hours=1)
async def refresh_all_tokens():
    for user_id, (sp_oauth, token_info) in user_spotify_data.items():
        if sp_oauth.is_token_expired(token_info):
            try:
                new_token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                user_spotify_data[user_id] = (sp_oauth, new_token_info)
                
                # Save the refreshed token
                with open(f'.spotify_cache_{user_id}', 'w') as f:
                    json.dump(new_token_info, f)
                
                logger.info(f"Refreshed token for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh token for user {user_id}: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Use /help to see available commands.")
    else:
        logger.error(f"An error occurred: {error}")
        await ctx.send(f"An error occurred. Please try again later.")

bot.run(TOKEN)