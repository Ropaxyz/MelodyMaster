#!/usr/bin/env python3
import os
import discord
from discord.ext import commands, tasks
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
from enum import Enum
from pathlib import Path
from collections import defaultdict

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'bot.log',
            maxBytes=5*1024*1024,
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SpotifyBot')

def create_progress_bar(progress_ms: int, duration_ms: int) -> tuple[str, str, str]:
    """Create a progress bar with timestamps"""
    progress_percent = (progress_ms / duration_ms) if duration_ms > 0 else 0
    bar_length = 20
    filled_length = int(progress_percent * bar_length)
    bar = '¦' * filled_length + '¦' * (bar_length - filled_length)
    current_time = f"{progress_ms // 60000}:{(progress_ms // 1000 % 60):02d}"
    total_time = f"{duration_ms // 60000}:{(duration_ms // 1000 % 60):02d}"
    return bar, current_time, total_time

class SpotifyError(Exception):
    """Base exception for Spotify-related errors"""
    pass

class RetryableSpotifyError(SpotifyError):
    """Exception for errors that can be retried"""
    pass

class TimeRange(Enum):
    """Time ranges for Spotify statistics"""
    SHORT_TERM = 'short_term'
    MEDIUM_TERM = 'medium_term'
    LONG_TERM = 'long_term'

