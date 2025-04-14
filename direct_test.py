"""
Direct test of Twitter credentials from .env file
"""
import os
import sys

def mask_string(s):
    """Mask a string for display"""
    if not s:
        return "MISSING"
    if len(s) <= 8:
        return "TOO_SHORT"
    return f"{s[:4]}...{s[-4:]}"

# Function to read .env file manually
def read_env_file():
    """Read .env file and return credentials"""
    env_vars = {}
    
    try:
        if os.path.exists('.env'):
            print(f"Reading .env file from {os.getcwd()}")
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                        except ValueError:
                            pass
        else:
            print("No .env file found!")
    except Exception as e:
        print(f"Error reading .env file: {e}")
    
    return env_vars

def main():
    """Main function"""
    print("\n=== DIRECT TWITTER CREDENTIALS TEST ===\n")
    
    # Read environment variables from .env file
    env_vars = read_env_file()
    
    # Check for Twitter credentials
    twitter_vars = {
        'TWITTER_API_KEY': env_vars.get('TWITTER_API_KEY', ''),
        'TWITTER_API_SECRET': env_vars.get('TWITTER_API_SECRET', ''),
        'TWITTER_ACCESS_TOKEN': env_vars.get('TWITTER_ACCESS_TOKEN', ''),
        'TWITTER_ACCESS_TOKEN_SECRET': env_vars.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    }
    
    # Print masked credentials
    print("Twitter credentials found:")
    for key, value in twitter_vars.items():
        print(f"{key}: {mask_string(value)}")
    
    # Check if all credentials are available
    if all(twitter_vars.values()):
        print("\nAll Twitter credentials found! ✓")
        
        # Try posting a tweet using hardcoded values
        print("\nWriting test script with hardcoded credentials...")
        
        # Create a test file with the actual credentials
        with open('test_direct.py', 'w') as f:
            f.write(f'''
import tweepy

# Credentials from .env file
api_key = "{twitter_vars['TWITTER_API_KEY']}"
api_secret = "{twitter_vars['TWITTER_API_SECRET']}"
access_token = "{twitter_vars['TWITTER_ACCESS_TOKEN']}"
access_token_secret = "{twitter_vars['TWITTER_ACCESS_TOKEN_SECRET']}"

# Set up auth
auth = tweepy.OAuth1UserHandler(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# Create API
api = tweepy.API(auth)

# Post a tweet
try:
    me = api.verify_credentials()
    print(f"Authenticated as @{{me.screen_name}}")
    
    status = api.update_status("BTCBuzzBot direct test! #Bitcoin " + str(__import__('time').time()))
    print(f"Tweet posted with ID: {{status.id}}")
except Exception as e:
    print(f"Error: {{e}}")
''')
        
        print("\nTest script created. Run with: python test_direct.py")
        return True
    else:
        print("\nSome Twitter credentials are missing! ✗")
        missing = [key for key, value in twitter_vars.items() if not value]
        print(f"Missing: {', '.join(missing)}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\nCreated test_direct.py with your credentials")
        print("Run it with: python test_direct.py")
    else:
        print("\nFailed to find all required Twitter credentials")
        sys.exit(1) 