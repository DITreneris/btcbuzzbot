"""
Prompt Template Management Module for BTCBuzzBot

This module handles the storage, retrieval, and formatting of prompt templates
for LLM-based content generation. It provides a clean interface for managing
templates in the database and applying context to them.
"""

import datetime
import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('prompt_templates')

# Try to import database utilities, fallback to mock if not available
try:
    from database import get_db_connection
except ImportError:
    logger.warning("Could not import database module, using mock implementation")
    
    def get_db_connection(db_path=None):
        """Mock implementation for testing"""
        import sqlite3
        return sqlite3.connect(":memory:")


class PromptManager:
    """
    Manager for prompt templates used in LLM content generation.
    Handles storage, retrieval, and formatting of prompts.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the prompt manager.
        
        Args:
            db_path: Path to SQLite database (optional)
        """
        self.db_path = db_path
        self._ensure_table_exists()
        
    def _ensure_table_exists(self) -> None:
        """Ensure the prompt_templates table exists in the database"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_templates'")
            if cursor.fetchone() is None:
                logger.info("Creating prompt_templates table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        template TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_used TEXT,
                        performance_score REAL DEFAULT 0
                    )
                """)
                
                # Create the generation_params table if it doesn't exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='generation_params'")
                if cursor.fetchone() is None:
                    logger.info("Creating generation_params table")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS generation_params (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            post_id INTEGER,
                            model_name TEXT NOT NULL,
                            temperature REAL NOT NULL,
                            max_tokens INTEGER NOT NULL,
                            top_p REAL,
                            prompt_id INTEGER,
                            raw_prompt TEXT,
                            completion_time REAL,
                            created_at TEXT NOT NULL,
                            FOREIGN KEY (post_id) REFERENCES posts(id),
                            FOREIGN KEY (prompt_id) REFERENCES prompt_templates(id)
                        )
                    """)
                
                # Modify posts table if needed (safely)
                try:
                    cursor.execute("PRAGMA table_info(posts)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    if 'is_llm_generated' not in columns:
                        logger.info("Adding is_llm_generated column to posts table")
                        cursor.execute("ALTER TABLE posts ADD COLUMN is_llm_generated BOOLEAN DEFAULT 0")
                        
                    if 'prompt_template_id' not in columns:
                        logger.info("Adding prompt_template_id column to posts table")
                        cursor.execute("ALTER TABLE posts ADD COLUMN prompt_template_id INTEGER")
                        
                    if 'generation_time' not in columns:
                        logger.info("Adding generation_time column to posts table")
                        cursor.execute("ALTER TABLE posts ADD COLUMN generation_time REAL")
                except Exception as e:
                    logger.warning(f"Could not modify posts table: {str(e)}")
                    
                conn.commit()
                
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring tables exist: {str(e)}")
            
    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by ID.
        
        Args:
            template_id: ID of the template to retrieve
            
        Returns:
            Template as dictionary or None if not found
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, template, purpose, created_at, last_used, performance_score "
                "FROM prompt_templates WHERE id = ?", 
                (template_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
                
            return {
                "id": result[0],
                "name": result[1],
                "template": result[2],
                "purpose": result[3],
                "created_at": result[4],
                "last_used": result[5],
                "performance_score": result[6]
            }
        except Exception as e:
            logger.error(f"Error retrieving template {template_id}: {str(e)}")
            return None
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by name.
        
        Args:
            name: Name of the template to retrieve
            
        Returns:
            Template as dictionary or None if not found
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, template, purpose, created_at, last_used, performance_score "
                "FROM prompt_templates WHERE name = ?", 
                (name,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
                
            return {
                "id": result[0],
                "name": result[1],
                "template": result[2],
                "purpose": result[3],
                "created_at": result[4],
                "last_used": result[5],
                "performance_score": result[6]
            }
        except Exception as e:
            logger.error(f"Error retrieving template {name}: {str(e)}")
            return None
    
    def get_template_by_purpose(self, purpose: str) -> Optional[Dict[str, Any]]:
        """
        Get the best template for a specific purpose.
        Selects the template with the highest performance score.
        
        Args:
            purpose: Purpose of the template (e.g., 'price_update', 'joke')
            
        Returns:
            Best template as dictionary or None if not found
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, template, purpose, created_at, last_used, performance_score "
                "FROM prompt_templates WHERE purpose = ? "
                "ORDER BY performance_score DESC LIMIT 1", 
                (purpose,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
                
            return {
                "id": result[0],
                "name": result[1],
                "template": result[2],
                "purpose": result[3],
                "created_at": result[4],
                "last_used": result[5],
                "performance_score": result[6]
            }
        except Exception as e:
            logger.error(f"Error retrieving template for purpose {purpose}: {str(e)}")
            return None
    
    def create_template(self, name: str, template: str, purpose: str) -> Optional[int]:
        """
        Create a new prompt template.
        
        Args:
            name: Name of the template
            template: The prompt template text
            purpose: Purpose of the template (e.g., 'price_update', 'joke')
            
        Returns:
            ID of the created template or None if failed
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO prompt_templates (name, template, purpose, created_at) "
                "VALUES (?, ?, ?, ?)",
                (name, template, purpose, now)
            )
            
            template_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created template '{name}' with ID {template_id}")
            return template_id
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return None
    
    def update_template(self, template_id: int, **kwargs) -> bool:
        """
        Update an existing template.
        
        Args:
            template_id: ID of the template to update
            **kwargs: Fields to update (name, template, purpose, performance_score)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build SET clause dynamically
            set_clause = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['name', 'template', 'purpose', 'performance_score']:
                    set_clause.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clause:
                logger.warning("No valid fields to update")
                return False
                
            query = f"UPDATE prompt_templates SET {', '.join(set_clause)} WHERE id = ?"
            params.append(template_id)
            
            cursor.execute(query, params)
            
            if cursor.rowcount == 0:
                logger.warning(f"Template {template_id} not found for update")
                conn.close()
                return False
                
            conn.commit()
            conn.close()
            
            logger.info(f"Updated template {template_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {str(e)}")
            return False
    
    def delete_template(self, template_id: int) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
            
            if cursor.rowcount == 0:
                logger.warning(f"Template {template_id} not found for deletion")
                conn.close()
                return False
                
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted template {template_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {str(e)}")
            return False
    
    def list_templates(self, purpose: str = None) -> List[Dict[str, Any]]:
        """
        List all templates, optionally filtered by purpose.
        
        Args:
            purpose: Optional purpose to filter by
            
        Returns:
            List of template dictionaries
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            query = ("SELECT id, name, template, purpose, created_at, last_used, performance_score "
                    "FROM prompt_templates")
                    
            params = []
            if purpose:
                query += " WHERE purpose = ?"
                params.append(purpose)
                
            query += " ORDER BY name"
            
            cursor.execute(query, params)
            
            results = cursor.fetchall()
            conn.close()
            
            templates = []
            for row in results:
                templates.append({
                    "id": row[0],
                    "name": row[1],
                    "template": row[2],
                    "purpose": row[3],
                    "created_at": row[4],
                    "last_used": row[5],
                    "performance_score": row[6]
                })
                
            return templates
        except Exception as e:
            logger.error(f"Error listing templates: {str(e)}")
            return []
    
    def format_prompt(self, template_id: int, context: Dict[str, Any]) -> Optional[str]:
        """
        Format a prompt with the given context.
        
        Args:
            template_id: ID of the template to format
            context: Dictionary of context values to insert into template
            
        Returns:
            Formatted prompt string or None if failed
        """
        template = self.get_template(template_id)
        
        if not template:
            logger.error(f"Template with ID {template_id} not found")
            return None
                
        prompt_text = template["template"]
        
        try:
            # Replace placeholders in the template with context values
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                prompt_text = prompt_text.replace(placeholder, str(value))
                
            # Update last_used timestamp
            self.update_template_usage(template_id)
                
            return prompt_text
        except Exception as e:
            logger.error(f"Error formatting template {template_id}: {str(e)}")
            return None
    
    def update_template_usage(self, template_id: int) -> None:
        """
        Update the last_used timestamp for a template.
        
        Args:
            template_id: ID of the template to update
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            cursor.execute(
                "UPDATE prompt_templates SET last_used = ? WHERE id = ?",
                (now, template_id)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating template usage {template_id}: {str(e)}")
    
    def update_performance_score(self, template_id: int, engagement_score: float) -> None:
        """
        Update the performance score for a template based on engagement.
        Uses a rolling average to maintain score stability.
        
        Args:
            template_id: ID of the template to update
            engagement_score: New engagement score (0.0-1.0)
        """
        try:
            template = self.get_template(template_id)
            if not template:
                logger.error(f"Template {template_id} not found for performance update")
                return
                
            # Get current score
            current_score = template["performance_score"] or 0.0
            
            # Calculate new score (70% old, 30% new)
            new_score = (current_score * 0.7) + (engagement_score * 0.3)
            
            # Update in database
            self.update_template(template_id, performance_score=new_score)
            
            logger.info(f"Updated performance score for template {template_id}: {new_score:.3f}")
        except Exception as e:
            logger.error(f"Error updating performance score for {template_id}: {str(e)}")
    
    def log_generation_params(self, 
                             post_id: Optional[int], 
                             model_name: str,
                             temperature: float,
                             max_tokens: int,
                             top_p: float,
                             prompt_id: Optional[int], 
                             raw_prompt: str,
                             completion_time: float) -> Optional[int]:
        """
        Log generation parameters for a post.
        
        Args:
            post_id: ID of the post (can be None for standalone generations)
            model_name: Name of the model used
            temperature: Temperature setting used
            max_tokens: Max tokens setting used
            top_p: Top-p setting used 
            prompt_id: ID of the prompt template used (can be None)
            raw_prompt: The actual prompt text sent to the model
            completion_time: Time taken to generate the content
            
        Returns:
            ID of the logged parameters or None if failed
        """
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            cursor.execute(
                """INSERT INTO generation_params 
                   (post_id, model_name, temperature, max_tokens, top_p, 
                    prompt_id, raw_prompt, completion_time, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (post_id, model_name, temperature, max_tokens, top_p, 
                 prompt_id, raw_prompt, completion_time, now)
            )
            
            params_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return params_id
        except Exception as e:
            logger.error(f"Error logging generation parameters: {str(e)}")
            return None


# Create default templates if running directly
if __name__ == "__main__":
    logger.info("Initializing prompt template manager and creating default templates")
    
    manager = PromptManager()
    
    # Price Update Template
    price_template = """Generate a short, engaging tweet about the current Bitcoin price.
Current price: {price}
24h change: {change_pct}% ({direction})
Market trend: {market_trend}

Make it informative but also add some personality. Include the price, mention the {direction}ward movement, and reflect the {market_trend} sentiment.
Keep it under 280 characters and include hashtags #Bitcoin #BTC at the end.

Tweet:"""

    # Joke Template
    joke_template = """Generate a short, funny joke or pun related to Bitcoin or cryptocurrency. 
Make it witty, original, and suitable for Twitter (under 280 characters).
Include the hashtags #Bitcoin #CryptoHumor at the end.

Joke:"""

    # Motivational Template
    motivational_template = """Generate a short, motivational message for Bitcoin investors and enthusiasts.
{context}Focus on long-term thinking, persistence, and the revolutionary potential of Bitcoin.
Make it inspiring but not overly hyped. Keep it under 280 characters total.
Include hashtags #Bitcoin #HODL at the end.

Motivational message:"""

    # News Commentary Template
    news_template = """Generate a short commentary on this Bitcoin-related news:
{news_headline}

Make it insightful and thoughtful. Avoid hype and keep it balanced.
Keep it under 280 characters total and include hashtags #Bitcoin #Crypto at the end.

Commentary:"""

    # Create the templates if they don't already exist
    existing_templates = manager.list_templates()
    existing_names = [t["name"] for t in existing_templates]
    
    if "Price Update" not in existing_names:
        manager.create_template(
            name="Price Update",
            template=price_template,
            purpose="price_update"
        )
        
    if "Crypto Joke" not in existing_names:
        manager.create_template(
            name="Crypto Joke",
            template=joke_template,
            purpose="joke"
        )
        
    if "Motivational" not in existing_names:
        manager.create_template(
            name="Motivational",
            template=motivational_template,
            purpose="motivation"
        )
        
    if "News Commentary" not in existing_names:
        manager.create_template(
            name="News Commentary",
            template=news_template,
            purpose="news"
        )
        
    logger.info("Default templates created successfully")
    
    # List all templates
    templates = manager.list_templates()
    print("\nAvailable Templates:")
    for template in templates:
        print(f"- {template['name']} (ID: {template['id']}, Purpose: {template['purpose']})") 