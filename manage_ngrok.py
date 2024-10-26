#!/usr/bin/env python3
import os
import subprocess
import time
import logging
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('NgrokManager')

def get_ngrok_url():
    """Get the current ngrok URL"""
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()['tunnels']
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    return tunnel['public_url']
        except:
            logger.info(f"Waiting for ngrok to start (attempt {attempt + 1}/{max_attempts})...")
            time.sleep(2)
    return None

def update_env_file(ngrok_url):
    """Update the .env file with new ngrok URL"""
    try:
        load_dotenv()
        new_url = f"{ngrok_url}/callback"
        
        # Read current .env content
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Update or add SPOTIFY_REDIRECT_URI
        redirect_uri_found = False
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('SPOTIFY_REDIRECT_URI='):
                    f.write(f'SPOTIFY_REDIRECT_URI={new_url}\n')
                    redirect_uri_found = True
                else:
                    f.write(line)
            
            if not redirect_uri_found:
                f.write(f'\nSPOTIFY_REDIRECT_URI={new_url}\n')
        
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")

def main():
    try:
        # Kill any existing ngrok processes
        subprocess.run(['pkill', 'ngrok'], stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        # Start ngrok in background
        ngrok_process = subprocess.Popen(['ngrok', 'http', '8888'])
        
        # Wait for ngrok to start and get URL
        logger.info("Starting ngrok and waiting for URL...")
        time.sleep(3)
        ngrok_url = get_ngrok_url()
        
        if not ngrok_url:
            logger.error("Failed to get ngrok URL")
            return
        
        # Update .env file
        callback_url = f"{ngrok_url}/callback"
        update_env_file(ngrok_url)
        
        # Print instructions with clear URL display
        print("\n" + "="*60)
        print("IMPORTANT: UPDATE SPOTIFY DASHBOARD")
        print("="*60)
        print("\nCopy this exact URL to Spotify Dashboard:")
        print("\n" + "="*len(callback_url))
        print(callback_url)
        print("="*len(callback_url) + "\n")
        print("Steps:")
        print("1. Go to https://developer.spotify.com/dashboard")
        print("2. Select your app")
        print("3. Click 'Edit Settings'")
        print("4. Under 'Redirect URIs':")
        print("   - Remove any old URLs")
        print(f"   - Add: {callback_url}")
        print("5. Click 'Save'\n")
        print("="*60)
        print("Keep this terminal open to maintain the ngrok connection")
        print("="*60 + "\n")
        
        # Keep ngrok running
        try:
            ngrok_process.wait()
        except KeyboardInterrupt:
            print("\nShutting down ngrok...")
            ngrok_process.terminate()
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        if 'ngrok_process' in locals():
            ngrok_process.terminate()

if __name__ == "__main__":
    main()