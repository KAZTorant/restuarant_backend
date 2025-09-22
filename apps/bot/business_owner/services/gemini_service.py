import json
import logging
import os
from typing import Dict, Any, Optional
import asyncio
from asgiref.sync import sync_to_async

import google.generativeai as genai
from django.conf import settings
from django.apps import apps

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API for restaurant analytics."""

    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=self.api_key)

        # Try different model names in order of preference
        model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        self.model = None

        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info(
                    f"Successfully initialized Gemini model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_name}: {e}")
                continue

        if not self.model:
            raise ValueError(
                "Could not initialize any Gemini model. Please check your API key and model availability.")

    @staticmethod
    def get_model_fields() -> Dict[str, list]:
        """
        Dynamically retrieve all model fields for each available model.

        Returns:
            Dict with model names as keys and list of field info as values
        """
        from apps.bot.business_owner.services.query_builder import QueryBuilder

        model_fields = {}

        for model_name, model_path in QueryBuilder.MODEL_MAPPING.items():
            try:
                app_label, model_class_name = model_path.split('.')
                model_class = apps.get_model(app_label, model_class_name)

                fields_info = []

                # Get all model fields
                for field in model_class._meta.get_fields():
                    # Skip is_deleted fields for Order and OrderItem models
                    # Note: OrderItem has is_deleted_by_administrator which is different and should be included
                    if (model_name in ['Order', 'OrderItem'] and
                            field.name == 'is_deleted'):
                        continue

                    field_info = {
                        'name': field.name,
                        'type': field.__class__.__name__,
                    }

                    # Add field-specific information
                    if hasattr(field, 'verbose_name') and field.verbose_name:
                        field_info['verbose_name'] = field.verbose_name

                    if hasattr(field, 'help_text') and field.help_text:
                        field_info['help_text'] = field.help_text

                    if hasattr(field, 'choices') and field.choices:
                        field_info['choices'] = [choice[0]
                                                 for choice in field.choices]

                    if hasattr(field, 'related_model') and field.related_model:
                        field_info['related_to'] = field.related_model.__name__

                    if hasattr(field, 'default') and field.default is not None:
                        field_info['default'] = str(field.default)

                    if hasattr(field, 'null'):
                        field_info['nullable'] = field.null

                    if hasattr(field, 'blank'):
                        field_info['blank'] = field.blank

                    fields_info.append(field_info)

                model_fields[model_name] = fields_info

            except Exception as e:
                logger.error(
                    f"Error getting fields for model {model_name}: {e}")
                model_fields[model_name] = []

        return model_fields

    @staticmethod
    def format_model_fields_for_prompt() -> str:
        """
        Format model fields information for Gemini prompt.

        Returns:
            Formatted string with model fields information
        """
        model_fields = GeminiService.get_model_fields()

        formatted_text = "Available Models and Their Complete Fields:\n\n"

        for model_name, fields in model_fields.items():
            formatted_text += f"{model_name}: [\n"

            for field in fields:
                field_line = f"  - {field['name']} ({field['type']})"

                # Add related model info
                if 'related_to' in field:
                    field_line += f" -> {field['related_to']}"

                # Add choices info
                if 'choices' in field:
                    choices_str = ', '.join(field['choices'])
                    field_line += f" choices: [{choices_str}]"

                # Add verbose name if available
                if 'verbose_name' in field and field['verbose_name'] != field['name']:
                    field_line += f" ({field['verbose_name']})"

                # Add help text if available
                if 'help_text' in field:
                    field_line += f" - {field['help_text']}"

                formatted_text += field_line + "\n"

            formatted_text += "]\n\n"

        return formatted_text

    @staticmethod
    async def analyze_user_request(user_text: str) -> Dict[str, Any]:
        """
        Analyze user text and return JSON with instructions and query specifications.

        Args:
            user_text: User's natural language request

        Returns:
            Dict containing instructions and query specifications
        """
        service = GeminiService()

        system_prompt = """
        You are a restaurant analytics assistant. Analyze the user's request and return ONLY a JSON response with two main parts:
        
        1. "instructions": What to do with the data (analysis goal)
        2. "query": ORM specifications for data retrieval
        
