# AI Analytics Bot Setup Guide

## Overview
The AI Analytics feature has been successfully implemented for the restaurant Telegram bot. This feature allows users to ask natural language questions about restaurant data and receive AI-powered analysis.

## Features Implemented

### 1. Command: `/ai_analyze`
- Natural language query processing
- Automated database querying
- AI-powered analysis and reporting
- Support for orders, meals, tables, users, and statistics

### 2. Conversation Flow
1. User triggers `/ai_analyze` command
2. Bot prompts for natural language input
3. Gemini AI analyzes the request and generates database query specifications
4. Django ORM executes queries based on specifications
5. Data is serialized and sent back to Gemini for analysis
6. Bot returns formatted analysis report to user

### 3. Supported Query Types
- Sales statistics and trends
- Popular meals and menu analysis  
- Order status and payment method breakdowns
- Time-based reports (daily, weekly, monthly)
- Table utilization analysis
- User activity reports

## Technical Implementation

### File Structure Created
```
apps/bot/
├── __init__.py
├── apps.py
├── admin.py
├── models.py
├── business_owner/
│   ├── __init__.py
│   ├── commands/
│   │   ├── __init__.py
│   │   └── ai_analyze.py          # Main command handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py      # Gemini API integration
│   │   └── query_builder.py       # ORM query builder
│   └── serializers/
│       ├── __init__.py
│       └── analytics_serializer.py # Data serialization
└── urls.py
```

### Modified Files
- `apps/orders/telegram_bot/bot.py` - Added AI command integration
- `config/settings.py` - Added bot app and Gemini settings
- `apps/urls.py` - Added bot URL patterns
- `requirements.txt` - Added google-generativeai dependency

## Environment Configuration

### Required Environment Variables
Add these to your `.env` file:

```env
# Existing variables
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# New required variable
GEMINI_API_KEY=your-gemini-api-key-here
```

### How to Get Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and add it to your `.env` file

## Installation Steps

### 1. Install Dependencies
```bash
pip install google-generativeai
```

### 2. Set Environment Variables
Create/update your `.env` file with the Gemini API key.

### 3. Run Migrations (if needed)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Start the Bot
```bash
python manage.py run_telegram_bot
```

## Usage Examples

Users can now send natural language queries like:

- "Bu həftənin satış statistikası necədir?" (What are this week's sales statistics?)
- "Ən populyar yeməklər hansılardır?" (What are the most popular meals?)
- "Ödənilməmiş sifarişlər neçədir?" (How many unpaid orders are there?)
- "Bu ayın gəliri keçən ayla müqayisədə necədir?" (How does this month's revenue compare to last month?)
- "Nağd və kartla ödənişlərin nisbəti necədir?" (What's the ratio of cash vs card payments?)

## JSON Query Format

The system uses this JSON structure for database queries:

```json
{
  "instructions": "What to do with the data (analysis goal)",
  "query": {
    "models": ["Order", "OrderItem", "Meal"],
    "fields": ["total_price", "payment_method", "created_at"],
    "filters": {
      "status": {
        "type": "exact",
        "value": "completed"
      }
    },
    "time_range": {
      "type": "this_week"
    },
    "ordering": {
      "field": "created_at",
      "direction": "desc"
    },
    "limit": 100
  }
}
```

## Available Models
- **Order**: Restaurant orders with payment info
- **OrderItem**: Individual items in orders
- **Meal**: Menu items with categories and prices
- **MealCategory**: Categories for organizing meals
- **MealGroup**: Groups for meal organization
- **Table**: Restaurant tables with capacity info
- **Room**: Restaurant rooms/areas
- **User**: System users and roles
- **Statistics**: Daily sales statistics
- **Report**: Work period reports
- **WorkPeriodConfig**: Work period configuration

## Error Handling
- Invalid queries return helpful error messages
- API failures are gracefully handled
- Long responses are split to fit Telegram limits
- User state is properly managed during conversations

## Security Considerations
- Gemini API key should be kept secure
- Consider rate limiting for production use
- User permissions can be added later if needed

## Troubleshooting

### Common Issues
1. **"GEMINI_API_KEY environment variable is required"**
   - Add your Gemini API key to the `.env` file

2. **Import errors**
   - Make sure `google-generativeai` is installed
   - Ensure the bot app is added to INSTALLED_APPS

3. **Query failures**
   - Check database connectivity
   - Verify model names and field names are correct

### Logging
All AI analytics operations are logged. Check Django logs for detailed error information.

## Future Enhancements
- Add user permission checks
- Implement query caching
- Add more sophisticated data visualization
- Support for custom date ranges
- Export functionality for reports
