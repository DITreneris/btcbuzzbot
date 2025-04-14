import pytest
from src.content_manager import ContentManager
from src.database import Database
import os
import asyncio

@pytest.mark.asyncio
async def test_add_quote():
    # Use test database
    db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
    cm = ContentManager(db)
    
    # Add test quote
    quote_text = "Test quote"
    quote_id = await cm.add_quote(quote_text)
    
    # Verify it was added
    result = await db.db.quotes.find_one({"text": quote_text})
    assert result is not None
    assert result["text"] == quote_text
    assert result["used_count"] == 0
    
    # Cleanup
    await db.db.quotes.delete_one({"text": quote_text})
    
@pytest.mark.asyncio
async def test_add_joke():
    # Use test database
    db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
    cm = ContentManager(db)
    
    # Add test joke
    joke_text = "Test joke"
    joke_id = await cm.add_joke(joke_text)
    
    # Verify it was added
    result = await db.db.jokes.find_one({"text": joke_text})
    assert result is not None
    assert result["text"] == joke_text
    assert result["used_count"] == 0
    
    # Cleanup
    await db.db.jokes.delete_one({"text": joke_text})
    
@pytest.mark.asyncio
async def test_get_random_content_empty():
    # Use test database
    db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
    cm = ContentManager(db)
    
    # Clear existing data in test collections
    await db.db.quotes.delete_many({})
    await db.db.jokes.delete_many({})
    
    # Get random content with empty DB
    content = await cm.get_random_content()
    
    # Should return fallback content
    assert content["text"] == "HODL to the moon! 🚀"
    assert content["type"] == "quote"

@pytest.mark.asyncio
async def test_get_random_content():
    # Use test database
    db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
    cm = ContentManager(db)
    
    # Clear existing data
    await db.db.quotes.delete_many({})
    await db.db.jokes.delete_many({})
    
    # Add test data
    await cm.add_quote("Test quote 1")
    await cm.add_joke("Test joke 1")
    
    # Get random content
    content = await cm.get_random_content()
    
    # Verify we got some content
    assert "text" in content
    assert "type" in content
    assert content["type"] in ["quote", "joke"]
    
    # Verify used_count was incremented
    if content["type"] == "quote":
        result = await db.db.quotes.find_one({"text": content["text"]})
    else:
        result = await db.db.jokes.find_one({"text": content["text"]})
    
    assert result["used_count"] == 1
    assert "last_used" in result
    
    # Cleanup
    await db.db.quotes.delete_many({})
    await db.db.jokes.delete_many({})
    
@pytest.mark.asyncio
async def test_add_initial_content():
    # Use test database
    db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
    cm = ContentManager(db)
    
    # Clear existing data
    await db.db.quotes.delete_many({})
    await db.db.jokes.delete_many({})
    
    # Add initial content
    await cm.add_initial_content()
    
    # Verify content was added
    quote_count = await db.db.quotes.count_documents({})
    joke_count = await db.db.jokes.count_documents({})
    
    assert quote_count == 10
    assert joke_count == 10
    
    # Cleanup
    await db.db.quotes.delete_many({})
    await db.db.jokes.delete_many({}) 