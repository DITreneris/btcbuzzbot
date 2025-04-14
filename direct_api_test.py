"""
Direct Twitter API test using requests instead of tweepy
"""
import os
import sys
import time
import hmac
import base64
import hashlib
import urllib.parse
import random
import string

try:
    import requests
    print("Successfully imported requests")
except ImportError:
    print("Installing requests...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
        print("Requests installed successfully")
    except Exception as e:
        print(f"Failed to install requests: {e}")
        print("\nPlease manually install requests with:")
        print("pip install requests")
        sys.exit(1)

# Twitter API credentials
API_KEY = "8Cv7D8NHOyUwOFf1LJMwWMH2t"
API_SECRET = "Mm5FP36hE6Ow1TuAzhZv81zTRHqwXiG0Y7wg1XVFPb0Xo9NU2o"
ACCESS_TOKEN = "1640064704224899073-5ks80Qb6qJd01fMZm1f6N8JFoQDr2e"
ACCESS_TOKEN_SECRET = "pUnUvz6hPWyMnDLXFOiODpFwXQvOoFnXYSucSB2yz"

def percent_encode(string):
    """Percent encode a string for OAuth"""
    return urllib.parse.quote(string, safe='')

def generate_nonce(length=32):
    """Generate a random nonce string for OAuth"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def verify_credentials():
    """Verify Twitter API credentials using GET account/verify_credentials endpoint"""
    print("\nVerifying Twitter API credentials...")
    
    # OAuth parameters
    method = 'GET'
    base_url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
    oauth_timestamp = str(int(time.time()))
    oauth_nonce = generate_nonce()
    
    # Create OAuth parameters dict
    oauth_params = {
        'oauth_consumer_key': API_KEY,
        'oauth_nonce': oauth_nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': oauth_timestamp,
        'oauth_token': ACCESS_TOKEN,
        'oauth_version': '1.0'
    }
    
    # Create parameter string
    param_string = '&'.join([
        f"{percent_encode(k)}={percent_encode(v)}" 
        for k, v in sorted(oauth_params.items())
    ])
    
    # Create signature base string
    signature_base_string = f"{method}&{percent_encode(base_url)}&{percent_encode(param_string)}"
    
    # Create signing key
    signing_key = f"{percent_encode(API_SECRET)}&{percent_encode(ACCESS_TOKEN_SECRET)}"
    
    # Generate signature
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode('utf-8'),
            signature_base_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')
    
    # Add signature to params
    oauth_params['oauth_signature'] = signature
    
    # Create Authorization header
    auth_header = 'OAuth ' + ', '.join([
        f'{percent_encode(k)}="{percent_encode(v)}"' 
        for k, v in sorted(oauth_params.items())
    ])
    
    # Make the request
    headers = {'Authorization': auth_header}
    
    try:
        response = requests.get(base_url, headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ Authentication successful!")
            print(f"Authenticated as: @{user_data.get('screen_name')}")
            return True
        else:
            print(f"✗ Authentication failed with status code: {response.status_code}")
            print(f"Error message: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error making request: {e}")
        return False

def get_api_status():
    """Check Twitter API status"""
    print("\nChecking Twitter API status...")
    
    try:
        response = requests.get('https://api.twitter.com/1.1/help/configuration.json')
        
        if response.status_code == 200:
            print("✓ Twitter API appears to be up and running")
            return True
        elif response.status_code == 401:
            print("✓ Twitter API is responding (with auth error, which is expected)")
            return True
        else:
            print(f"✗ Twitter API returned unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error checking API status: {e}")
        return False

def main():
    """Run main test"""
    print("===== DIRECT TWITTER API TEST =====")
    print(f"Test time: {time.ctime()}")
    
    # Check API credentials
    print("\nTwitter API credentials:")
    print(f"API Key: {API_KEY[:4]}...{API_KEY[-4:]}")
    print(f"API Secret: {API_SECRET[:4]}...{API_SECRET[-4:]}")
    print(f"Access Token: {ACCESS_TOKEN[:4]}...{ACCESS_TOKEN[-4:]}")
    print(f"Access Token Secret: {ACCESS_TOKEN_SECRET[:4]}...{ACCESS_TOKEN_SECRET[-4:]}")
    
    # Check API status
    api_up = get_api_status()
    if not api_up:
        print("\n✗ Twitter API appears to be down or unreachable")
        return False
    
    # Verify credentials
    auth_success = verify_credentials()
    
    if auth_success:
        print("\n✓ Twitter API credentials are valid and working!")
        return True
    else:
        print("\n✗ Twitter API credentials verification failed")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n===== TEST RESULTS =====")
        print("✓ TEST PASSED: Twitter API credentials are working")
        print("You should be able to post tweets with these credentials")
        sys.exit(0)
    else:
        print("\n===== TEST RESULTS =====")
        print("✗ TEST FAILED: There are issues with your Twitter API credentials")
        print("Please check your credentials and Twitter API app settings")
        sys.exit(1) 