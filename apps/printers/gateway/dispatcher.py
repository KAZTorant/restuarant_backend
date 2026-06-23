import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from apps.printers.gateway.registry import register_pending_job, wait_for_job

logger = logging.getLogger(__name__)


class GatewayOfflineError(Exception):
    pass


class GatewayTimeoutError(Exception):
    pass


def _group_name(location_id) -> str:
    return f'print_gateway_{location_id}'


def send_print_job(text, target, meta=None, location_id=None):
    """
    Send a print_job to the gateway connected for location_id.
    Blocks until print_result or timeout.
    Returns a dict with success, status_code, message, and optional error/printer.
    """
    location_id = location_id or settings.PRINT_GATEWAY_DEFAULT_LOCATION_ID
    meta = meta or {}
    job_id = str(uuid.uuid4())
    timeout = settings.PRINT_GATEWAY_TIMEOUT

    channel_layer = get_channel_layer()
    if channel_layer is None:
        raise GatewayOfflineError('Channel layer is not configured.')

    register_pending_job(job_id)

    payload = {
        'text': text,
        'target': target,
        'meta': meta,
    }

    async_to_sync(channel_layer.group_send)(
        _group_name(location_id),
        {
            'type': 'gateway.print_job',
            'job_id': job_id,
            'payload': payload,
        },
    )

    result = wait_for_job(job_id, timeout)
    if result is None:
        logger.warning(
            'Print gateway timeout location_id=%s job_id=%s timeout=%ss',
            location_id,
            job_id,
            timeout,
        )
        raise GatewayTimeoutError(
            f'Print gateway cavab vermədi ({timeout}s). Gateway qoşulub?'
        )

    return result
