import json
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import io
from PIL import Image
import PyPDF2
import fitz  # PyMuPDF for better PDF handling

@dataclass
class InvoiceProcessingConfig:
    """Configuration for invoice processing"""
    fields: List[str]
    output_language: str = "en"
    output_format: str = "json"
    include_line_items: bool = True

class InvoiceProcessor:
    """Main class for processing invoices and generating prompts"""
    
    def __init__(self):
        self.common_fields = [
            'vendor_name',
            'invoice_number', 
            'invoice_date',
            'due_date',
            'total_amount',
            'tax_amount',
            'line_items',
            'item_description',
            'item_quantity',
            'item_unit_price',
            'item_total'
        ]
        
        self.field_descriptions = {
            'vendor_name': 'The name of the company or individual providing the goods/services',
            'invoice_number': 'Unique identifier for this invoice',
            'invoice_date': 'Date when the invoice was issued',
            'due_date': 'Payment due date',
            'total_amount': 'Total amount due including taxes',
            'tax_amount': 'Total tax amount',
            'line_items': 'List of individual items/services with details',
            'item_description': 'Description of each item/service',
            'item_quantity': 'Quantity of each item',
            'item_unit_price': 'Price per unit for each item',
            'item_total': 'Total amount for each line item'
        }
    
    def generate_extraction_prompt(self, config: InvoiceProcessingConfig, 
                                 file_content: str = None,  # type: ignore
                                 file_type: str = "image") -> str:
        """Generate a prompt for invoice field extraction"""
        
        # Build field list with descriptions
        field_list = []
        for field in config.fields:
            description = self.field_descriptions.get(field, f"Extract {field} from the invoice")
            field_list.append(f"- {field}: {description}")
        
        # Create the main prompt
        prompt = f"""You are an expert invoice data extraction system. Analyze the provided invoice document and extract the following information:

REQUIRED FIELDS:
{chr(10).join(field_list)}

EXTRACTION GUIDELINES:
1. Extract information exactly as it appears in the document
2. For dates, use the format found in the document or convert to YYYY-MM-DD if unclear
3. For monetary amounts, include currency symbols and preserve decimal places
4. For line items, extract all available items with their details
5. If a field is not found, use null or empty string
6. Be precise and accurate - double-check all extracted values

OUTPUT FORMAT:
Return the extracted data as a JSON object with the following structure:
{{
    "extracted_fields": {{
        {self._generate_json_structure(config.fields)}
    }},
    "confidence_score": "percentage of confidence in extraction accuracy",
    "processing_notes": "any relevant notes about the extraction process"
}}

LANGUAGE: Extract and return all text in {config.output_language}

IMPORTANT: Only return the JSON object, no additional text or explanations."""

        return prompt
    
    def _generate_json_structure(self, fields: List[str]) -> str:
        """Generate JSON structure template for the prompt"""
        structure_parts = []
        
        for field in fields:
            if field == 'line_items':
                structure_parts.append('"line_items": [\n        {\n            "description": "item description",\n            "quantity": "quantity",\n            "unit_price": "price per unit",\n            "total": "total amount"\n        }\n    ]')
            elif field in ['total_amount', 'tax_amount', 'item_unit_price', 'item_total']:
                structure_parts.append(f'"{field}": "amount with currency"')
            elif field in ['invoice_date', 'due_date']:
                structure_parts.append(f'"{field}": "YYYY-MM-DD"')
            elif field == 'item_quantity':
                structure_parts.append(f'"{field}": "numeric quantity"')
            else:
                structure_parts.append(f'"{field}": "extracted value"')
        
        return ',\n        '.join(structure_parts)
    
    def process_pdf_file(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            # Try with PyMuPDF first (better text extraction)
            doc = fitz.open(file_path) # type: ignore
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e:
                return f"Error extracting PDF text: {str(e)}"
    
    def process_image_file(self, file_path: str) -> str:
        """Convert image to base64 for vision models"""
        try:
            with open(file_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            return f"Error processing image: {str(e)}"
    
    def create_vision_prompt(self, config: InvoiceProcessingConfig, 
                           image_base64: str) -> Dict[str, Any]:
        """Create a prompt structure for vision models"""
        text_prompt = self.generate_extraction_prompt(config)
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }
    
    def process_single_invoice(self, file_path: str, config: InvoiceProcessingConfig) -> Dict[str, Any]:
        """Process a single invoice file and return prompt data"""
        file_extension = file_path.lower().split('.')[-1]
        
        result = {
            "file_path": file_path,
            "config": config,
            "prompt": None,
            "file_type": None,
            "content": None
        }
        
        if file_extension == 'pdf':
            result["file_type"] = "pdf"
            text_content = self.process_pdf_file(file_path)
            result["content"] = text_content
            result["prompt"] = self.generate_extraction_prompt(config, text_content, "pdf")
            
        elif file_extension in ['jpg', 'jpeg', 'png']:
            result["file_type"] = "image"
            image_base64 = self.process_image_file(file_path)
            result["content"] = image_base64
            result["prompt"] = self.create_vision_prompt(config, image_base64)
            
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        return result

# Example usage functions for Google Colab
def create_config_from_selection(selected_fields: List[str], 
                               language: str = "en",
                               format_type: str = "json") -> InvoiceProcessingConfig:
    """Create configuration from field selection (similar to frontend)"""
    return InvoiceProcessingConfig(
        fields=selected_fields,
        output_language=language,
        output_format=format_type
    )

def process_invoice_batch(file_paths: List[str], 
                        config: InvoiceProcessingConfig) -> List[Dict[str, Any]]:
    """Process multiple invoice files"""
    processor = InvoiceProcessor()
    results = []
    
    for file_path in file_paths:
        try:
            result = processor.process_single_invoice(file_path, config)
            results.append(result)
        except Exception as e:
            results.append({
                "file_path": file_path,
                "error": str(e)
            })
    
    return results

# Colab-specific helper functions
def display_extraction_results(results: List[Dict[str, Any]]):
    """Display results in a nice format for Colab"""
    for i, result in enumerate(results, 1):
        print(f"\n{'='*50}")
        print(f"INVOICE {i}: {result.get('file_path', 'Unknown')}")
        print(f"{'='*50}")
        
        if 'error' in result:
            print(f"❌ ERROR: {result['error']}")
            continue
            
        print(f"📄 File Type: {result.get('file_type', 'Unknown')}")
        print(f"🎯 Fields to Extract: {', '.join(result['config'].fields)}")
        
        if result['file_type'] == 'pdf':
            print(f"📝 Text Content Preview: {result['content'][:200]}...")
        
        print(f"\n🤖 PROMPT READY FOR YOUR MODEL:")
        print("-" * 30)
        
        if isinstance(result['prompt'], dict):
            # Vision model prompt
            print("Vision Model Prompt Structure:")
            print(json.dumps(result['prompt'], indent=2))
        else:
            # Text model prompt
            print(result['prompt'])

# Example usage in Colab
def colab_example():
    """Example of how to use this in Google Colab"""
    
    # 1. Create configuration (equivalent to frontend field selection)
    selected_fields = [
        'vendor_name',
        'invoice_number',
        'invoice_date',
        'total_amount',
        'line_items'
    ]
    
    config = create_config_from_selection(
        selected_fields=selected_fields,
        language="en",
        format_type="json"
    )
    
    # 2. Process files
    file_paths = [
        "/content/invoice1.pdf",
        "/content/invoice2.jpg"
    ]
    
    results = process_invoice_batch(file_paths, config)
    
    # 3. Display results
    display_extraction_results(results)
    
    # 4. Use the prompts with your model
    for result in results:
        if 'error' not in result:
            prompt = result['prompt']
            print(f"\n🚀 Ready to send to your model:")
            print(f"File: {result['file_path']}")
            print(f"Prompt type: {'Vision' if isinstance(prompt, dict) else 'Text'}")
            
            # Here you would call your model
            # model_response = your_model.generate(prompt)
            
    return results

if __name__ == "__main__":
    # Run example
    print("Invoice Processing Logic for Google Colab")
    print("Use colab_example() to see how it works!")