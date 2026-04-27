"""
Panjiva spreadsheet parser.

Auto-detects format from column headers:
  Format 1 (shipment): has "BUYER" column  → groups rows by buyer → Lead + purchase_history
  Format 2 (consignee): has "CONSIGNEE" column → one row per company → Lead + Contacts
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime


def _norm(h: str) -> str:
    return ' '.join(h.strip().lower().split())


def _decimal(val) -> Decimal | None:
    if val is None or str(val).strip() in ('', '-', 'N/A', 'NA', 'nan', 'None'):
        return None
    s = str(val).replace(',', '').strip()
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _date_str(val) -> str:
    if not val or str(val).strip() in ('', '-', 'nan', 'None'):
        return ''
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%d-%b-%Y', '%d %b %Y', '%Y%m%d'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


def _read_file(file) -> tuple[list[str], list[list]]:
    name = file.name.lower()
    if name.endswith('.csv'):
        content = file.read().decode('utf-8-sig', errors='replace')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return [], []
        return rows[0], rows[1:]
    else:
        import openpyxl
        wb = openpyxl.load_workbook(filename=io.BytesIO(file.read()), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            wb.close()
            return [], []
        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not all_rows:
            return [], []
        headers = [str(c) if c is not None else '' for c in all_rows[0]]
        data = [[str(c) if c is not None else '' for c in row] for row in all_rows[1:]]
        return headers, data


def _getter(norm_idx: dict, row: list):
    def get(key: str) -> str:
        idx = norm_idx.get(key)
        if idx is None or idx >= len(row):
            return ''
        return str(row[idx]).strip()
    return get


def _parse_format1(headers: list[str], rows: list[list]) -> list[dict]:
    """Shipment format: group by BUYER."""
    norm_idx = {_norm(h): i for i, h in enumerate(headers)}
    buyers: dict[str, dict] = {}

    for row in rows:
        get = _getter(norm_idx, row)
        buyer = get('buyer')
        if not buyer or buyer.lower() in ('nan', 'none', ''):
            continue

        if buyer not in buyers:
            buyers[buyer] = {
                'company_name': buyer,
                'company_country': get('destination'),
                'company_website': '',
                'contacts': [],
                'purchase_history': [],
            }

        quantity = _decimal(get('quantity'))
        value_usd = _decimal(get('value(usd)')) or _decimal(get('value (usd)'))
        unit_price = _decimal(get('unit price'))

        record: dict = {
            'date': _date_str(get('date')),
            'product_desc': get('product desc'),
            'hs_code': get('hs code'),
            'unit': get('unit'),
        }
        if quantity is not None:
            record['quantity'] = float(quantity)
        if value_usd is not None:
            record['value_usd'] = float(value_usd)
        if unit_price is not None:
            record['unit_price'] = float(unit_price)

        buyers[buyer]['purchase_history'].append(record)

    return list(buyers.values())


def _parse_format2(headers: list[str], rows: list[list]) -> list[dict]:
    """Consignee format: one lead per row."""
    norm_idx = {_norm(h): i for i, h in enumerate(headers)}
    result = []

    for row in rows:
        get = _getter(norm_idx, row)
        company = get('consignee')
        if not company or company.lower() in ('nan', 'none', ''):
            continue

        address = get('consignee full address')
        country = ''
        if address:
            parts = [p.strip() for p in address.split(',') if p.strip()]
            country = parts[-1] if parts else ''

        website = get('consignee website 1') or get('consignee website 2')
        designation = get('consignee trade roles')

        contacts = []
        for i in range(1, 4):
            email = get(f'consignee email {i}') or None
            phone = get(f'consignee phone {i}') or None
            if not email and not phone:
                continue
            if email and email.lower() in ('nan', 'none'):
                email = None
            if phone and phone.lower() in ('nan', 'none'):
                phone = None
            if email or phone:
                contacts.append({
                    'email': email,
                    'phone': phone,
                    'designation': designation,
                    'first_name': '',
                    'last_name': '',
                })

        result.append({
            'company_name': company,
            'company_country': country,
            'company_website': website,
            'contacts': contacts,
            'purchase_history': [],
        })

    return result


def parse_panjiva(file) -> list[dict]:
    """
    Parse a Panjiva CSV/Excel file.

    Returns a list of dicts, each representing one lead:
      {
        'company_name': str,
        'company_country': str,
        'company_website': str,
        'contacts': [{'email', 'phone', 'designation', 'first_name', 'last_name'}],
        'purchase_history': [{'date', 'product_desc', 'hs_code', 'quantity', 'value_usd', 'unit_price', 'unit'}],
      }
    """
    headers, rows = _read_file(file)
    if not headers:
        return []

    norm_set = {_norm(h) for h in headers}

    if 'consignee' in norm_set:
        return _parse_format2(headers, rows)
    if 'buyer' in norm_set:
        return _parse_format1(headers, rows)

    return []
