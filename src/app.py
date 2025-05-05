import asyncio
import os
import logging
import secrets # For session secret key
from functools import wraps

from flask import (
    Flask, request, jsonify, render_template, 
    session, redirect, url_for, flash # Added render_template, session etc.
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Project Imports
from src.config import Config
from src.main import post_btc_update # Function to trigger posting
from src.auth import authenticate_user, add_admin_user # Assuming auth functions
from src.init import get_shared_instance # Import the getter

# Get shared instances (using the getter)
# We need ContentRepository for admin content management
content_repo = get_shared_instance('ContentRepository')
# Assuming other instances might be needed later
# db_instance = get_shared_instance('Database')
# content_manager = get_shared_instance('ContentManager') 

logger = logging.getLogger(__name__)

# --- Authentication Routes ---

# Decorator to require login for certain routes
def login_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        # Ensure the function is awaited if it's async
        if asyncio.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        else:
            return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
// ... existing code ...
        flash('Invalid credentials', 'error')
    return render_template('login.html') # Assuming login.html exists

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin')
@login_required
def admin_dashboard():
    # Simple placeholder dashboard
    return render_template('admin_dashboard.html') # Assuming admin_dashboard.html exists

# New Routes for Content Management
@app.route('/admin/content', methods=['GET'])
@login_required
async def admin_manage_content():
    """Display quotes and jokes, with forms to add/delete."""
    try:
        quotes = await content_repo.get_all_quotes_async()
        jokes = await content_repo.get_all_jokes_async()
        return render_template('admin_content.html', quotes=quotes, jokes=jokes)
    except Exception as e:
        logger.error(f"Error fetching content for admin page: {e}", exc_info=True)
        flash("Failed to load content data.", "error")
        # Render the template with empty lists on error
        return render_template('admin_content.html', quotes=[], jokes=[])

@app.route('/admin/content/add', methods=['POST'])
@login_required
async def admin_add_content():
    """Handle adding a new quote or joke."""
    content_type = request.form.get('content_type')
    text = request.form.get('text')

    if not text:
        flash("Content text cannot be empty.", "warning")
        return redirect(url_for('admin_manage_content'))

    try:
        if content_type == 'quote':
            added_id = await content_repo.add_quote_async(text)
            if added_id:
                 flash(f'Quote added successfully (ID: {added_id}).', 'success')
            else:
                 flash(f'Failed to add quote.', 'error') # Could be duplicate or DB error
        elif content_type == 'joke':
            added_id = await content_repo.add_joke_async(text)
            if added_id:
                flash(f'Joke added successfully (ID: {added_id}).', 'success')
            else:
                 flash(f'Failed to add joke.', 'error')
        else:
            flash('Invalid content type specified.', 'error')
    except Exception as e:
        logger.error(f"Error adding {content_type}: {e}", exc_info=True)
        flash(f"An error occurred while adding the {content_type}.", "error")

    return redirect(url_for('admin_manage_content'))

@app.route('/admin/content/delete/<string:content_type>/<int:item_id>', methods=['POST'])
@login_required
async def admin_delete_content(content_type, item_id):
    """Handle deleting a specific quote or joke."""
    try:
        deleted = False
        if content_type == 'quote':
            deleted = await content_repo.delete_quote_async(item_id)
        elif content_type == 'joke':
            deleted = await content_repo.delete_joke_async(item_id)
        else:
            flash('Invalid content type for deletion.', 'error')
            return redirect(url_for('admin_manage_content'))

        if deleted:
            flash(f'{content_type.capitalize()} deleted successfully (ID: {item_id}).', 'success')
        else:
            # Could be item not found or DB error
            flash(f'Failed to delete {content_type} (ID: {item_id}). It might not exist.', 'warning') 
            
    except Exception as e:
        logger.error(f"Error deleting {content_type} ID {item_id}: {e}", exc_info=True)
        flash(f"An error occurred while deleting the {content_type}.", "error")

    return redirect(url_for('admin_manage_content'))

# --- API Routes (Example - Keep or Modify) ---
# ... (rest of the file) 