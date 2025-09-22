import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from apps.bot.business_owner.services.gemini_service import GeminiService
from apps.bot.business_owner.services.query_builder import QueryBuilder
from apps.bot.business_owner.serializers.analytics_serializer import AnalyticsSerializer

logger = logging.getLogger(__name__)


class AIAnalyzeCommand:
    """Simplified AI Analytics command with continuous chat and consistent back buttons."""

    @staticmethod
    def get_standard_keyboard():
        """Get standard keyboard with back buttons for all AI responses."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔄 Yeni sual", callback_data='new_ai_analyze')],
            [InlineKeyboardButton("🏠 Ana menyu", callback_data='main_menu')]
        ])

    @staticmethod
    async def send_response(update: Update, text: str, keyboard=None):
        """Universal response sender that works for both messages and callbacks."""
        if keyboard is None:
            keyboard = AIAnalyzeCommand.get_standard_keyboard()

        try:
            if update.message:
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode='HTML')
            elif update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    @staticmethod
    async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai_analyze command or new analysis request."""
        logger.info(f"AI analyze started for user: {update.effective_user.id}")

        welcome_text = """<b>🤖 AI ANALİTİK ASİSTANI</b>

📊 <b>Restoran məlumatlarınızı təbii dildə analiz edin!</b>

<b>💡 MƏSAL SUALLAR:</b>
• "Bu həftənin satış statistikası necədir?"
• "Ən populyar yeməklər hansılardır?"
• "Ödənilməmiş sifarişlər neçədir?"
• "Bu ayın gəliri keçən ayla müqayisədə necədir?"
• "Hansı stollar daha çox istifadə olunur?"
• "Nağd və kartla ödənişlərin nisbəti necədir?"

<b>📝 SUALINIZI YAZIN:</b>
<i>Analizdə görmək istədiyiniz məlumatı yazın...</i>"""

        # Set user state for continuous chat
        context.user_data['ai_analyze_active'] = True

        await AIAnalyzeCommand.send_response(update, welcome_text)

    @staticmethod
    async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process user's analysis question."""
        user_text = update.message.text.strip()
        user_id = update.effective_user.id

        logger.info(f"Processing question from user {user_id}: '{user_text}'")

        # Show processing message
        processing_msg = await update.message.reply_text(
            "🤖 <b>ANALİZ EDİLİR...</b>\n\n⏳ <i>Bir neçə saniyə gözləyin...</i>",
            parse_mode='HTML'
        )

        try:
            # Step 1: Analyze with Gemini
            analysis_result = await GeminiService.analyze_user_request(user_text)
            instructions = analysis_result.get('instructions', '')
            query_spec = analysis_result.get('query', {})

            if not instructions or not query_spec:
                await processing_msg.edit_text(
                    "<b>❌ SUAL BAŞA DÜŞÜLMƏDI</b>\n\n"
                    "Daha aydın bir sual verin.\n\n"
                    "<i>Məsələn: 'Bu həftənin satış statistikası necədir?'</i>",
                    reply_markup=AIAnalyzeCommand.get_standard_keyboard(),
                    parse_mode='HTML'
                )
                return

            # Step 2: Execute database query
            await processing_msg.edit_text(
                "🤖 <b>ANALİZ EDİLİR...</b>\n\n"
                "✅ Sorğu anlaşıldı\n"
                "🔍 Məlumatlar toplanır...",
                parse_mode='HTML'
            )

            query_results = await QueryBuilder.execute_query(query_spec)

            if not query_results.get('success'):
                await processing_msg.edit_text(
                    "<b>❌ VERİLƏNLƏR BAZASI XƏTASI</b>\n\n"
                    f"Xəta: {query_results.get('error', 'Naməlum xəta')}\n\n"
                    "<i>Başqa bir sual yoxlayın.</i>",
                    reply_markup=AIAnalyzeCommand.get_standard_keyboard(),
                    parse_mode='HTML'
                )
                return

            # Step 3: Generate analysis
            await processing_msg.edit_text(
                "🤖 <b>ANALİZ EDİLİR...</b>\n\n"
                "✅ Sorğu anlaşıldı\n"
                "✅ Məlumatlar toplandı\n"
                "🧠 AI hesabat hazırlayır...",
                parse_mode='HTML'
            )

            serialized_data = AnalyticsSerializer.serialize_for_analysis(
                query_results)
            analysis_report = await GeminiService.generate_analysis(serialized_data, instructions)

            # Step 4: Send final result with standard keyboard
            await processing_msg.edit_text(
                analysis_report,
                reply_markup=AIAnalyzeCommand.get_standard_keyboard(),
                parse_mode='HTML'
            )

            logger.info("Analysis completed successfully")

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            await processing_msg.edit_text(
                "<b>❌ ANALİZ XƏTASI</b>\n\n"
                f"Texniki xəta: {str(e)[:100]}...\n\n"
                "<i>Yenidən cəhd edin.</i>",
                reply_markup=AIAnalyzeCommand.get_standard_keyboard(),
                parse_mode='HTML'
            )

    @staticmethod
    async def handle_cancel(query):
        """Handle cancel/exit from AI analyze."""
        logger.info("AI analyze cancelled by user")

        text = """<b>✅ AI ANALİZ BAŞA ÇATDI</b>

<i>Yenidən analiz etmək üçün aşağıdakı düymələri istifadə edin.</i>"""

        keyboard = AIAnalyzeCommand.get_standard_keyboard()

        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error handling cancel: {e}")

    @staticmethod
    def is_ai_analyze_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is in continuous AI analyze mode."""
        return context.user_data.get('ai_analyze_active', False)

    @staticmethod
    def deactivate_ai_analyze(context: ContextTypes.DEFAULT_TYPE):
        """Deactivate AI analyze mode."""
        context.user_data.pop('ai_analyze_active', None)
