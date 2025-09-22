import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union
from django.db.models import QuerySet, Q
from django.apps import apps
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Service for building Django ORM queries from JSON specifications."""

    # Model mapping for easy access
    MODEL_MAPPING = {
        'Order': 'orders.Order',
        'OrderItem': 'orders.OrderItem',
        'Meal': 'meals.Meal',
        'MealCategory': 'meals.MealCategory',
        'MealGroup': 'meals.MealGroup',
        'Table': 'tables.Table',
        'Room': 'tables.Room',
        'User': 'users.User',
        'Statistics': 'orders.Statistics',
        'Report': 'orders.Report',
        'WorkPeriodConfig': 'orders.WorkPeriodConfig',
    }

    @staticmethod
    @sync_to_async
    def execute_query(query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute query based on JSON specification and return serialized data.

        Args:
            query_spec: Query specification from Gemini

        Returns:
            Dict containing query results and metadata
        """
        try:
            logger.info("=== QUERY EXECUTION START ===")
            logger.info(f"Query specification: {query_spec}")

            models = query_spec.get('models', [])
            if not models:
                logger.error("No models specified in query specification")
                raise ValueError("No models specified in query")

            logger.info(f"Models to query: {models}")
            results = {}

            for model_name in models:
                logger.info(f"Processing model: {model_name}")

                if model_name not in QueryBuilder.MODEL_MAPPING:
                    logger.warning(f"Unknown model: {model_name}")
                    logger.warning(
                        f"Available models: {list(QueryBuilder.MODEL_MAPPING.keys())}")
                    continue

                try:
                    logger.info(f"Querying model: {model_name}")
                    model_data = QueryBuilder._query_single_model(
                        model_name, query_spec)
                    logger.info(
                        f"Query result for {model_name}: {model_data['count']} records")
                    results[model_name] = model_data
                except Exception as e:
                    logger.error(f"Error querying {model_name}: {e}")
                    logger.error(
                        f"Error details: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    results[model_name] = {'error': str(e), 'data': []}

            final_result = {
                'success': True,
                'results': results,
                'query_spec': query_spec,
                'executed_at': datetime.now().isoformat()
            }

            logger.info(
                f"Final query result summary: {len(results)} models processed")
            for model_name, result in results.items():
                if 'error' in result:
                    logger.error(f"{model_name}: ERROR - {result['error']}")
                else:
                    logger.info(f"{model_name}: {result['count']} records")

            logger.info("=== QUERY EXECUTION END ===")
            return final_result

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                'success': False,
                'error': str(e),
                'query_spec': query_spec,
                'executed_at': datetime.now().isoformat()
            }

    @staticmethod
    def _query_single_model(model_name: str, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Query a single model based on specifications."""

        logger.info(f"--- Querying {model_name} ---")

        # Get the model class
        app_label, model_class_name = QueryBuilder.MODEL_MAPPING[model_name].split(
            '.')
        logger.info(
            f"Model mapping: {model_name} -> {app_label}.{model_class_name}")

        model_class = apps.get_model(app_label, model_class_name)
        logger.info(f"Model class loaded: {model_class}")

        # Start with base queryset - use all_orders() for Order model to get all records
        if model_name == 'Order' and hasattr(model_class.objects, 'all_orders'):
            queryset = model_class.objects.all_orders()
            logger.info("Using all_orders() method for Order model")
        else:
            queryset = model_class.objects.all()
            logger.info("Using standard all() method")

        initial_count = queryset.count()
        logger.info(f"Initial queryset count: {initial_count}")

        # Apply filters
        filters = query_spec.get('filters', {})
        if filters:
            logger.info(f"Applying filters: {filters}")
            # Validate filter field names
            QueryBuilder._validate_field_names(
                model_class, model_name, list(filters.keys()))
            queryset = QueryBuilder._apply_filters(queryset, filters)
            after_filters_count = queryset.count()
            logger.info(f"Count after filters: {after_filters_count}")
        else:
            logger.info("No filters to apply")

        # Apply time range filters
        time_range = query_spec.get('time_range', {})
        if time_range:
            logger.info(f"Applying time range: {time_range}")
            queryset = QueryBuilder._apply_time_range(queryset, time_range)
            after_time_count = queryset.count()
            logger.info(f"Count after time range: {after_time_count}")
        else:
            logger.info("No time range to apply")

        # Apply ordering
        ordering = query_spec.get('ordering', {})
        if ordering:
            field = ordering.get('field')
            direction = ordering.get('direction', 'asc')
            if field:
                # Validate ordering field name
                QueryBuilder._validate_field_names(
                    model_class, model_name, [field])
                order_field = f"-{field}" if direction == 'desc' else field
                logger.info(f"Applying ordering: {order_field}")
                queryset = queryset.order_by(order_field)
            else:
                logger.warning("Ordering specified but no field provided")
        else:
            logger.info("No ordering to apply")

        # Apply limit
        limit = query_spec.get('limit')
        if limit and isinstance(limit, int) and limit > 0:
            logger.info(f"Applying limit: {limit}")
            queryset = queryset[:limit]
        else:
            logger.info("No limit to apply")

        # Get specified fields or all fields
        fields = query_spec.get('fields', [])
        logger.info(
            f"Fields to retrieve: {fields if fields else 'all fields'}")

        # Validate field names exist in the model
        if fields:
            QueryBuilder._validate_field_names(model_class, model_name, fields)

        # Execute query and serialize data
        logger.info("Executing final query and serializing data...")
        data = []

        try:
            queryset_list = list(queryset)
            final_count = len(queryset_list)
            logger.info(f"Final queryset executed: {final_count} records")

            for i, obj in enumerate(queryset_list):
                if i < 5:  # Log first 5 objects for debugging
                    logger.debug(f"Processing object {i+1}: {obj}")

                if fields:
                    # Only include specified fields
                    obj_data = {}
                    for field in fields:
                        if hasattr(obj, field):
                            value = getattr(obj, field)
                            obj_data[field] = QueryBuilder._serialize_value(
                                value)
                            if i < 3:  # Log first 3 field values
                                logger.debug(f"  Field {field}: {value}")
                        else:
                            logger.warning(
                                f"Field '{field}' not found in {model_name}")
                else:
                    # Include all fields
                    obj_data = QueryBuilder._serialize_model_instance(obj)
                    if i < 3:  # Log first 3 serialized objects
                        logger.debug(
                            f"  Serialized object: {list(obj_data.keys())}")

                data.append(obj_data)

            result = {
                'model': model_name,
                'count': len(data),
                'data': data
            }

            logger.info(
                f"Model {model_name} query completed: {len(data)} records serialized")
            return result

        except Exception as e:
            logger.error(
                f"Error during queryset execution for {model_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    @staticmethod
    def _apply_filters(queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Apply filters to queryset based on filter specifications."""

        logger.info(f"Applying {len(filters)} filters")

        for field_name, filter_spec in filters.items():
            filter_type = filter_spec.get('type')
            logger.info(f"Applying filter: {field_name} ({filter_type})")

            try:
                if filter_type == 'exact':
                    value = filter_spec.get('value')
                    queryset = queryset.filter(**{field_name: value})

                elif filter_type == 'contains':
                    value = filter_spec.get('value')
                    queryset = queryset.filter(
                        **{f"{field_name}__icontains": value})

                elif filter_type == 'in':
                    values = filter_spec.get('values', [])
                    if values:
                        queryset = queryset.filter(
                            **{f"{field_name}__in": values})

                elif filter_type == 'range':
                    minimum = filter_spec.get('minimum')
                    maximum = filter_spec.get('maximum')
                    if minimum is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__gte": minimum})
                    if maximum is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__lte": maximum})

                elif filter_type == 'gte':
                    value = filter_spec.get('value')
                    if value is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__gte": value})

                elif filter_type == 'lte':
                    value = filter_spec.get('value')
                    if value is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__lte": value})

                elif filter_type == 'gt':
                    value = filter_spec.get('value')
                    if value is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__gt": value})

                elif filter_type == 'lt':
                    value = filter_spec.get('value')
                    if value is not None:
                        queryset = queryset.filter(
                            **{f"{field_name}__lt": value})

                elif filter_type == 'isnull':
                    value = filter_spec.get('value', True)
                    queryset = queryset.filter(
                        **{f"{field_name}__isnull": value})

                else:
                    logger.warning(f"Unknown filter type: {filter_type}")

            except Exception as e:
                logger.error(f"Error applying filter {field_name}: {e}")
                # Continue with other filters

        return queryset

    @staticmethod
    def _apply_time_range(queryset: QuerySet, time_range: Dict[str, Any]) -> QuerySet:
        """Apply time range filters to queryset."""

        time_type = time_range.get('type')
        today = date.today()

        try:
            if time_type == 'today':
                start_date = today
                end_date = today

            elif time_type == 'yesterday':
                start_date = today - timedelta(days=1)
                end_date = start_date

            elif time_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)

            elif time_type == 'last_week':
                start_date = today - timedelta(days=today.weekday() + 7)
                end_date = start_date + timedelta(days=6)

            elif time_type == 'this_month':
                start_date = today.replace(day=1)
                if today.month == 12:
                    end_date = today.replace(
                        year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = today.replace(
                        month=today.month + 1, day=1) - timedelta(days=1)

            elif time_type == 'last_month':
                if today.month == 1:
                    start_date = today.replace(
                        year=today.year - 1, month=12, day=1)
                    end_date = today.replace(day=1) - timedelta(days=1)
                else:
                    start_date = today.replace(month=today.month - 1, day=1)
                    end_date = today.replace(day=1) - timedelta(days=1)

            elif time_type == 'custom':
                start_date_str = time_range.get('start_date')
                end_date_str = time_range.get('end_date')

                if start_date_str:
                    start_date = datetime.strptime(
                        start_date_str, '%Y-%m-%d').date()
                else:
                    start_date = None

                if end_date_str:
                    end_date = datetime.strptime(
                        end_date_str, '%Y-%m-%d').date()
                else:
                    end_date = None

            else:
                logger.warning(f"Unknown time range type: {time_type}")
                return queryset

            # Apply date filters (assuming created_at field exists)
            # Try common date field names
            date_fields = ['created_at', 'date', 'created', 'timestamp']
            date_field = None

            for field in date_fields:
                if hasattr(queryset.model, field):
                    date_field = field
                    break

            if date_field:
                if start_date:
                    queryset = queryset.filter(
                        **{f"{date_field}__date__gte": start_date})
                if end_date:
                    queryset = queryset.filter(
                        **{f"{date_field}__date__lte": end_date})
            else:
                logger.warning(
                    f"No suitable date field found for {queryset.model}")

        except Exception as e:
            logger.error(f"Error applying time range: {e}")

        return queryset

    @staticmethod
    def _serialize_model_instance(obj) -> Dict[str, Any]:
        """Serialize a model instance to a dictionary."""
        data = {}

        for field in obj._meta.fields:
            field_name = field.name
            value = getattr(obj, field_name)
            data[field_name] = QueryBuilder._serialize_value(value)

        return data

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Serialize a value to JSON-compatible format."""
        if value is None:
            return None
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        elif hasattr(value, '__dict__'):
            # For related objects, just return their string representation or ID
            if hasattr(value, 'id'):
                return {'id': value.id, 'str': str(value)}
            return str(value)
        else:
            return value

    @staticmethod
    def _validate_field_names(model_class, model_name: str, field_names: list):
        """
        Validate that all field names exist in the model.
        Raises ValueError with detailed error message if invalid fields found.
        """
        if not field_names:
            return

        # Get all valid field names from the model
        valid_fields = set()
        for field in model_class._meta.get_fields():
            valid_fields.add(field.name)

        # Also add some common lookup suffixes that are valid
        lookup_suffixes = ['__icontains', '__gte',
                           '__lte', '__gt', '__lt', '__in', '__isnull']

        invalid_fields = []
        for field_name in field_names:
            # Remove lookup suffixes for validation
            base_field = field_name.split('__')[0]

            if base_field not in valid_fields:
                invalid_fields.append(field_name)

        if invalid_fields:
            valid_fields_list = sorted(list(valid_fields))
            error_msg = (
                f"Invalid field(s) for {model_name}: {invalid_fields}. "
                f"Valid fields are: {valid_fields_list}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
