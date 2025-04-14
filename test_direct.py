import sys

print("Starting Twitter API test...")

try:
    import tweepy
    print("Successfully imported tweepy")
except ImportError as e:
    print(f"Failed to import tweepy: {e}")
    print("Installing tweepy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tweepy"])
    import tweepy
    print("Tweepy installed and imported")

print("Setting up Twitter credentials...")
# Credentials from .env file
api_key = "8Cv7D8NHOyUwOFf1LJMwWMH2t"
api_secret = "Mm5FP36hE6Ow1TuAzhZv81zTRHqwXiG0Y7wg1XVFPb0Xo9NU2o"
access_token = "1640064704224899073-5ks80Qb6qJd01fMZm1f6N8JFoQDr2e"
access_token_secret = "pUnUvz6hPWyMnDLXFOiODpFwXQvOoFnXYSucSB2yz"

print(f"API Key: {api_key[:4]}...{api_key[-4:]}")
print(f"API Secret: {api_secret[:4]}...{api_secret[-4:]}")
print(f"Access Token: {access_token[:4]}...{access_token[-4:]}")
print(f"Access Token Secret: {access_token_secret[:4]}...{access_token_secret[-4:]}")

print("Setting up authentication...")
try:
    # Set up auth
    auth = tweepy.OAuth1UserHandler(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    print("Authentication handler created")
except Exception as auth_error:
    print(f"Error creating auth handler: {auth_error}")
    import traceback
    traceback.print_exc()
    exit(1)

print("Creating API instance...")
try:
    # Create API
    api = tweepy.API(auth)
    print("API instance created")
except Exception as api_error:
    print(f"Error creating API: {api_error}")
    import traceback
    traceback.print_exc()
    exit(1)

print("Verifying credentials...")
# Post a tweet
try:
    me = api.verify_credentials()
    print(f"Successfully authenticated as @{me.screen_name}")
    
    tweet_text = f"BTCBuzzBot direct test! #Bitcoin {__import__('time').time()}"
    print(f"Posting tweet: {tweet_text}")
    
    status = api.update_status(tweet_text)
    print(f"Tweet posted successfully with ID: {status.id}")
    print(f"Tweet URL: https://twitter.com/i/web/status/{status.id}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
    # Check for common errors
    error_text = str(e).lower()
    if "duplicate" in error_text:
        print("This appears to be a duplicate tweet error. Twitter doesn't allow posting identical tweets.")
    elif "auth" in error_text or "401" in error_text:
        print("This appears to be an authentication error. Your credentials may be invalid.")
    elif "forbidden" in error_text or "403" in error_text:
        print("This appears to be a permissions error. Make sure your app has 'Write' permissions.")
        
    exit(1)
