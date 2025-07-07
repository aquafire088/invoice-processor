# backend/app.py - Flask/FastAPI Backend Integration
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
from werkzeug.utils import secure_filename
import json
from typing import Dict, Any, List
import asyncio
import aiohttp

# Import your invoice processor
from InvoiceProcessor import InvoiceProcessor, InvoiceProcessingConfig

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize processor
processor = InvoiceProcessor()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ModelAPIClient:
    """Client for communicating with your model API"""
    
    def __init__(self, model_api_url: str, api_key: str = None): # type: ignore
        self.api_url = model_api_url
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    async def call_model(self, prompt: str, is_vision: bool = False) -> Dict[str, Any]:
        """Call your model API with the generated prompt"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "your-model-name",
                    "messages": [{"role": "user", "content": prompt}] if not is_vision else prompt["messages"], # type: ignore
                    "max_tokens": 2000,
                    "temperature": 0.1
                }
                
                async with session.post(
                    self.api_url, 
                    json=payload, 
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Model API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to call model API: {str(e)}")

# Initialize model client (configure with your API details)
#model_client = ModelAPIClient(
#     model_api_url="https://your-model-api-endpoint.com/v1/chat/completions",
#    api_key=os.getenv("MODEL_API_KEY")  # Set this in your environment)

@app.route('/api/invoices/upload', methods=['POST'])
async def upload_and_process():
    """Main endpoint that matches your frontend's fetch request"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get form data (matching your frontend)
        fields = request.form.get('fields', '').split(',')
        output_language = request.form.get('output_language', 'en')
        output_format = request.form.get('output_format', 'json')
        
        if not fields or fields == ['']:
            return jsonify({'error': 'No fields specified'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename) # type: ignore
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Create configuration
            config = InvoiceProcessingConfig(
                fields=fields,
                output_language=output_language,
                output_format=output_format
            )
            
            # Process the file and generate prompt
            result = processor.process_single_invoice(file_path, config)
            
            # Call your model with the generated prompt
            is_vision = result['file_type'] == 'image'
            model_response = await model_client.call_model( # type: ignore
                result['prompt'], 
                is_vision=is_vision
            )
            
            # Parse model response
            extracted_data = parse_model_response(model_response)
            
            # Return response in format expected by frontend
            response_data = {
                'fileName': filename,
                'extractedFields': extracted_data.get('extracted_fields', {}),
                'rawResponse': model_response,
                'promptUsed': result['prompt'] if isinstance(result['prompt'], str) else json.dumps(result['prompt']),
                'confidence': extracted_data.get('confidence_score', 'N/A'),
                'processingNotes': extracted_data.get('processing_notes', '')
            }
            
            return jsonify(response_data)
            
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def parse_model_response(model_response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the model's response to extract structured data"""
    try:
        # Extract content from model response (adjust based on your model's response format)
        content = model_response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Try to parse JSON from the response
        if content.strip().startswith('{'):
            return json.loads(content)
        else:
            # If not JSON, try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    'extracted_fields': {},
                    'confidence_score': '0%',
                    'processing_notes': f'Could not parse model response: {content}'
                }
    except Exception as e:
        return {
            'extracted_fields': {},
            'confidence_score': '0%',
            'processing_notes': f'Error parsing response: {str(e)}'
        }

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'processor': 'ready'})

@app.route('/api/fields', methods=['GET'])
def get_available_fields():
    """Get list of available fields for extraction"""
    return jsonify({
        'fields': processor.common_fields,
        'descriptions': processor.field_descriptions
    })

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/styles.css')
def styles():
    return send_file('styles.css')

@app.route('/app.js')
def app_js():
    return send_file('app.js')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)