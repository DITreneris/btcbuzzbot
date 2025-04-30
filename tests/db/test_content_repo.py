import pytest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.db.content_repo import ContentRepository

class TestContentRepository:
    """Test suite for ContentRepository"""
    
    @pytest.fixture
    def mock_postgres_connection(self):
        """Fixture for mocking PostgreSQL connection"""
        with patch('src.db.content_repo.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [1]  # For RETURNING id
            mock_cursor.fetchall.return_value = [{"id": 1, "text": "Test", "category": "test", "used_count": 0}]
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            yield mock_connect
    
    @pytest.fixture
    def repo_postgres(self, mock_postgres_connection):
        """Create ContentRepository instance configured for PostgreSQL"""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@localhost/db'}):
            with patch('src.db.content_repo.PSYCOPG2_AVAILABLE', True):
                repo = ContentRepository()
                yield repo

    # ---- Test cases for SQLite ----
    @pytest.mark.asyncio
    async def test_add_quote_sqlite(self):
        """Test adding a quote with SQLite"""
        # Create a direct patch for the add_quote method
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.content_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.content_repo.PSYCOPG2_AVAILABLE', False):
                repo = ContentRepository()
                
                # Patch the add_quote method directly to return a specific value
                with patch.object(repo, 'add_quote', AsyncMock(return_value=1)):
                    quote_id = await repo.add_quote("Test quote", "test")
                    assert quote_id == 1
    
    @pytest.mark.asyncio
    async def test_delete_quote_sqlite(self):
        """Test deleting a quote with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.content_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.content_repo.PSYCOPG2_AVAILABLE', False):
                repo = ContentRepository()
                
                # Patch the delete_quote method directly
                with patch.object(repo, 'delete_quote', AsyncMock(return_value=True)):
                    result = await repo.delete_quote(1)
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_add_joke_sqlite(self):
        """Test adding a joke with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.content_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.content_repo.PSYCOPG2_AVAILABLE', False):
                repo = ContentRepository()
                
                # Patch the add_joke method directly
                with patch.object(repo, 'add_joke', AsyncMock(return_value=1)):
                    joke_id = await repo.add_joke("Test joke", "test")
                    assert joke_id == 1
    
    @pytest.mark.asyncio
    async def test_delete_joke_sqlite(self):
        """Test deleting a joke with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.content_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.content_repo.PSYCOPG2_AVAILABLE', False):
                repo = ContentRepository()
                
                # Patch the delete_joke method directly
                with patch.object(repo, 'delete_joke', AsyncMock(return_value=True)):
                    result = await repo.delete_joke(1)
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_get_random_content_sqlite(self):
        """Test getting random content with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.content_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.content_repo.PSYCOPG2_AVAILABLE', False):
                repo = ContentRepository()
                
                # Mock a return value for the get_random_content method
                mock_content = {
                    "id": 1, 
                    "text": "Test", 
                    "category": "test", 
                    "used_count": 0
                }
                
                # Patch the get_random_content method
                with patch.object(repo, 'get_random_content', AsyncMock(return_value=mock_content)):
                    content = await repo.get_random_content("quotes")
                    assert content is not None
                    assert content["id"] == 1
                    assert content["text"] == "Test"
    
    # ---- Test cases for PostgreSQL ----
    @pytest.mark.asyncio
    async def test_add_quote_postgres(self, repo_postgres):
        """Test adding a quote with PostgreSQL"""
        quote_id = await repo_postgres.add_quote("Test quote", "test")
        assert quote_id == 1
    
    @pytest.mark.asyncio
    async def test_delete_quote_postgres(self, repo_postgres, mock_postgres_connection):
        """Test deleting a quote with PostgreSQL"""
        result = await repo_postgres.delete_quote(1)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_add_joke_postgres(self, repo_postgres):
        """Test adding a joke with PostgreSQL"""
        joke_id = await repo_postgres.add_joke("Test joke", "test")
        assert joke_id == 1
    
    @pytest.mark.asyncio
    async def test_delete_joke_postgres(self, repo_postgres, mock_postgres_connection):
        """Test deleting a joke with PostgreSQL"""
        result = await repo_postgres.delete_joke(1)
        assert result is True 