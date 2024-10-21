import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')

sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
                        cache_path='.spotify_cache')

# Get the authorization URL
auth_url = sp_oauth.get_authorize_url()
print(f"Please navigate to this URL in a web browser: {auth_url}")

# Wait for the user to enter the redirect URL
redirect_url = input("Enter the URL you were redirected to: ")

# Extract the code from the URL
code = sp_oauth.parse_response_code(redirect_url)

# Get the access token
token_info = sp_oauth.get_access_token(code)

print("Authentication successful!")
print(f"Access token: {token_info['access_token']}")
print("The token has been cached for future use.")