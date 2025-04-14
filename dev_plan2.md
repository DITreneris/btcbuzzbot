# BTCBuzzBot Development Plan 2.0: Ollama LLM Integration

## 🎯 OBJECTIVES

1. Enhance tweet content quality through Ollama LLM integration
2. Automate content generation while maintaining brand voice
3. Reduce manual content creation time by 50%
4. Increase engagement metrics by 40%
5. Establish framework for future ML-driven improvements

## 📋 IMPLEMENTATION OVERVIEW

### Sprint 1: Environment Setup & Model Selection (Week 1-2)

**Tasks:**
1. Install Ollama locally
   - Download and install Ollama
   - Configure system environment
   - Test basic functionality

2. Evaluate candidate models
   - Test Mistral 7B
   - Test Llama-3 8B
   - Test Phi-2 (lightweight option)
   - Benchmark for:
     * Generation quality
     * Response time
     * Resource usage

3. Create Ollama API wrapper
   - Implement REST client for Ollama
   - Create error handling
   - Add retry mechanisms
   - Build caching system

**Deliverables:**
- Working Ollama installation with selected model
- Performance benchmark report
- Basic Python API client implementation
- Model selection recommendation document

**KPIs:**
- Model response time < 2 seconds
- Memory usage < 10GB RAM
- Success rate > 95% for test prompts

### Sprint 2: Prompt Engineering & Content Templates (Week 2-4)

**Tasks:**
1. Design base prompt templates
   - Price update template with context
   - Crypto joke template
   - Motivational content template
   - News commentary template

2. Implement dynamic prompt components
   - Price trend detector (bull/bear/sideways)
   - Market sentiment injector
   - Hashtag generator
   - Brand voice alignment system

3. Create testing framework
   - Automated prompt testing
   - Content output evaluation
   - Character count validation
   - Brand voice consistency checker

**Deliverables:**
- Library of prompt templates
- Dynamic prompt generation system
- Automated testing framework
- Documentation of prompt patterns

**KPIs:**
- 90% of generated tweets under character limit
- 95% content passes brand voice check
- 80% reduction in manual prompt creation time

### Sprint 3: Integration with Bot System (Week 4-6)

**Tasks:**
1. Create content pipeline
   - Connect Ollama API to existing bot
   - Build content validation filter
   - Implement fallback mechanisms
   - Add content storage in database

2. Modify database schema
   - Add LLM generation parameters table
   - Update posts table with generation metadata
   - Create prompt templates table
   - Add performance tracking fields

3. Implement scheduler updates
   - Connect scheduler to LLM pipeline
   - Add configurable generation parameters
   - Implement emergency backup templates
   - Create retry logic for failed generations

**Deliverables:**
- Integrated content generation pipeline
- Updated database schema
- Enhanced scheduler with LLM support
- System architecture documentation

**KPIs:**
- Pipeline processing time < 3 seconds
- 99% scheduler reliability
- 0% system crashes due to LLM integration

### Sprint 4: Testing & Optimization (Week 6-8)

**Tasks:**
1. Implement A/B testing
   - Create testing framework for comparing:
     * Template-based vs. LLM content
     * Different prompt strategies
     * Different posting schedules
   - Build performance tracking
   - Create reporting dashboard

2. Optimize for performance
   - Run generation benchmarks
   - Implement prompt caching where applicable
   - Optimize database queries
   - Add error prediction and prevention

3. Fine-tune content strategy
   - Identify high-performing prompt patterns
   - Adjust content mix ratios
   - Optimize hashtag strategy
   - Refine tone parameters

**Deliverables:**
- A/B testing framework
- Performance optimization report
- Refined content strategy document
- Dashboard for content performance

**KPIs:**
- 40% increase in engagement vs baseline
- 99% uptime for LLM generation system
- < 2% content rejection rate

## 🔧 TECHNICAL IMPLEMENTATION DETAILS

### Database Changes

