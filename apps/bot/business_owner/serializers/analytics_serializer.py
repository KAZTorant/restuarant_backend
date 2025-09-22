import logging
from typing import Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class AnalyticsSerializer:
    """Serializer for preparing data for Gemini analysis."""

    @staticmethod
    def serialize_for_analysis(query_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize query results for Gemini analysis.

        Args:
            query_results: Results from QueryBuilder.execute_query()

        Returns:
            Cleaned and formatted data for analysis
        """
        try:
            logger.info("=== ANALYTICS SERIALIZATION START ===")
            logger.info(
                f"Query results success: {query_results.get('success')}")

            if not query_results.get('success'):
                logger.error(
                    f"Query results failed: {query_results.get('error')}")
                return {
                    'error': query_results.get('error', 'Unknown error'),
                    'data': {}
                }

            results = query_results.get('results', {})
            logger.info(f"Models in results: {list(results.keys())}")

            serialized_data = {}

            for model_name, model_data in results.items():
                logger.info(f"Serializing {model_name}")

                if 'error' in model_data:
                    logger.error(
                        f"{model_name} has error: {model_data['error']}")
                    serialized_data[model_name] = {
                        'error': model_data['error'],
                        'count': 0,
                        'data': []
                    }
                else:
                    logger.info(
                        f"{model_name} has {model_data.get('count', 0)} records")
                    serialized_data[model_name] = AnalyticsSerializer._serialize_model_data(
                        model_name, model_data
                    )

            summary = AnalyticsSerializer._generate_summary(serialized_data)
            logger.info(f"Generated summary: {summary}")

            final_result = {
                'success': True,
                'data': serialized_data,
                'summary': summary,
                'executed_at': query_results.get('executed_at')
            }

            logger.info("=== ANALYTICS SERIALIZATION COMPLETED ===")
            return final_result

        except Exception as e:
            logger.error(f"Error serializing data for analysis: {e}")
            return {
                'error': str(e),
                'data': {}
            }

    @staticmethod
    def _serialize_model_data(model_name: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data for a specific model."""

        data = model_data.get('data', [])
        count = model_data.get('count', 0)

        # Apply model-specific serialization
        if model_name == 'Order':
            return AnalyticsSerializer._serialize_orders(data, count)
        elif model_name == 'OrderItem':
            return AnalyticsSerializer._serialize_order_items(data, count)
        elif model_name == 'Meal':
            return AnalyticsSerializer._serialize_meals(data, count)
        elif model_name == 'Statistics':
            return AnalyticsSerializer._serialize_statistics(data, count)
        else:
            # Generic serialization
            return {
                'count': count,
                'data': data,
                'model': model_name
            }

    @staticmethod
    def _serialize_orders(data: List[Dict], count: int) -> Dict[str, Any]:
        """Serialize order data with analytics-friendly format."""

        total_revenue = 0
        payment_methods = {}
        status_counts = {}
        daily_sales = {}
        archived_count = 0
        active_count = 0

        for order in data:
            # Revenue calculation
            total_price = order.get('total_price', 0)
            if isinstance(total_price, (int, float, Decimal)):
                total_revenue += float(total_price)

            # Payment method analysis
            payment_method = order.get('payment_method', 'unknown')
            payment_methods[payment_method] = payment_methods.get(
                payment_method, 0) + 1

            # Status analysis
            status = order.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

            # Archive status analysis
            is_deleted = order.get('is_deleted', False)
            if is_deleted:
                archived_count += 1
            else:
                active_count += 1

            # Daily sales (if created_at is available)
            created_at = order.get('created_at')
            if created_at:
                try:
                    date_str = created_at.split(
                        'T')[0] if 'T' in created_at else created_at.split(' ')[0]
                    if date_str not in daily_sales:
                        daily_sales[date_str] = {'count': 0, 'revenue': 0}
                    daily_sales[date_str]['count'] += 1
                    daily_sales[date_str]['revenue'] += float(total_price)
                except:
                    pass

        return {
            'count': count,
            'total_revenue': total_revenue,
            'average_order_value': total_revenue / count if count > 0 else 0,
            'payment_methods': payment_methods,
            'status_distribution': status_counts,
            'daily_breakdown': daily_sales,
            'active_orders': active_count,
            'archived_orders': archived_count,
            'raw_data': data
        }

    @staticmethod
    def _serialize_order_items(data: List[Dict], count: int) -> Dict[str, Any]:
        """Serialize order items with analytics focus."""

        total_quantity = 0
        meal_popularity = {}
        total_item_revenue = 0

        for item in data:
            # Quantity analysis
            quantity = item.get('quantity', 0)
            if isinstance(quantity, (int, float)):
                total_quantity += quantity

            # Revenue from items
            price = item.get('price', 0)
            if isinstance(price, (int, float, Decimal)):
                total_item_revenue += float(price) * quantity

            # Meal popularity
            meal_id = None
            if 'meal' in item:
                if isinstance(item['meal'], dict):
                    meal_id = item['meal'].get('id')
                    meal_name = item['meal'].get('str', f"Meal {meal_id}")
                else:
                    meal_id = item['meal']
                    meal_name = f"Meal {meal_id}"

                if meal_id:
                    if meal_name not in meal_popularity:
                        meal_popularity[meal_name] = {
                            'count': 0, 'quantity': 0, 'revenue': 0}
                    meal_popularity[meal_name]['count'] += 1
                    meal_popularity[meal_name]['quantity'] += quantity
                    meal_popularity[meal_name]['revenue'] += float(
                        price) * quantity

        return {
            'count': count,
            'total_quantity': total_quantity,
            'total_revenue': total_item_revenue,
            'average_quantity_per_item': total_quantity / count if count > 0 else 0,
            'meal_popularity': meal_popularity,
            'raw_data': data
        }

    @staticmethod
    def _serialize_meals(data: List[Dict], count: int) -> Dict[str, Any]:
        """Serialize meals data."""

        available_count = 0
        categories = {}
        price_ranges = {'0-10': 0, '10-20': 0, '20-50': 0, '50+': 0}

        for meal in data:
            # Availability
            if meal.get('is_available', False):
                available_count += 1

            # Category analysis
            category = meal.get('category', 'uncategorized')
            if isinstance(category, dict):
                category = category.get('str', 'uncategorized')
            categories[category] = categories.get(category, 0) + 1

            # Price range analysis
            price = meal.get('price', 0)
            if isinstance(price, (int, float, Decimal)):
                price = float(price)
                if price < 10:
                    price_ranges['0-10'] += 1
                elif price < 20:
                    price_ranges['10-20'] += 1
                elif price < 50:
                    price_ranges['20-50'] += 1
                else:
                    price_ranges['50+'] += 1

        return {
            'count': count,
            'available_count': available_count,
            'unavailable_count': count - available_count,
            'categories': categories,
            'price_ranges': price_ranges,
            'raw_data': data
        }

    @staticmethod
    def _serialize_statistics(data: List[Dict], count: int) -> Dict[str, Any]:
        """Serialize statistics data."""

        total_sales = 0
        total_orders = 0
        dates = []

        for stat in data:
            sales = stat.get('total_sales', 0)
            orders = stat.get('order_count', 0)

            if isinstance(sales, (int, float, Decimal)):
                total_sales += float(sales)
            if isinstance(orders, (int, float)):
                total_orders += orders

            date_str = stat.get('date')
            if date_str:
                dates.append(date_str)

        return {
            'count': count,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'average_daily_sales': total_sales / count if count > 0 else 0,
            'average_daily_orders': total_orders / count if count > 0 else 0,
            'date_range': {
                'start': min(dates) if dates else None,
                'end': max(dates) if dates else None
            },
            'raw_data': data
        }

    @staticmethod
    def _generate_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall summary of the data."""

        summary = {
            'models_queried': list(data.keys()),
            'total_records': sum(model_data.get('count', 0) for model_data in data.values()),
            'has_errors': any('error' in model_data for model_data in data.values())
        }

        # Add specific summaries if available
        if 'Order' in data and 'total_revenue' in data['Order']:
            summary['total_revenue'] = data['Order']['total_revenue']
            summary['order_count'] = data['Order']['count']

        if 'Meal' in data:
            summary['meal_count'] = data['Meal']['count']
            summary['available_meals'] = data['Meal'].get('available_count', 0)

        return summary