{GeminiService.format_model_fields_for_prompt()}
        
        CRITICAL FIELD USAGE RULES:
        - ONLY use field names EXACTLY as listed in the model fields above
        - NEVER assume or guess field names that are not explicitly listed
        - NEVER use variations like "table_number" when only "table" exists
        - NEVER use "name" if only "username" exists
        - If you need related model data, use the relationship field (e.g., "table" not "table_number")
        - Always reference the exact field names from the model definitions above
        
        IMPORTANT NOTES:
        - Order and OrderItem models have built-in archiving system (is_deleted field)
        - By default, queries automatically return only non-archived records
        - The is_deleted field is handled internally and not available for direct querying
        - You cannot filter by is_deleted - the system handles this automatically
        - All Order and OrderItem queries return only active (non-archived) records by default
        
        FIELD NAME VALIDATION:
        - Before using any field name in queries, verify it exists in the model field list above
        - Use relationship fields (ForeignKey) to access related data, not assumed field names
        - For table information: use "table" field, not "table_number" or "table_name"
        - For user information: use "waitress" field for Order model
        - For meal information: use "meal" field for OrderItem model
        
        Query JSON Format:
        {
          "models": ["Model names to query"],
          "fields": ["Fields to retrieve"],
          "filters": {
            "field_name": {
              "type": "range|exact|contains|in|isnull|gte|lte|gt|lt",
              "value": "single value for exact/contains/gte/lte/gt/lt/isnull",
              "values": ["array for 'in' type"],
              "minimum": "min value for 'range' type",
              "maximum": "max value for 'range' type"
            }
          },
          "time_range": {
            "type": "last_week|last_month|today|yesterday|this_week|this_month|custom",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
          },
          "ordering": {
            "field": "field to order by",
            "direction": "asc|desc"
          },
          "limit": number
        }
        
        EXAMPLE QUERIES (showing correct field usage):

        Example 1 - Weekly sales (CORRECT field names):
        {
          "instructions": "Analyze weekly sales performance and payment methods",
          "query": {
            "models": ["Order"],
            "fields": ["total_price", "is_paid", "created_at", "waitress", "table"],
            "time_range": {
              "type": "this_week"
            }
          }
        }

        Example 2 - Popular meals (CORRECT field names):
        {
          "instructions": "Find most popular meals by quantity ordered",
          "query": {
            "models": ["OrderItem"],
            "fields": ["quantity", "meal", "price", "order"],
            "ordering": {
              "field": "quantity",
              "direction": "desc"
            },
            "limit": 10
          }
        }

        Example 3 - Table usage analysis (CORRECT - use "table" not "table_number"):
        {
          "instructions": "Analyze table usage patterns",
          "query": {
            "models": ["Order"],
            "fields": ["table", "created_at", "customer_count", "total_price"]
          }
        }

        Return ONLY valid JSON, no explanations or markdown.
        """

        user_prompt = f"""
        User request: "{user_text}"
        
        Analyze this request and return the JSON response for restaurant data analysis.
        """

        try:
            logger.info("=== GEMINI REQUEST START ===")
            logger.info(f"User text: {user_text}")
            logger.debug(
                f"Full system prompt length: {len(system_prompt)} chars")
            logger.debug(f"User prompt: {user_prompt}")

            # Run the synchronous API call in a thread
            response = await sync_to_async(service.model.generate_content)(
                f"{system_prompt}\n\n{user_prompt}")
            response_text = response.text.strip()

            logger.info(f"Raw Gemini response: {response_text}")

            # Clean response if it contains markdown
            if response_text.startswith('```json'):
                response_text = response_text.replace(
                    '```json', '').replace('```', '').strip()
                logger.info("Cleaned JSON markdown from response")
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
                logger.info("Cleaned generic markdown from response")

            logger.info(f"Cleaned response: {response_text}")

            parsed_json = json.loads(response_text)
            logger.info(f"Parsed JSON successfully: {parsed_json}")
            logger.info("=== GEMINI REQUEST END ===")

            return parsed_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {response.text}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise

    @staticmethod
    async def generate_analysis(data: Dict[str, Any], instructions: str) -> str:
        """
        Generate analysis report from data based on instructions.

        Args:
            data: Retrieved data from database
            instructions: Analysis instructions from previous call

        Returns:
            Formatted analysis text for Telegram
        """
        service = GeminiService()

        system_prompt = """
        You are a restaurant analytics expert. Generate a concise, informative analysis report based on the provided data and instructions.
        
        CRITICAL TELEGRAM HTML FORMATTING RULES:
        - ONLY use these HTML tags: <b>, <i>, <u>, <s>, <code>, <pre>
        - NEVER use: <ul>, <li>, <ol>, <div>, <span>, <p>, <br>, <h1>, <h2>, <h3>, etc.
        - For bullet points, use • symbol with line breaks, NOT <li> tags
        - For line breaks, use actual newlines (\n), NOT <br> tags
        - For emphasis, use <b>bold</b> and <i>italic</i> only
        - For numbers/data, use <code>123.45</code>
        - Keep formatting simple and clean
        
        Guidelines:
        - Use emojis and formatting for Telegram
        - Keep responses under 4000 characters (Telegram limit)
        - Include key insights and trends
        - Use bullet points with • symbol for lists
        - Include specific numbers and percentages
        - Suggest actionable recommendations when appropriate
        - Use Azerbaijani language for user-facing text
        - Format numbers with proper currency (AZN) where applicable
        
        Example correct format:
        <b>📊 SATIŞ HESABATI</b>
        
        <b>Əsas Məlumatlar:</b>
        • Ümumi satış: <code>1,250.50 AZN</code>
        • Sifariş sayı: <code>45</code>
        • Orta sifariş dəyəri: <code>27.79 AZN</code>
        
        <b>Tövsiyələr:</b>
        • Populyar yeməkləri artırın
        • Nağd ödənişləri təşviq edin
        
        <i>Qeyd: Bu məlumatlar cari dövr üçündür.</i>
        """

        user_prompt = f"""
        Instructions: {instructions}
        
        Data: {json.dumps(data, indent=2, default=str)}
        
        Generate a comprehensive analysis report in Azerbaijani language using HTML formatting for Telegram.
        """

        try:
            # Run the synchronous API call in a thread
            response = await sync_to_async(service.model.generate_content)(
                f"{system_prompt}\n\n{user_prompt}")

            # Clean the response for Telegram HTML compatibility
            cleaned_response = GeminiService._clean_telegram_html(
                response.text.strip())
            return cleaned_response

        except Exception as e:
            logger.error(f"Error generating analysis: {e}")
            raise

    @staticmethod
    def _clean_telegram_html(text: str) -> str:
        """
        Clean HTML content to be compatible with Telegram's supported HTML tags.
        Remove unsupported tags and replace with Telegram-friendly alternatives.
        """
        import re

        # Remove unsupported HTML tags but keep their content
        unsupported_tags = [
            'ul', 'ol', 'li', 'div', 'span', 'p', 'br', 'hr',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'tr', 'td', 'th',
            'thead', 'tbody', 'tfoot', 'section', 'article', 'header', 'footer'
        ]

        cleaned_text = text

        # Remove opening and closing tags for unsupported elements
        for tag in unsupported_tags:
            # Remove opening tags with any attributes
            cleaned_text = re.sub(
                f'<{tag}[^>]*>', '', cleaned_text, flags=re.IGNORECASE)
            # Remove closing tags
            cleaned_text = re.sub(
                f'</{tag}>', '', cleaned_text, flags=re.IGNORECASE)

        # Replace <br> and <br/> with newlines
        cleaned_text = re.sub(r'<br\s*/?>', '\n',
                              cleaned_text, flags=re.IGNORECASE)

        # Replace <p> tags with double newlines for paragraph separation
        cleaned_text = re.sub(r'<p[^>]*>', '\n\n',
                              cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'</p>', '', cleaned_text, flags=re.IGNORECASE)

        # Convert list items to bullet points
        cleaned_text = re.sub(r'<li[^>]*>', '• ',
                              cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(
            r'</li>', '\n', cleaned_text, flags=re.IGNORECASE)

        # Clean up multiple consecutive newlines
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        # Clean up leading/trailing whitespace
        cleaned_text = cleaned_text.strip()

        return cleaned_text
