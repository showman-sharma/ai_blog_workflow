
import os
import requests
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

load_dotenv()

WORDPRESS_CLIENT_ID = os.getenv("WORDPRESS_CLIENT_ID")
WORDPRESS_CLIENT_SECRET = os.getenv("WORDPRESS_CLIENT_SECRET")
WORDPRESS_REDIRECT_URI = os.getenv("WORDPRESS_REDIRECT_URI")

def update_env_with_token(token):
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('WORDPRESS_ACCESS_TOKEN='):
                    lines.append(f'WORDPRESS_ACCESS_TOKEN={token}\n')
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f'WORDPRESS_ACCESS_TOKEN={token}\n')
    with open(env_path, 'w') as f:
        f.writelines(lines)
    print(f".env file updated with new access token.")

def get_wordpress_access_token(auth_code):
    url = "https://public-api.wordpress.com/oauth2/token"
    data = {
        "client_id": WORDPRESS_CLIENT_ID,
        "client_secret": WORDPRESS_CLIENT_SECRET,
        "redirect_uri": WORDPRESS_REDIRECT_URI,
        "grant_type": "authorization_code",
        "code": auth_code
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        print("Your access token is:", token)
        update_env_with_token(token)
        return token
    else:
        print("Error:", response.text)
        return None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        if 'code' in params:
            code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>")
            print("Received authorization code:", code)
            token = get_wordpress_access_token(code)
            print("Add this to your .env file as WORDPRESS_ACCESS_TOKEN=")
            print(token)
            # Stop the server after receiving the code
            def shutdown_server(server):
                server.shutdown()
            import threading
            threading.Thread(target=shutdown_server, args=(self.server,)).start()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error: No code found in URL.</h1></body></html>")

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, OAuthHandler)
    print("Waiting for WordPress authorization redirect...")
    httpd.serve_forever()

def get_wordpress_authorization_url():
    from urllib.parse import urlencode
    params = {
        "client_id": WORDPRESS_CLIENT_ID,
        "redirect_uri": WORDPRESS_REDIRECT_URI,
        "response_type": "code",
        "scope": "global"
    }
    return f"https://public-api.wordpress.com/oauth2/authorize?{urlencode(params)}"

if __name__ == "__main__":
    print("Open the following WordPress authorization URL in your browser and approve the app:")
    print(get_wordpress_authorization_url())
    print("After approval, WordPress will redirect to http://localhost:8000/callback with the code.")
    run_server()
