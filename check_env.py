"""
Check .env file for Twitter credentials
"""
import os
import sys

def check_env_file():
    """Check if .env file exists and contains required credentials"""
    print("\n===== CHECKING .ENV FILE =====\n")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("ERROR: .env file not found in current directory")
        print(f"Current directory: {os.getcwd()}")
        print("Please create a .env file with your Twitter API credentials")
        return False
    
    print(f"Found .env file in {os.getcwd()}")
    
    # Try to read .env file
    try:
        env_contents = {}
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        env_contents[key] = value
                    except ValueError:
                        print(f"WARNING: Invalid line in .env file: {line}")
        
        # Check for required credentials
        print("\nChecking for Twitter credentials:")
        
        required_keys = [
            'TWITTER_API_KEY',
            'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN',
            'TWITTER_ACCESS_TOKEN_SECRET'
        ]
        
        all_found = True
        for key in required_keys:
            if key in env_contents:
                value = env_contents[key]
                # Show first/last few chars only
                masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "[TOO SHORT]"
                print(f"✓ {key}: {masked_value}")
            else:
                print(f"✗ {key}: MISSING")
                all_found = False
        
        if all_found:
            print("\nAll required Twitter credentials found in .env file")
            return True
        else:
            print("\nERROR: Some required Twitter credentials are missing")
            print("Make sure your .env file contains:")
            print("TWITTER_API_KEY=xxx")
            print("TWITTER_API_SECRET=xxx")
            print("TWITTER_ACCESS_TOKEN=xxx")
            print("TWITTER_ACCESS_TOKEN_SECRET=xxx")
            return False
            
    except Exception as e:
        print(f"ERROR reading .env file: {e}")
        return False

if __name__ == "__main__":
    print("====== TWITTER CREDENTIALS CHECK ======")
    
    result = check_env_file()
    
    print("\n====== CHECK RESULTS ======")
    if result:
        print("✓ SUCCESS: All required Twitter credentials found in .env file")
        sys.exit(0)
    else:
        print("✗ FAILURE: Twitter credentials check failed")
        sys.exit(1) 