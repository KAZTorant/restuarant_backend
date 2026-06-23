import logging

import requests
from django.conf import settings

from apps.printers.gateway.dispatcher import (
    GatewayOfflineError,
    GatewayTimeoutError,
    send_print_job,
)
from apps.printers.models import PrintGatewayLocation

logger = logging.getLogger(__name__)


class GatewayResponse:
    def __init__(self, status_code, ok=None, message='', data=None):
        self.status_code = status_code
        self.ok = ok if ok is not None else 200 <= status_code < 300
        self.message = message
        self.data = data or {}


class PrintGatewayClient:
    @staticmethod
    def send(text, target=None, meta=None, location_id=None):
        if not settings.PRINT_GATEWAY_ENABLED:
            return None

        target = target or {'type': 'main'}
        meta = meta or {}
        location_id = location_id or settings.PRINT_GATEWAY_DEFAULT_LOCATION_ID

        mode = settings.PRINT_GATEWAY_MODE
        if mode == 'http':
            return PrintGatewayClient._send_http(text, target, meta)
        return PrintGatewayClient._send_websocket(text, target, meta, location_id)

    @staticmethod
    def _send_websocket(text, target, meta, location_id):
        if not PrintGatewayLocation.objects.filter(pk=location_id, is_online=True).exists():
            logger.error(
                'Print gateway offline for location_id=%s',
                location_id,
            )
            return GatewayResponse(
                503,
                ok=False,
                message='Print gateway qoşulu deyil.',
            )

        try:
            result = send_print_job(
                text=text,
                target=target,
                meta=meta,
                location_id=location_id,
            )
        except GatewayTimeoutError as exc:
            return GatewayResponse(504, ok=False, message=str(exc))
        except GatewayOfflineError as exc:
            return GatewayResponse(503, ok=False, message=str(exc))

        status_code = result.get('status_code', 500 if not result.get('success') else 200)
        return GatewayResponse(
            status_code,
            ok=result.get('success', False),
            message=result.get('message', ''),
            data=result,
        )

    @staticmethod
    def _send_http(text, target, meta):
        payload = {
            'text': text,
            'target': target,
            'meta': meta,
        }
        try:
            resp = requests.post(
                f'{settings.PRINT_GATEWAY_URL.rstrip("/")}/api/v1/print',
                json=payload,
                headers={
                    'Authorization': f'Bearer {settings.PRINT_GATEWAY_API_KEY}',
                    'Content-Type': 'application/json',
                },
                timeout=settings.PRINT_GATEWAY_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.error('Print gateway HTTP error: %s', exc)
            return GatewayResponse(502, ok=False, message=str(exc))

        try:
            data = resp.json()
        except ValueError:
            data = {}

        message = data.get('message', resp.text)
        return GatewayResponse(resp.status_code, ok=resp.ok, message=message, data=data)
