"""
Bare minimum tweepy test
"""

try:
    print("Attempting to import tweepy...")
    import tweepy
    print("✅ Tweepy imported successfully!")
    print(f"Tweepy version: {tweepy.__version__}")
except ImportError:
    print("❌ Failed to import tweepy")
    import sys
    print(f"Python path: {sys.path}")

if __name__ == "__main__":
    print("Python version and path check:")
    import sys
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print("Path entries:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}") 