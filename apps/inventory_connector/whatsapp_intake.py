import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from inventory.models import InventoryItem, InventoryRecord, InventryCategory

logger = logging.getLogger(__name__)

UNIT_MAP = {
    'kg': 'kg',
    'kq': 'kg',
    'kilo': 'kg',
    'l': 'l',
    'lt': 'l',
    'litr': 'l',
    'litre': 'l',
    'eded': 'pcs',
    'ed': 'pcs',
    'ad': 'pcs',
    'pcs': 'pcs',
    'ədəd': 'pcs',
    'əd': 'pcs',
    'package': 'package',
    'baglama': 'package',
    'bağlama': 'package',
    'bag': 'package',
}

_UNIT_ALT = (
    r'kq|kg|kilo|litr|litre|lt|ədəd|eded|bağlama|baglama|package|pcs|bag|əd|ed|ad|l'
)
_NUM = r'\d+(?:[.,]\d+)?'

HELP_TEXT = (
    'Bu mətndən anbar sətri oxunmadı.\n'
    'Nümunə:\n'
    'Un 10 kq\n'
    'Süd 5 l 1.20\n'
    'Yumurta 30 eded\n'
    'Şəkil də göndərə bilərsiniz.'
)


def _is_num(token):
    return bool(re.fullmatch(_NUM, token or ''))


def _decimal(token):
    try:
        value = Decimal(str(token).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value


def _unit(token):
    if not token:
        return None
    return UNIT_MAP.get(token.casefold())


def parse_stock_line(line):
    raw = (line or '').strip().strip('-•*').strip()
    if not raw:
        return None
    normalized = re.sub(
        rf'({_NUM})({_UNIT_ALT})\b',
        r'\1 \2',
        raw,
        flags=re.IGNORECASE,
    )
    tokens = normalized.split()
    if len(tokens) < 2:
        return None

    price = None
    unit = None
    qty = None
    name_tokens = []

    if _is_num(tokens[-1]) and len(tokens) >= 4 and _unit(tokens[-2]) and _is_num(tokens[-3]):
        price = _decimal(tokens[-1])
        unit = _unit(tokens[-2])
        qty = _decimal(tokens[-3])
        name_tokens = tokens[:-3]
    elif _unit(tokens[-1]) and len(tokens) >= 3 and _is_num(tokens[-2]):
        unit = _unit(tokens[-1])
        qty = _decimal(tokens[-2])
        name_tokens = tokens[:-2]
    elif _is_num(tokens[-1]):
        qty = _decimal(tokens[-1])
        name_tokens = tokens[:-1]
    else:
        return None

    name = ' '.join(name_tokens).strip(' :,;-')
    if qty is None or len(name) < 2:
        return None
    return {
        'name': name,
        'quantity': qty,
        'unit': unit,
        'price': price,
    }


def parse_stock_text(text):
    items = []
    for line in (text or '').splitlines():
        parsed = parse_stock_line(line)
        if parsed:
            items.append(parsed)
    return items


def _find_item(name):
    exact = list(InventoryItem.objects.filter(name__iexact=name)[:2])
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return exact[0]
    return None


def _default_category():
    category = InventryCategory.objects.order_by('id').first()
    if category:
        return category
    return InventryCategory.objects.create(name='Ümumi')


def _format_qty(value):
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


@transaction.atomic
def apply_stock_lines(items, allow_create):
    added = []
    missing = []
    for item in items:
        product = _find_item(item['name'])
        created = False
        if product is None:
            if not allow_create or not item['unit']:
                missing.append(item['name'])
                continue
            product = InventoryItem.objects.create(
                name=item['name'],
                category=_default_category(),
                unit=item['unit'],
            )
            created = True
        InventoryRecord.objects.create(
            inventory_item=product,
            quantity=item['quantity'],
            record_type='add',
            reason='purchase',
            price=float(item['price'] or 0),
        )
        added.append({
            'name': product.name,
            'quantity': _format_qty(item['quantity']),
            'unit': product.unit,
            'created': created,
        })
    return added, missing


def build_reply(text, source):
    items = parse_stock_text(text)
    if not items:
        reply = HELP_TEXT
        if source == 'ocr' and (text or '').strip():
            preview = ' '.join((text or '').split())
            if len(preview) > 300:
                preview = preview[:300] + '…'
            reply = f'Şəkildən oxunan mətn:\n{preview}\n\n{HELP_TEXT}'
        return False, reply, []

    added, missing = apply_stock_lines(items, allow_create=True)
    lines = []
    if added:
        lines.append('Anbara əlavə olundu:')
        for row in added:
            suffix = ' (yeni məhsul)' if row['created'] else ''
            lines.append(f"• {row['name']} — {row['quantity']} {row['unit']}{suffix}")
    if missing:
        if lines:
            lines.append('')
        lines.append('Tapılmadı:')
        for name in missing:
            lines.append(f'• {name}')
        lines.append('Yeni məhsul üçün vahid yazın: kq, l, eded, baglama.')
    if not lines:
        lines.append(HELP_TEXT)
    return bool(added), '\n'.join(lines), added
