"""
LLM API Module for BTCBuzzBot

This module provides the Flask API endpoints for interacting with the LLM integration.
It handles requests for content generation, template management, and configuration.
"""

import logging
import os
import json
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('llm_api')

# Import LLM modules, with fallbacks for testing
try:
    from src.llm_integration import OllamaClient, ContentGenerator, initialize_ollama
    from src.prompt_templates import PromptManager
    from src.utils import requires_auth  # Assuming an authentication decorator exists
    from src.database import get_db_connection
except ImportError:
    logger.warning("Running with mock imports - some functionality may be limited")
    
    # Mock authentication decorator
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated
    
    # Try alternative imports
    try:
        from llm_integration import OllamaClient, ContentGenerator, initialize_ollama
        from prompt_templates import PromptManager
    except ImportError:
        logger.error("Could not import LLM modules")
        
        # Mock classes for testing
        class OllamaClient:
            def __init__(self, *args, **kwargs):
                pass
                
            def generate(self, *args, **kwargs):
                return {"text": "Mock generated text", "success": True}
                
        class ContentGenerator:
            def __init__(self, *args, **kwargs):
                pass
                
            def generate_price_update(self, *args, **kwargs):
                return {"text": "Mock price update", "success": True}
                
            def generate_crypto_joke(self, *args, **kwargs):
                return {"text": "Mock joke", "success": True}
                
            def generate_motivational_content(self, *args, **kwargs):
                return {"text": "Mock motivational content", "success": True}
                
        class PromptManager:
            def __init__(self, *args, **kwargs):
                pass
                
            def list_templates(self, *args, **kwargs):
                return [{"id": 1, "name": "Mock Template"}]
                
            def get_template(self, *args, **kwargs):
                return {"id": 1, "name": "Mock Template", "template": "Mock {placeholder}"}
                
            def create_template(self, *args, **kwargs):
                return 1
                
            def update_template(self, *args, **kwargs):
                return True
                
            def delete_template(self, *args, **kwargs):
                return True
                
        def initialize_ollama(*args, **kwargs):
            return OllamaClient()
            
        def get_db_connection(*args, **kwargs):
            import sqlite3
            return sqlite3.connect(":memory:")

# Create Blueprint for LLM API routes
llm_api = Blueprint('llm_api', __name__)

# Initialize global clients if not in testing mode
try:
    client = initialize_ollama()
    content_generator = ContentGenerator(client)
    prompt_manager = PromptManager()
    logger.info("Initialized global LLM clients")
except Exception as e:
    logger.error(f"Failed to initialize global LLM clients: {str(e)}")
    logger.warning("API will attempt to initialize clients on first request")
    client = None
    content_generator = None
    prompt_manager = None

def ensure_clients():
    """Ensure global clients are initialized"""
    global client, content_generator, prompt_manager
    
    if client is None or content_generator is None or prompt_manager is None:
        logger.info("Initializing LLM clients on first request")
        try:
            client = initialize_ollama()
            content_generator = ContentGenerator(client)
            prompt_manager = PromptManager()
            logger.info("Successfully initialized LLM clients")
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients on request: {str(e)}")
            return False
            
    return True