class Config:
    """Configuration handler for the bot"""
    def __init__(self):
        logger.info("Initializing Config...")
        if not load_dotenv():
            raise EnvironmentError("Failed to load .env file")
            
        required_vars = [
            'DISCORD_BOT_TOKEN',
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET',
            'SPOTIFY_REDIRECT_URI',
            'CHANNEL_ID'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")
            
        self.DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        self.SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
        self.SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
        self.CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

class PlaybackControls(discord.ui.View):
    def __init__(self, spotify_manager: 'SpotifyManager', user_id: int, message: discord.Message = None):
        super().__init__(timeout=None)
        self.spotify_manager = spotify_manager
        self.user_id = user_id
        self.message = message
        self.update_task = None
        self.is_updating = False

    async def start_periodic_updates(self):
        """Start periodic updates of the now playing message"""
        if not self.is_updating:
            self.is_updating = True
            while self.is_updating:
                try:
                    if self.message:
                        await self.update_display()
                    await asyncio.sleep(10)  # Update every 10 seconds
                except Exception as e:
                    logger.error(f"Error in periodic update: {e}")
                    self.is_updating = False
                    break

    async def stop_periodic_updates(self):
        """Stop periodic updates"""
        self.is_updating = False

    async def update_display(self):
        """Update the now playing message with current track info"""
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            current_track = sp.current_user_playing_track()
            
            if not current_track or not current_track.get('item'):
                return
            
            track = current_track['item']
            embed = discord.Embed(
                title="Now Playing",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="Track",
                value=f"**{track['name']}**",
                inline=False
            )
            embed.add_field(
                name="Artist",
                value=track['artists'][0]['name'],
                inline=True
            )
            embed.add_field(
                name="Album",
                value=track['album']['name'],
                inline=True
            )
            
            if current_track['progress_ms'] is not None:
                progress = current_track['progress_ms']
                duration = track['duration_ms']
                bar, current_time, total_time = create_progress_bar(progress, duration)
                embed.add_field(
                    name="Progress",
                    value=f"`{bar}` {current_time}/{total_time}",
                    inline=False
                )
            
            if track['album']['images']:
                embed.set_thumbnail(url=track['album']['images'][0]['url'])
            
            await self.message.edit(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user is authorized to use these controls"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't control someone else's playback!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="\N{BLACK LEFT-POINTING TRIANGLE}", row=0)
    async def previous_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            sp.previous_track()
            await interaction.response.send_message("Previous track", ephemeral=True)
            await asyncio.sleep(1)  # Wait for Spotify to update
            await self.update_display()
        except Exception as e:
            logger.error(f"Previous track error: {e}")
            await interaction.response.send_message("Failed to skip to previous track", ephemeral=True)

    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.primary, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", row=0)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            current_playback = sp.current_playback()
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                await interaction.response.send_message("Playback paused", ephemeral=True)
                button.emoji = "\N{BLACK RIGHT-POINTING TRIANGLE}"
            else:
                sp.start_playback()
                await interaction.response.send_message("Playback resumed", ephemeral=True)
                button.emoji = "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}"
            await self.update_display()
        except Exception as e:
            logger.error(f"Play/Pause error: {e}")
            await interaction.response.send_message("Failed to toggle playback", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            sp.next_track()
            await interaction.response.send_message("Next track", ephemeral=True)
            await asyncio.sleep(1)  # Wait for Spotify to update
            await self.update_display()
        except Exception as e:
            logger.error(f"Next track error: {e}")
            await interaction.response.send_message("Failed to skip track", ephemeral=True)

    @discord.ui.button(label="Volume Down", style=discord.ButtonStyle.secondary, emoji="\N{DOWNWARDS BLACK ARROW}", row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            current_playback = sp.current_playback()
            if current_playback:
                current_volume = current_playback['device']['volume_percent']
                new_volume = max(0, current_volume - 10)
                sp.volume(new_volume)
                await interaction.response.send_message(f"Volume decreased to {new_volume}%", ephemeral=True)
        except Exception as e:
            logger.error(f"Volume down error: {e}")
            await interaction.response.send_message("Failed to lower volume", ephemeral=True)

    @discord.ui.button(label="Volume Up", style=discord.ButtonStyle.secondary, emoji="\N{UPWARDS BLACK ARROW}", row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            sp = await self.spotify_manager.get_client(self.user_id)
            current_playback = sp.current_playback()
            if current_playback:
                current_volume = current_playback['device']['volume_percent']
                new_volume = min(100, current_volume + 10)
                sp.volume(new_volume)
                await interaction.response.send_message(f"Volume set to {new_volume}%", ephemeral=True)
        except Exception as e:
            logger.error(f"Volume up error: {e}")
            await interaction.response.send_message("Failed to increase volume", ephemeral=True)

class SpotifyManager:
    """Manages Spotify authentication and interactions"""
    def __init__(self, config: Config, bot: Optional['SpotifyBot'] = None):
        self.config = config
        self.bot = bot
        self.token_locks = defaultdict(asyncio.Lock)
        self.cache_dir = Path("spotify_caches")
        self.cache_dir.mkdir(exist_ok=True)
        self.track_monitor_tasks: Dict[int, asyncio.Task] = {}
        self.last_tracks: Dict[int, str] = {}

    def _create_oauth(self, user_id: int) -> SpotifyOAuth:
        """Create a SpotifyOAuth instance for the given user"""
        return SpotifyOAuth(
            client_id=self.config.SPOTIFY_CLIENT_ID,
            client_secret=self.config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=self.config.SPOTIFY_REDIRECT_URI,
            scope=" ".join([
                "user-read-currently-playing",
                "user-top-read",
                "user-read-recently-played",
                "playlist-modify-public",
                "playlist-modify-private",
                "user-read-playback-state",
                "user-modify-playback-state"
            ]),
            cache_path=str(self.cache_dir / f'cache-{user_id}'),
            open_browser=False
        )

    async def check_auth_code(self, user_id: int) -> Optional[dict]:
        """Check for and process any new authorization code"""
        temp_file = self.cache_dir / "latest_auth_code.txt"
        try:
            if temp_file.exists():
                auth_code = temp_file.read_text().strip()
                if auth_code:
                    sp_oauth = self._create_oauth(user_id)
                    token_info = sp_oauth.get_access_token(auth_code, as_dict=True)
                    
                    cache_path = self.cache_dir / f'cache-{user_id}'
                    with open(cache_path, 'w') as f:
                        json.dump(token_info, f)
                    
                    temp_file.unlink()
                    await self.start_track_monitor(user_id)
                    await self._send_success_message(user_id)
                    return token_info
        except Exception as e:
            logger.error(f"Error processing auth code: {e}")
        return None

    async def _send_success_message(self, user_id: int):
        """Send success message to user after successful authentication"""
        if self.bot:
            try:
                user = await self.bot.fetch_user(user_id)
                if user:
                    dm_channel = await user.create_dm()
                    embed = discord.Embed(
                        title="? Successfully Connected!",
                        description=(
                            "Your Spotify account has been connected! "
                            "I'll now send you updates when your music changes.\n\n"
                            "**Available Commands:**\n"
                            " `/nowplaying` - Show current track with controls\n"
                            " `/stats` - View your listening statistics\n"
                            " `/recommendations` - Get music recommendations\n"
                            " `/playlist` - Create custom playlists\n"
                            " `/toggle_monitor` - Turn track notifications on/off"
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.set_footer(text="You can use these commands in our DMs!")
                    await dm_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Error sending success message: {e}")

    async def get_client(self, user_id: int, force_refresh: bool = False) -> spotipy.Spotify:
        """Get a Spotify client for the given user"""
        async with self.token_locks[user_id]:
            try:
                token_info = await self.check_auth_code(user_id)
                
                if not token_info:
                    cache_path = self.cache_dir / f'cache-{user_id}'
                    if cache_path.exists():
                        with open(cache_path) as f:
                            token_info = json.load(f)
                    
                if not token_info or force_refresh:
                    auth_url = self._create_oauth(user_id).get_authorize_url()
                    raise ValueError(f"Please authenticate using this URL: {auth_url}")
                
                if self._create_oauth(user_id).is_token_expired(token_info):
                    sp_oauth = self._create_oauth(user_id)
                    token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                    with open(self.cache_dir / f'cache-{user_id}', 'w') as f:
                        json.dump(token_info, f)
                
                return spotipy.Spotify(auth=token_info['access_token'])
                
            except Exception as e:
                logger.error(f"Error in get_client: {e}")
                raise

    async def _monitor_track_changes(self, user_id: int):
        """Monitor a user's currently playing track and send updates"""
        while True:
            try:
                sp = await self.get_client(user_id)
                current_track = sp.current_user_playing_track()
                
                if current_track and current_track.get('item'):
                    track_id = current_track['item']['id']
                    
                    if self.last_tracks.get(user_id) != track_id:
                        self.last_tracks[user_id] = track_id
                        await self._send_track_update(user_id, current_track)
                        
            except Exception as e:
                logger.error(f"Error in track monitor for user {user_id}: {e}")
            
            await asyncio.sleep(10)

    async def _send_track_update(self, user_id: int, current_track: dict):
        """Send track update message to user"""
        try:
            user = await self.bot.fetch_user(user_id)
            dm_channel = await user.create_dm()
            
            track = current_track['item']
            embed = discord.Embed(
                title="Now Playing",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="Track", value=f"**{track['name']}**", inline=False)
            embed.add_field(name="Artist", value=track['artists'][0]['name'], inline=True)
            embed.add_field(name="Album", value=track['album']['name'], inline=True)
            
            if current_track['progress_ms'] is not None:
                progress = current_track['progress_ms']
                duration = track['duration_ms']
                bar, current_time, total_time = create_progress_bar(progress, duration)
                embed.add_field(
                    name="Progress",
                    value=f"`{bar}` {current_time}/{total_time}",
                    inline=False
                )
            
            if track['album']['images']:
                embed.set_thumbnail(url=track['album']['images'][0]['url'])
            
            message = await dm_channel.send(embed=embed)
            view = PlaybackControls(self, user_id, message)
            await message.edit(view=view)
            asyncio.create_task(view.start_periodic_updates())
            
        except Exception as e:
            logger.error(f"Error sending track update for user {user_id}: {e}")

    async def start_track_monitor(self, user_id: int):
        """Start monitoring track changes for a user"""
        if user_id in self.track_monitor_tasks:
            self.track_monitor_tasks[user_id].cancel()
        
        self.track_monitor_tasks[user_id] = asyncio.create_task(
            self._monitor_track_changes(user_id)
        )
        logger.info(f"Started track monitor for user {user_id}")

    async def stop_track_monitor(self, user_id: int):
        """Stop monitoring track changes for a user"""
        if user_id in self.track_monitor_tasks:
            self.track_monitor_tasks[user_id].cancel()
            del self.track_monitor_tasks[user_id]
            logger.info(f"Stopped track monitor for user {user_id}")

class SetupView(discord.ui.View):
    """View for the initial Spotify connection setup"""
    def __init__(self, spotify_manager: SpotifyManager):
        super().__init__(timeout=None)
        self.spotify_manager = spotify_manager

    @discord.ui.button(
        label="Connect Spotify",
        style=discord.ButtonStyle.green,
        custom_id="spotify_setup"
    )
    async def setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Setup button clicked by user {interaction.user.id}")
        try:
            sp_oauth = self.spotify_manager._create_oauth(interaction.user.id)
            auth_url = sp_oauth.get_authorize_url()
            
            embed = discord.Embed(
                title="Connect Your Spotify Account",
                description="Follow these steps to connect your Spotify account:",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="Step 1",
                value="Click the link below to connect your Spotify account:",
                inline=False
            )
            
            embed.add_field(
                name="Authentication Link",
                value=f"[Click Here to Connect Spotify]({auth_url})",
                inline=False
            )
            
            embed.add_field(
                name="Step 2",
                value=(
                    "After authenticating, you'll receive a DM confirming the connection.\n"
                    "Available commands:\n"
                    " `/nowplaying` - Show current track details\n"
                    " `/stats` - View your listening statistics\n"
                    " `/recommendations` - Get music recommendations\n"
                    " `/playlist` - Create custom playlists\n"
                    " `/toggle_monitor` - Turn track notifications on/off"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Setup button error: {e}")
            await interaction.response.send_message(
                "? An error occurred during setup. Please try again later.",
                ephemeral=True
            )

class SpotifyBot(discord.Client):
    """Main Discord bot class"""
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.config = Config()
        self.spotify_manager = SpotifyManager(self.config, self)

    async def setup_hook(self):
        """Initialize bot hooks and commands"""
        logger.info("Setting up bot hooks...")
        self.add_view(SetupView(self.spotify_manager))
        await self.register_commands()
        logger.info("Bot hooks setup completed")

    async def register_commands(self):
        """Register all slash commands"""
        @self.tree.command(
            name="toggle_monitor",
            description="Toggle track change notifications"
        )
        async def toggle_monitor(interaction: discord.Interaction):
            logger.info(f"Toggle monitor command used by {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            try:
                user_id = interaction.user.id
                if user_id in self.spotify_manager.track_monitor_tasks:
                    await self.spotify_manager.stop_track_monitor(user_id)
                    await interaction.followup.send("?? Track notifications disabled", ephemeral=True)
                else:
                    await self.spotify_manager.start_track_monitor(user_id)
                    await interaction.followup.send("?? Track notifications enabled", ephemeral=True)
            except Exception as e:
                logger.error(f"Error in toggle_monitor command: {e}")
                await interaction.followup.send("? An error occurred. Please try again later.", ephemeral=True)

        @self.tree.command(
            name="nowplaying",
            description="Show your currently playing track with controls"
        )
        async def nowplaying(interaction: discord.Interaction):
            logger.info(f"Nowplaying command used by {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            try:
                sp = await self.spotify_manager.get_client(interaction.user.id)
                current_track = sp.current_user_playing_track()
                
                if not current_track or not current_track.get('item'):
                    await interaction.followup.send("No track currently playing!", ephemeral=True)
                    return
                
                track = current_track['item']
                embed = discord.Embed(
                    title="Now Playing",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                
                embed.add_field(
                    name="Track",
                    value=f"**{track['name']}**",
                    inline=False
                )
                embed.add_field(
                    name="Artist",
                    value=track['artists'][0]['name'],
                    inline=True
                )
                embed.add_field(
                    name="Album",
                    value=track['album']['name'],
                    inline=True
                )
                
                if current_track['progress_ms'] is not None:
                    progress = current_track['progress_ms']
                    duration = track['duration_ms']
                    bar, current_time, total_time = create_progress_bar(progress, duration)
                    embed.add_field(
                        name="Progress",
                        value=f"`{bar}` {current_time}/{total_time}",
                        inline=False
                    )
                
                if track['album']['images']:
                    embed.set_thumbnail(url=track['album']['images'][0]['url'])
                
                # Send initial message
                message = await interaction.followup.send(embed=embed, wait=True, ephemeral=True)
                
                # Create view with message reference
                view = PlaybackControls(self.spotify_manager, interaction.user.id, message)
                await message.edit(view=view)
                
                # Start periodic updates
                asyncio.create_task(view.start_periodic_updates())
                
            except ValueError as e:
                if "Please authenticate" in str(e):
                    await interaction.followup.send(str(e), ephemeral=True)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error in nowplaying command: {e}")
                await interaction.followup.send("? An error occurred. Please try again later.", ephemeral=True)

        @self.tree.command(
            name="recommendations",
            description="Get personalized music recommendations"
        )
        async def recommendations(interaction: discord.Interaction, genre: Optional[str] = None):
            logger.info(f"Recommendations command used by {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            try:
                sp = await self.spotify_manager.get_client(interaction.user.id)
                
                top_tracks = sp.current_user_top_tracks(limit=2, time_range='short_term')
                seed_tracks = [track['id'] for track in top_tracks['items']]
                
                top_artists = sp.current_user_top_artists(limit=2, time_range='short_term')
                seed_artists = [artist['id'] for artist in top_artists['items']]
                
                recommendations = sp.recommendations(
                    seed_tracks=seed_tracks[:2],
                    seed_artists=seed_artists[:2],
                    seed_genres=[genre] if genre else [],
                    limit=5
                )
                
                embed = discord.Embed(
                    title="Recommended Tracks",
                    description="Based on your listening history",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                
                for i, track in enumerate(recommendations['tracks'], 1):
                    embed.add_field(
                        name=f"{i}. {track['name']}",
                        value=f"By {track['artists'][0]['name']}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except ValueError as e:
                if "Please authenticate" in str(e):
                    await interaction.followup.send(str(e), ephemeral=True)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error in recommendations command: {e}")
                await interaction.followup.send("? An error occurred. Please try again later.", ephemeral=True)

        @self.tree.command(
            name="playlist",
            description="Create a playlist based on your top tracks"
        )
        async def playlist(interaction: discord.Interaction, name: str, track_count: int = 20):
            logger.info(f"Playlist command used by {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            try:
                sp = await self.spotify_manager.get_client(interaction.user.id)
                
                top_tracks = sp.current_user_top_tracks(
                    limit=track_count,
                    time_range='short_term'
                )
                
                user_id = sp.me()['id']
                playlist = sp.user_playlist_create(
                    user_id,
                    name,
                    description=f"Created by Spotify Bot on {datetime.now().strftime('%Y-%m-%d')}"
                )
                
                track_uris = [track['uri'] for track in top_tracks['items']]
                sp.playlist_add_items(playlist['id'], track_uris)
                
                embed = discord.Embed(
                    title="Playlist Created!",
                    description=f"Created playlist '{name}' with your top {len(track_uris)} tracks",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(
                    name="Playlist Link",
                    value=f"[Click here to open in Spotify]({playlist['external_urls']['spotify']})",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except ValueError as e:
                if "Please authenticate" in str(e):
                    await interaction.followup.send(str(e), ephemeral=True)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error in playlist command: {e}")
                await interaction.followup.send("? An error occurred. Please try again later.", ephemeral=True)

        @self.tree.command(
            name="stats",
            description="Show your listening statistics"
        )
        async def stats(interaction: discord.Interaction):
            logger.info(f"Stats command used by {interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            try:
                sp = await self.spotify_manager.get_client(interaction.user.id)
                
                top_tracks = sp.current_user_top_tracks(limit=5, time_range='short_term')
                top_artists = sp.current_user_top_artists(limit=5, time_range='short_term')
                
                embed = discord.Embed(
                    title="Your Spotify Statistics",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Add top tracks
                tracks_text = ""
                for i, track in enumerate(top_tracks['items'], 1):
                    tracks_text = ""
                for i, track in enumerate(top_tracks['items'], 1):
                    tracks_text += f"{i}. {track['name']} by {track['artists'][0]['name']}\n"
                embed.add_field(
                    name="Your Top Tracks (Last 4 Weeks)",
                    value=tracks_text or "No tracks found",
                    inline=False
                )
                
                # Add top artists
                artists_text = ""
                for i, artist in enumerate(top_artists['items'], 1):
                    artists_text += f"{i}. {artist['name']}\n"
                embed.add_field(
                    name="Your Top Artists (Last 4 Weeks)",
                    value=artists_text or "No artists found",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except ValueError as e:
                if "Please authenticate" in str(e):
                    await interaction.followup.send(str(e), ephemeral=True)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error in stats command: {e}")
                await interaction.followup.send("? An error occurred. Please try again later.", ephemeral=True)

        try:
            logger.info("Syncing application commands globally...")
            await self.tree.sync()
            logger.info("Application commands synced successfully")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            raise

    async def create_setup_message(self, channel_id: int):
        """Create setup message in specified channel"""
        try:
            channel = await self.fetch_channel(channel_id)
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return
                
            logger.info("Deleting old setup messages...")
            async for message in channel.history(limit=100):
                if message.author == self.user:
                    await message.delete()
            
            embed = discord.Embed(
                title="Spotify Bot Setup",
                description="Welcome to the Spotify Bot! Click the button below to connect your Spotify account.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="Features",
                value=(
                    "?? Real-time track updates in DMs\n"
                    "?? Playback controls with buttons\n"
                    "?? Track progress visualization\n"
                    "?? View your listening statistics\n"
                    "?? Get personalized recommendations\n"
                    "?? Create custom playlists\n"
                    "?? Volume control and more!"
                ),
                inline=False
            )
            
            embed.add_field(
                name="How to Connect",
                value=(
                    "1. Click the 'Connect Spotify' button below\n"
                    "2. Follow the authentication link\n"
                    "3. Log in to Spotify and authorize the bot\n"
                    "4. Wait for the confirmation DM\n"
                    "5. Start using commands in our DM chat!"
                ),
                inline=False
            )
            
            embed.set_footer(text="Your Spotify session will be automatically refreshed when needed")
            
            view = SetupView(self.spotify_manager)
            await channel.send(embed=embed, view=view)
            logger.info("Setup message created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating setup message: {e}")
            return False

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        await self.create_setup_message(self.config.CHANNEL_ID)

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new server"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Try to find a suitable channel for the setup message
        channel = None
        
        # First, look for channels with 'bot', 'setup', 'spotify' in the name
        for ch in guild.text_channels:
            if any(keyword in ch.name.lower() for keyword in ['bot', 'setup', 'spotify']):
                channel = ch
                break
        
        # If no specific channel found, try to use the system channel
        if channel is None and guild.system_channel:
            channel = guild.system_channel
        
        # If still no channel, try to use the first text channel we have permission to send in
        if channel is None:
            for ch in guild.text_channels:
                permissions = ch.permissions_for(guild.me)
                if permissions.send_messages and permissions.view_channel:
                    channel = ch
                    break
        
        if channel:
            logger.info(f"Selected channel {channel.name} (ID: {channel.id}) for setup message")
            await self.create_setup_message(channel.id)
            
            # Send welcome message
            welcome_embed = discord.Embed(
                title="Thanks for adding Spotify Bot!",
                description=(
                    "I've set up the bot commands and created a setup message in this channel. "
                    "Users can now connect their Spotify accounts and start using the commands!\n\n"
                    "**Key Features:**\n"
                    "?? Real-time track updates in DMs\n"
                    "?? Interactive playback controls\n"
                    "?? Personal music recommendations\n"
                    "?? Custom playlist generation"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            welcome_embed.set_footer(text="Note: Users need to connect their own Spotify accounts to use the bot")
            
            try:
                await channel.send(embed=welcome_embed)
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")

if __name__ == "__main__":
    try:
        logger.info("Starting Spotify Bot...")
        bot = SpotifyBot()
        bot.run(bot.config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
