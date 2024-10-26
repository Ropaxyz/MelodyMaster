def create_callback_server():
    """Create callback server if it doesn't exist"""
    if not os.path.exists('callback_server.py'):
        callback_code = '''#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CallbackServer')

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            logger.info(f"Received callback with path: {self.path}")
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path == '/callback':
                # Extract the authorization code
                params = urllib.parse.parse_qs(parsed_path.query)
                logger.info(f"Query parameters: {params}")
                auth_code = params.get('code', [None])[0]
                
                if auth_code:
                    # Save the auth code to a file
                    cache_dir = Path("spotify_caches")
                    cache_dir.mkdir(exist_ok=True)
                    
                    with open(cache_dir / "latest_auth_code.txt", "w") as f:
                        f.write(auth_code)
                    
                    logger.info(f"Saved auth code: {auth_code[:10]}...")
                    
                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = """
    <html>
        <head>
            <title>Spotify Authentication Successful</title>
            <style>
                body { 
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding-top: 50px;
                    background-color: #1DB954;
                    color: white;
                }
                .container {
                    background-color: rgba(0,0,0,0.1);
                    padding: 20px;
                    border-radius: 10px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Successful! ?</h1>
                <p>You can now close this window and return to Discord.</p>
            </div>
        </body>
    </html>
    """
                    self.wfile.write(html.encode())
                    logger.info("Processed callback successfully")
                else:
                    logger.error("No authorization code received")
                    self.send_error(400, "No authorization code received")
            else:
                logger.error(f"Invalid callback path: {parsed_path.path}")
                self.send_error(404)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
            self.send_error(500)

def run():
    server = HTTPServer(('localhost', 8888), CallbackHandler)
    logger.info("Starting callback server on port 8888...")
    server.serve_forever()

if __name__ == "__main__":
    run()'''
        with open('callback_server.py', 'w') as f:
            f.write(callback_code)