@llm_api.route('/api/v1/generate', methods=['POST'])
@requires_auth
def generate_content():
    """
    Generate content using Ollama LLM.
    
    Expected JSON payload:
    {
        "content_type": "price_update|joke|motivation|custom",
        "context": {
            "price": 45000.0,
            "change_pct": 2.5,
            "direction": "up",
            "market_trend": "bullish",
            ...  # other content-specific context
        },
        "template_id": 1,  # Optional, for custom content
        "parameters": {  # Optional
            "temperature": 0.7,
            "max_tokens": 280
        }
    }
    """
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        content_type = data.get('content_type', 'price_update')
        context = data.get('context', {})
        parameters = data.get('parameters', {})
        
        result = None
        
        # Generate content based on type
        if content_type == 'price_update':
            # Validate required fields
            required_fields = ['price', 'change_pct', 'market_trend']
            missing_fields = [f for f in required_fields if f not in context]
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'Missing required context fields: {", ".join(missing_fields)}'
                }), 400
                
            # Calculate direction if not provided
            if 'direction' not in context:
                context['direction'] = 'up' if context['change_pct'] > 0 else 'down'
                
            result = content_generator.generate_price_update(
                current_price=context['price'],
                change_24h=context['change_pct'],
                market_trend=context['market_trend']
            )
            
        elif content_type == 'joke':
            result = content_generator.generate_crypto_joke()
            
        elif content_type == 'motivation':
            result = content_generator.generate_motivational_content(
                current_price=context.get('price'),
                market_status=context.get('market_trend')
            )
            
        elif content_type == 'custom':
            # Custom generation requires a template_id
            template_id = data.get('template_id')
            
            if not template_id:
                return jsonify({
                    'success': False,
                    'error': 'template_id is required for custom content'
                }), 400
                
            # Get the template
            template = prompt_manager.get_template(template_id)
            
            if not template:
                return jsonify({
                    'success': False,
                    'error': f'Template with ID {template_id} not found'
                }), 404
                
            # Format the prompt
            prompt = prompt_manager.format_prompt(template_id, context)
            
            if not prompt:
                return jsonify({
                    'success': False,
                    'error': 'Failed to format prompt'
                }), 500
                
            # Generate content
            result = client.generate(
                prompt=prompt,
                max_tokens=parameters.get('max_tokens', 280),
                temperature=parameters.get('temperature', 0.7),
                top_p=parameters.get('top_p', 0.9)
            )
            
            # Add template information to result
            result['template'] = {
                'id': template['id'],
                'name': template['name']
            }
            
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown content type: {content_type}'
            }), 400
            
        # Process the result
        if result and result.get('success', False):
            # Validate the content
            is_valid, reason = content_generator.validate_content(result['text'])
            
            if not is_valid:
                logger.warning(f"Generated content validation failed: {reason}")
                result['warning'] = reason
                
            # Log generation params if successful
            if 'prompt' in result:
                prompt_manager.log_generation_params(
                    post_id=None,  # No post ID yet
                    model_name=result.get('model', 'unknown'),
                    temperature=parameters.get('temperature', 0.7),
                    max_tokens=parameters.get('max_tokens', 280),
                    top_p=parameters.get('top_p', 0.9),
                    prompt_id=data.get('template_id'),
                    raw_prompt=result.get('prompt', ''),
                    completion_time=result.get('completion_time', 0.0)
                )
                
            # Return the response
            return jsonify({
                'success': True,
                'content': result['text'],
                'metadata': {
                    'content_type': content_type,
                    'model': result.get('model', 'unknown'),
                    'generation_time': result.get('completion_time', 0.0),
                    'context': context
                }
            })
        else:
            error = result.get('error', 'Unknown error') if result else 'Generation failed'
            logger.error(f"Content generation failed: {error}")
            
            return jsonify({
                'success': False,
                'error': error
            }), 500
            
    except Exception as e:
        logger.error(f"Error in generate_content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/templates', methods=['GET'])
@requires_auth
def list_templates():
    """List all available prompt templates"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        purpose = request.args.get('purpose')
        templates = prompt_manager.list_templates(purpose=purpose)
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Error in list_templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/templates/<int:template_id>', methods=['GET'])
@requires_auth
def get_template(template_id):
    """Get a specific template by ID"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        template = prompt_manager.get_template(template_id)
        
        if not template:
            return jsonify({
                'success': False,
                'error': f'Template with ID {template_id} not found'
            }), 404
            
        return jsonify({
            'success': True,
            'template': template
        })
        
    except Exception as e:
        logger.error(f"Error in get_template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/templates', methods=['POST'])
@requires_auth
def create_template():
    """Create a new prompt template"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        # Validate required fields
        required_fields = ['name', 'template', 'purpose']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
            
        # Create the template
        template_id = prompt_manager.create_template(
            name=data['name'],
            template=data['template'],
            purpose=data['purpose']
        )
        
        if not template_id:
            return jsonify({
                'success': False,
                'error': 'Failed to create template'
            }), 500
            
        return jsonify({
            'success': True,
            'template_id': template_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/templates/<int:template_id>', methods=['PUT'])
@requires_auth
def update_template(template_id):
    """Update an existing template"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        # Update the template
        success = prompt_manager.update_template(
            template_id=template_id,
            **{k: v for k, v in data.items() if k in ['name', 'template', 'purpose', 'performance_score']}
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': f'Failed to update template {template_id}'
            }), 500
            
        return jsonify({
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in update_template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/templates/<int:template_id>', methods=['DELETE'])
@requires_auth
def delete_template(template_id):
    """Delete a template"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        success = prompt_manager.delete_template(template_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': f'Failed to delete template {template_id}'
            }), 500
            
        return jsonify({
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in delete_template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/models', methods=['GET'])
@requires_auth
def list_models():
    """List available Ollama models"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        models = client.get_available_models()
        
        return jsonify({
            'success': True,
            'models': models,
            'current_model': client.model
        })
        
    except Exception as e:
        logger.error(f"Error in list_models: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/models/current', methods=['PUT'])
@requires_auth
def change_model():
    """Change the current Ollama model"""
    if not ensure_clients():
        return jsonify({
            'success': False,
            'error': 'LLM clients not initialized'
        }), 500
        
    try:
        data = request.get_json()
        
        if not data or 'model' not in data:
            return jsonify({
                'success': False,
                'error': 'No model specified'
            }), 400
            
        success = client.change_model(data['model'])
        
        if not success:
            return jsonify({
                'success': False,
                'error': f'Failed to change model to {data["model"]}'
            }), 500
            
        return jsonify({
            'success': True,
            'current_model': client.model
        })
        
    except Exception as e:
        logger.error(f"Error in change_model: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_api.route('/api/v1/status', methods=['GET'])
@requires_auth
def get_status():
    """Get LLM integration status"""
    try:
        status = {
            'initialized': client is not None and content_generator is not None and prompt_manager is not None,
            'ollama_connected': False,
            'current_model': None,
            'templates_count': 0
        }
        
        if status['initialized']:
            # Check Ollama connection
            try:
                models = client.get_available_models()
                status['ollama_connected'] = len(models) > 0
                status['current_model'] = client.model
                status['available_models'] = models
            except Exception:
                status['ollama_connected'] = False
                
            # Check templates
            try:
                templates = prompt_manager.list_templates()
                status['templates_count'] = len(templates)
            except Exception:
                status['templates_count'] = 0
                
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Function to register the blueprint with a Flask app
def register_llm_api(app):
    """Register the LLM API blueprint with a Flask app"""
    app.register_blueprint(llm_api)
    logger.info("Registered LLM API blueprint")
    
    # Register initialization functions if needed
    @app.before_first_request
    def before_first_request():
        ensure_clients()

# If running directly, create a test app
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    register_llm_api(app)
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'LLM API Test Server',
            'endpoints': [
                '/api/v1/generate',
                '/api/v1/templates',
                '/api/v1/models',
                '/api/v1/status'
            ]
        })
    
    app.run(debug=True, port=5000) 