```sql
-- New tables for LLM integration

-- prompt_templates table
CREATE TABLE prompt_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template TEXT NOT NULL,
    purpose TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_used TEXT,
    performance_score REAL DEFAULT 0
);

-- generation_params table
CREATE TABLE generation_params (
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
);

-- Update posts table
ALTER TABLE posts ADD COLUMN is_llm_generated BOOLEAN DEFAULT 0;
ALTER TABLE posts ADD COLUMN prompt_template_id INTEGER;
ALTER TABLE posts ADD COLUMN generation_time REAL;
```

### API Endpoints

```python
# New API endpoints for LLM integration

@app.route('/api/v1/generate', methods=['POST'])
@requires_auth
def generate_content():
    """Generate content using Ollama LLM"""
    data = request.get_json()
    content_type = data.get('content_type', 'general')
    context = data.get('context', {})
    
    content = generate_llm_content(content_type, context)
    
    return jsonify({
        'success': True,
        'content': content,
        'metadata': {
            'model_used': CURRENT_MODEL,
            'generation_time': content['generation_time'],
            'template_used': content['template_name']
        }
    })

@app.route('/api/v1/templates', methods=['GET'])
@requires_auth
def list_templates():
    """List all available prompt templates"""
    templates = get_all_templates()
    return jsonify({'templates': templates})

@app.route('/api/v1/templates', methods=['POST'])
@requires_auth
def create_template():
    """Create a new prompt template"""
    data = request.get_json()
    template_id = create_prompt_template(
        name=data['name'],
        template=data['template'],
        purpose=data['purpose']
    )
    return jsonify({'success': True, 'template_id': template_id})
```

### Core LLM Integration Module

```python
# src/llm_integration.py

import requests
import time
import json
from typing import Dict, Any, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "mistral:7b"):
        self.base_url = base_url
        self.model = model
        self.generate_endpoint = f"{base_url}/api/generate"
        
    def generate(self, 
                 prompt: str, 
                 max_tokens: int = 280,
                 temperature: float = 0.7,
                 top_p: float = 0.9) -> Dict[str, Any]:
        """Generate text using Ollama API"""
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        try:
            response = requests.post(self.generate_endpoint, json=payload)
            response.raise_for_status()
            completion_time = time.time() - start_time
            
            result = response.json()
            
            return {
                "text": result["response"],
                "completion_time": completion_time,
                "model": self.model,
                "success": True
            }
            
        except Exception as e:
            return {
                "text": "",
                "completion_time": time.time() - start_time,
                "model": self.model,
                "success": False,
                "error": str(e)
            }
```

### Prompt Template System

```python
# src/prompt_templates.py

import datetime
from typing import Dict, Any, List
from database import get_db_connection
import json

class PromptManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        
    def get_template(self, template_id: int) -> Dict[str, Any]:
        """Get a specific template by ID"""
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
    
    def create_template(self, name: str, template: str, purpose: str) -> int:
        """Create a new prompt template"""
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
        
        return template_id
        
    def format_prompt(self, template_id: int, context: Dict[str, Any]) -> str:
        """Format a prompt with the given context"""
        template = self.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
            
        prompt_text = template["template"]
        
        # Replace placeholders in the template with context values
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            prompt_text = prompt_text.replace(placeholder, str(value))
            
        return prompt_text
```

## 🔄 WORKFLOW IMPLEMENTATION

### Content Generation Flow:

1. Scheduler triggers content creation
2. System determines content type needed
3. Context data is gathered:
   - Current BTC price
   - Price trend (24h)
   - Market sentiment
   - Recent post performance
4. Appropriate template is selected
5. Context is injected into template
6. Complete prompt is sent to Ollama
7. Response is validated:
   - Character count check
   - Content policy check
   - Brand voice check
8. Valid content is stored in database
9. Content is posted to Twitter
10. Performance metrics are tracked

### Error Handling Flow:

1. If LLM generation fails:
   - Log error details
   - Retry with simplified prompt
   - If still failing, fall back to template system
2. If content validation fails:
   - Log rejection reason
   - Regenerate with adjusted parameters
   - After 3 failures, use backup template
3. If scheduling fails:
   - Log error and notify admin
   - Implement exponential backoff
   - After 5 failures, disable LLM generation temporarily

## 📊 PERFORMANCE METRICS & KPIs

