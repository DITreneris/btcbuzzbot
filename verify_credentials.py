import os
from dotenv import load_dotenv

def verify_credentials():
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    # Check if credentials exist
    credentials_exist = all([
        api_key, 
        api_secret, 
        access_token, 
        access_token_secret
    ])
    
    # Print results
    print("Twitter Credentials Verification:")
    print(f"API Key exists: {bool(api_key)}")
    print(f"API Secret exists: {bool(api_secret)}")
    print(f"Access Token exists: {bool(access_token)}")
    print(f"Access Token Secret exists: {bool(access_token_secret)}")
    print(f"All credentials exist: {credentials_exist}")
    
    if credentials_exist:
        print("\nCredentials have been successfully saved and loaded!")
    else:
        print("\nSome credentials are missing. Please check your .env file.")

if __name__ == "__main__":
    verify_credentials() 