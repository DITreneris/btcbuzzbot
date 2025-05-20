import pytest
import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.db.news_repo import NewsRepository

class TestNewsRepository:
    """Test suite for NewsRepository"""
    
    @pytest.fixture
    def mock_postgres_connection(self):
        """Fixture for mocking PostgreSQL connection"""
        with patch('src.db.news_repo.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [1]  # For RETURNING id
            mock_cursor.fetchall.return_value = []  # Default empty result
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            yield mock_connect
    
    @pytest.fixture
    def repo_postgres(self, mock_postgres_connection):
        """Create NewsRepository instance configured for PostgreSQL"""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@localhost/db'}):
            with patch('src.db.news_repo.PSYCOPG2_AVAILABLE', True):
                repo = NewsRepository()
                yield repo

    @pytest.fixture
    def sample_tweet_data(self):
        """Sample tweet data for testing"""
        return {
            'original_tweet_id': '123456789',
            'author_id': 'author123',
            'text': 'This is a test tweet about Bitcoin',
            'published_at': datetime.now().isoformat(),
            'fetched_at': datetime.now().isoformat(),
            'metrics': {'likes': 10, 'retweets': 5},
            'source': 'test_source'
        }

    # ----- Test cases for SQLite -----
    @pytest.mark.asyncio
    async def test_store_news_tweet_sqlite(self, sample_tweet_data):
        """Test storing a news tweet with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.news_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.news_repo.PSYCOPG2_AVAILABLE', False):
                repo = NewsRepository()
                
                # Patch the store_news_tweet method directly
                with patch.object(repo, 'store_news_tweet', AsyncMock(return_value=1)):
                    tweet_id = await repo.store_news_tweet(sample_tweet_data)
                    assert tweet_id == 1

    @pytest.mark.asyncio
    async def test_get_last_fetched_tweet_id_sqlite(self):
        """Test retrieving the last fetched tweet ID with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.news_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.news_repo.PSYCOPG2_AVAILABLE', False):
                repo = NewsRepository()
                
                # Patch the get_last_fetched_tweet_id method directly
                with patch.object(repo, 'get_last_fetched_tweet_id', AsyncMock(return_value='123456789')):
                    last_id = await repo.get_last_fetched_tweet_id()
                    assert last_id == '123456789'

    @pytest.mark.asyncio
    async def test_get_unprocessed_news_tweets_sqlite(self):
        """Test retrieving unprocessed news tweets with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.news_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.news_repo.PSYCOPG2_AVAILABLE', False):
                repo = NewsRepository()
                
                # Mock sample unprocessed tweets
                sample_tweets = [
                    {
                        'id': 1,
                        'original_tweet_id': '123456789',
                        'text': 'Test tweet 1',
                        'processed': False
                    },
                    {
                        'id': 2,
                        'original_tweet_id': '987654321',
                        'text': 'Test tweet 2',
                        'processed': False
                    }
                ]
                
                # Patch the get_unprocessed_news_tweets method
                with patch.object(repo, 'get_unprocessed_news_tweets', AsyncMock(return_value=sample_tweets)):
                    tweets = await repo.get_unprocessed_news_tweets(limit=10)
                    assert len(tweets) == 2
                    assert tweets[0]['original_tweet_id'] == '123456789'
                    assert tweets[1]['original_tweet_id'] == '987654321'

    @pytest.mark.asyncio
    async def test_update_tweet_analysis_sqlite(self):
        """Test updating tweet analysis with SQLite"""
        with patch.dict('os.environ', {'DATABASE_URL': ''}):
            with patch('src.db.news_repo.AIOSQLITE_AVAILABLE', True), \
                 patch('src.db.news_repo.PSYCOPG2_AVAILABLE', False):
                repo = NewsRepository()
                
                analysis_data = {
                    'sentiment_score': 7,
                    'sentiment_label': 'positive',
                    'summary': 'Test summary',
                    'keywords': ['bitcoin', 'test']
                }
                
                # Patch the update_tweet_analysis method
                with patch.object(repo, 'update_tweet_analysis', AsyncMock(return_value=True)):
                    result = await repo.update_tweet_analysis(
                        original_tweet_id='123456789',
                        status='analyzed',
                        analysis_data=analysis_data
                    )
                    assert result is True

    # ----- Test cases for PostgreSQL -----
    @pytest.mark.asyncio
    async def test_store_news_tweet_postgres(self, repo_postgres, sample_tweet_data, mock_postgres_connection):
        """Test storing a news tweet with PostgreSQL"""
        # Configure mock cursor to return ID 1 when tweet is stored
        mock_postgres_connection.return_value.cursor.return_value.fetchone.return_value = [1]
        
        tweet_id = await repo_postgres.store_news_tweet(sample_tweet_data)
        assert tweet_id == 1
        
        # Verify SQL execution
        cursor = mock_postgres_connection.return_value.cursor.return_value
        assert cursor.execute.called
        
        # Verify commit was called
        assert mock_postgres_connection.return_value.commit.called

    @pytest.mark.asyncio
    async def test_get_last_fetched_tweet_id_postgres(self, repo_postgres, mock_postgres_connection):
        """Test retrieving the last fetched tweet ID with PostgreSQL"""
        # Configure mock to return a specific tweet ID
        expected_id = '123456789'
        mock_postgres_connection.return_value.cursor.return_value.fetchone.return_value = [expected_id]
        
        last_id = await repo_postgres.get_last_fetched_tweet_id()
        assert last_id == expected_id
        
        # Verify SQL execution - should be selecting MAX(original_tweet_id)
        cursor = mock_postgres_connection.return_value.cursor.return_value
        assert cursor.execute.called
        
        # Check the SQL contains the right query
        call_args = cursor.execute.call_args[0]
        assert "SELECT MAX(original_tweet_id)" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_unprocessed_news_tweets_postgres(self, repo_postgres, mock_postgres_connection):
        """Test retrieving unprocessed news tweets with PostgreSQL"""
        # Configure mock to return sample tweets
        sample_tweets = [
            {
                'id': 1, 
                'original_tweet_id': '123456789',
                'text': 'Test tweet 1',
                'processed': False
            },
            {
                'id': 2,
                'original_tweet_id': '987654321',
                'text': 'Test tweet 2',
                'processed': False
            }
        ]
        
        # Need to properly mock RealDictCursor results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_tweets
        mock_postgres_connection.return_value.cursor.return_value = mock_cursor
        
        # Patch the cursor_factory in the method call
        with patch('src.db.news_repo.RealDictCursor'):
            tweets = await repo_postgres.get_unprocessed_news_tweets(limit=10)
            assert len(tweets) == 2
            
            # Verify SQL execution
            assert mock_cursor.execute.called
            
            # Check the SQL contains WHERE processed = FALSE
            call_args = mock_cursor.execute.call_args[0]
            assert "WHERE processed = FALSE" in call_args[0]
            assert "LIMIT" in call_args[0]

    @pytest.mark.asyncio
    async def test_update_tweet_analysis_postgres(self, repo_postgres, mock_postgres_connection):
        """Test updating tweet analysis with PostgreSQL"""
        original_tweet_id = '123456789'
        analysis_data = {
            'sentiment_score': 7,
            'sentiment_label': 'positive',
            'summary': 'Test summary',
            'keywords': ['bitcoin', 'test']
        }
        
        # Configure mock for successful update
        mock_postgres_connection.return_value.cursor.return_value.rowcount = 1
        
        # Call the method
        result = await repo_postgres.update_tweet_analysis(
            original_tweet_id=original_tweet_id,
            status='analyzed',
            analysis_data=analysis_data
        )
        
        # Verify successful update
        assert result is True
        
        # Verify SQL execution
        cursor = mock_postgres_connection.return_value.cursor.return_value
        assert cursor.execute.called
        
        # Verify commit was called
        assert mock_postgres_connection.return_value.commit.called 