### Technical KPIs:
- Response time: < 2s average generation time
- Reliability: > 99% successful generations
- Resource usage: < 10GB RAM during operation
- Throughput: Support 4 generations per hour minimum

### Content KPIs:
- Quality: < 5% rejection rate for generated content
- Relevance: > 90% accuracy in price trend commentary
- Brand consistency: > 95% adherence to voice guidelines

### Business KPIs:
- Engagement: 40% increase vs template-based content
- Efficiency: 50% reduction in content creation time
- Growth: 15% follower increase in first 3 months

## 🔄 INTEGRATION WITH EXISTING SYSTEMS

### Database Integration:
- Store templates in database
- Track prompt performance metrics
- Log all LLM interactions
- Maintain content history with metadata

### Admin Interface Updates:
- Add template management UI
- Create prompt testing interface
- Implement A/B testing controls
- Add performance dashboards

### API Infrastructure:
- Create API endpoints for LLM operations
- Implement authentication for template access
- Add monitoring endpoints
- Create content generation history

## ⚠️ RISK MANAGEMENT

### Technical Risks:
- **Resource limitations**: Initially deploy with smaller models (7B parameters or less)
- **API failures**: Implement robust retry logic with exponential backoff
- **Performance degradation**: Set up monitoring and alerting for slow responses

### Content Risks:
- **Inappropriate content**: Implement strict content filtering
- **Inconsistent quality**: Run quality pre-checks before posting
- **Repetitive patterns**: Track and analyze output for sameness

### Operational Risks:
- **Dependency on Ollama**: Create fallback to template system
- **Cost management**: Monitor resource usage closely
- **Model drift**: Regular evaluation of output quality

## 📅 TIMELINE (8 WEEKS)

**Week 1**: Environment setup, model evaluation
**Week 2**: Finalize model selection, API integration
**Week 3**: Prompt template development, testing framework
**Week 4**: Dynamic prompt components, database updates
**Week 5**: Pipeline integration, scheduler modifications
**Week 6**: A/B testing framework, initial performance testing
**Week 7**: Performance optimization, content strategy refinement
**Week 8**: Final testing, documentation, production deployment

---

## 🚀 CURRENT PROGRESS (UPDATED)

### Completed Items:

- ✅ Environment setup completed with Ollama properly installed and configured
- ✅ Model evaluation completed - selected Llama-3 8B as primary model
- ✅ Created Ollama API wrapper with retry mechanisms and error handling
- ✅ Implemented basic prompt templates for different content types
- ✅ Developed the LLM integration module (src/llm_integration.py)
- ✅ Created prompt template system (src/prompt_templates.py)
- ✅ Implemented LLM API client with proper error handling (src/llm_api.py)
- ✅ Updated database schema with new tables for LLM functionality
- ✅ Created scheduler_llm.py to handle LLM-based content generation
- ✅ Added basic admin interface for LLM control (templates/llm_admin.html)
- ✅ Pushed all code to GitHub repository
- ✅ Updated UI with dark theme for better user experience
- ✅ Created comprehensive documentation (README.md)
- ✅ Developed future roadmap with ML/AI enhancements (roadmap.md)

### In Progress:

- 🔄 Integration with Tweet handler (addressing missing tweet_handler module)
- 🔄 A/B testing framework for comparing LLM vs. template-based content
- 🔄 Performance optimization for faster generation times
- 🔄 Content validation and filtering system

### Pending Items:

- ⏳ Dashboard for monitoring content performance
- ⏳ Advanced prompt engineering for market sentiment analysis
- ⏳ Brand voice consistency checker
- ⏳ Production deployment and final testing
- ⏳ Engagement tracking and analytics integration

### Next Steps (Immediate Focus):

1. Complete the tweet_handler integration with proper error handling
2. Implement content validation to ensure quality before posting
3. Develop basic A/B testing framework to compare performance
4. Begin work on the performance dashboard

### Challenges Identified:

- Tweet posting integration needs to be fixed - the tweet_handler module is referenced but missing
- Need to ensure proper error handling for API rate limits
- Resource management for larger LLM models requires optimization
- Content filtering needs additional safeguards

Last updated: 2025-04-14 