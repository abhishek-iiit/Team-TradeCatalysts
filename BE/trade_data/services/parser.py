"""
Panjiva / Exim spreadsheet parser.

Supported formats:
  Exim    (has "BUYER" column)      → groups rows by BUYER
  Panjiva (has "Consignee" column)  → groups rows by Consignee

Reads xlsx by directly parsing the ZIP/XML contents — completely bypasses
openpyxl's stylesheet loading, which crashes on files produced by export tools.
Reads CSV/TSV with automatic delimiter detection.
"""

import csv
import io
import zipfile
from decimal import Decimal, InvalidOperation
from datetime import datetime
from xml.etree import ElementTree as ET


# ─── Low-level helpers ─────────────────────────────────────────────────────────

def _norm(h: str) -> str:
    return ' '.join(h.strip().lower().split())


def _clean(val) -> str:
    s = str(val).strip() if val is not None else ''
    return '' if s.lower() in ('nan', 'none') else s


def _decimal(val) -> Decimal | None:
    if val is None:
        return None
    s = str(val).replace(',', '').strip()
    if s in ('', '-', 'n/a', 'na', 'nan', 'none'):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _date_str(val) -> str:
    if not val:
        return ''
    s = str(val).strip()
    if s.lower() in ('', '-', 'nan', 'none'):
        return ''
    for fmt in (
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y',
        '%d-%b-%Y', '%d %b %Y', '%Y%m%d', '%d-%b-%y',
    ):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


def _col_to_idx(col_str: str) -> int:
    """'A' → 0, 'B' → 1, 'AA' → 26, etc."""
    idx = 0
    for ch in col_str.upper():
        idx = idx * 26 + (ord(ch) - ord('A') + 1)
    return idx - 1


# ─── Header-row finder ────────────────────────────────────────────────────────

# Keywords that must appear as a cell value in the actual header row.
# Checked with exact normalised match so metadata sentences don't trigger.
_HEADER_KEYWORDS = {'buyer', 'consignee', 'arrival date', 'shipment id'}


def _find_header_row(all_rows: list[list]) -> tuple[list[str], list[list]]:
    """
    Scan rows (skipping metadata/title lines) and return (header_row, data_rows).

    Strategy:
      1. Find the first row where ANY cell's normalised value matches a known
         header keyword ('buyer', 'consignee', 'arrival date', 'shipment id').
         This reliably skips "EX-IM Trade analysis report" / timestamp lines.
      2. Fall back to the first non-empty row if no keyword match is found.
    """
    # Pass 1 – keyword match
    for i, row in enumerate(all_rows):
        cells = {_norm(v) for v in row if str(v).strip()}
        if cells & _HEADER_KEYWORDS:
            return row, all_rows[i + 1:]

    # Pass 2 – first non-empty row
    for i, row in enumerate(all_rows):
        if any(str(v).strip() for v in row):
            return row, all_rows[i + 1:]

    return [], []


# ─── xlsx reader (no openpyxl — direct ZIP/XML) ────────────────────────────────

_MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def _parse_sheet(zf: zipfile.ZipFile, sheet_path: str, shared: list[str]) -> list[list]:
    """Parse one worksheet XML into a list of rows."""
    root = ET.fromstring(zf.read(sheet_path))

    max_col = 0
    sparse: dict[int, dict[int, str]] = {}

    for row_el in root.iter(f'{{{_MAIN_NS}}}row'):
        row_idx = int(row_el.get('r', '0')) - 1
        row_data: dict[int, str] = {}

        for cell in row_el:
            ref = cell.get('r', '')
            col_letters = ''.join(c for c in ref if c.isalpha())
            if not col_letters:
                continue
            col_idx = _col_to_idx(col_letters)
            max_col = max(max_col, col_idx + 1)

            ctype = cell.get('t', '')
            v_el = cell.find(f'{{{_MAIN_NS}}}v')

            if ctype == 's':
                i = int(v_el.text) if v_el is not None and v_el.text else 0
                value = shared[i] if i < len(shared) else ''
            elif ctype == 'inlineStr':
                t_el = cell.find(f'.//{{{_MAIN_NS}}}t')
                value = (t_el.text or '') if t_el is not None else ''
            elif ctype == 'b':
                value = 'TRUE' if (v_el.text if v_el is not None else '') == '1' else 'FALSE'
            else:
                value = (v_el.text or '') if v_el is not None else ''

            row_data[col_idx] = str(value).strip()

        if row_data:
            sparse[row_idx] = row_data

    if not sparse:
        return []

    max_row = max(sparse) + 1
    return [
        [sparse.get(r, {}).get(c, '') for c in range(max_col)]
        for r in range(max_row)
    ]


def _sheet_paths_in_order(zf: zipfile.ZipFile) -> list[str]:
    """
    Return worksheet file paths in workbook order (sheet1 first, etc.).
    Falls back to sorted alphabetical if workbook.xml is unreadable.
    """
    names = set(zf.namelist())

    # Parse xl/workbook.xml to get the declared sheet order + rId mapping
    try:
        wb_root = ET.fromstring(zf.read('xl/workbook.xml'))
        # Relationship file maps rId → file path
        rels_path = 'xl/_rels/workbook.xml.rels'
        rels: dict[str, str] = {}
        if rels_path in names:
            rels_root = ET.fromstring(zf.read(rels_path))
            REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
            for rel in rels_root.iter(f'{{{REL_NS}}}Relationship'):
                rid = rel.get('Id', '')
                target = rel.get('Target', '')
                # Target may be relative like "worksheets/sheet1.xml"
                full = f'xl/{target}' if not target.startswith('xl/') else target
                rels[rid] = full

        ordered: list[str] = []
        WB_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        for sheet_el in wb_root.iter(f'{{{WB_NS}}}sheet'):
            rid = sheet_el.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', '')
            path = rels.get(rid, '')
            if path and path in names:
                ordered.append(path)
        if ordered:
            return ordered
    except Exception:
        pass

    # Fallback: sorted alphabetical
    return sorted(
        p for p in names
        if p.startswith('xl/worksheets/sheet') and p.endswith('.xml')
    )


def _read_xlsx(raw: bytes) -> tuple[list[str], list[list]]:
    """
    Parse an xlsx file by reading its ZIP/XML internals directly.
    Immune to openpyxl stylesheet errors.
    Scans ALL sheets and returns the first one whose headers match known keywords.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())

        # ── Shared strings ──────────────────────────────────────────────────
        shared: list[str] = []
        for sst_path in ('xl/sharedStrings.xml', 'xl/SharedStrings.xml'):
            if sst_path in names:
                root = ET.fromstring(zf.read(sst_path))
                for si in root:
                    text = ''.join(
                        (t.text or '')
                        for t in si.iter(f'{{{_MAIN_NS}}}t')
                    )
                    shared.append(text)
                break

        sheet_paths = _sheet_paths_in_order(zf)
        if not sheet_paths:
            return [], []

        # ── Try each sheet; return the first with recognisable headers ──────
        fallback: tuple[list[str], list[list]] | None = None

        for path in sheet_paths:
            all_rows = _parse_sheet(zf, path, shared)
            if not all_rows:
                continue
            headers, data = _find_header_row(all_rows)
            if not headers:
                continue
            norm_cells = {_norm(h) for h in headers if h.strip()}
            if norm_cells & _HEADER_KEYWORDS:
                return headers, data          # found the right sheet
            if fallback is None:
                fallback = (headers, data)    # remember first non-empty as fallback

        return fallback if fallback else ([], [])


# ─── CSV / TSV reader ─────────────────────────────────────────────────────────

def _read_csv(raw: bytes) -> tuple[list[str], list[list]]:
    # Try UTF-8 with BOM first, then latin-1 as fallback
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        content = raw.decode('latin-1', errors='replace')

    # Detect delimiter by sampling *all* non-empty lines (not just the first,
    # which may be a metadata title with no delimiters at all).
    non_empty_lines = [l for l in content.split('\n') if l.strip()]
    sample = '\n'.join(non_empty_lines[:30])  # up to 30 lines for sniffer

    delimiter = ','
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters='\t,|;')
        delimiter = dialect.delimiter
    except csv.Error:
        # Fallback: pick delimiter with most columns across non-empty lines
        best, best_score = ',', 0
        for d in ('\t', ',', '|', ';'):
            col_counts = [len(l.split(d)) for l in non_empty_lines[:10]]
            score = max(col_counts, default=0)
            if score > best_score:
                best_score, best = score, d
        delimiter = best

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return [], []

    return _find_header_row(rows)


# ─── Main file reader ─────────────────────────────────────────────────────────

def _read_file(file) -> tuple[list[str], list[list]]:
    raw = file.read()
    name = file.name.lower()

    if any(name.endswith(ext) for ext in ('.xlsx', '.xlsm', '.xlsb')):
        return _read_xlsx(raw)

    if name.endswith('.xls'):
        # Try as xlsx first (some tools save xlsx with .xls extension)
        try:
            return _read_xlsx(raw)
        except Exception:
            raise ValueError(
                'Old .xls format is not supported. Please re-save the file as .xlsx or export as CSV.'
            )

    # CSV / TSV / txt
    return _read_csv(raw)


# ─── Column getter ────────────────────────────────────────────────────────────

def _make_getter(norm_idx: dict, row: list):
    def get(*keys: str) -> str:
        for key in keys:
            idx = norm_idx.get(key)
            if idx is not None and idx < len(row):
                v = _clean(row[idx])
                if v:
                    return v
        return ''
    return get


# ─── Format 1: Exim ──────────────────────────────────────────────────────────

def _parse_exim(headers: list[str], rows: list[list]) -> list[dict]:
    norm_idx = {_norm(h): i for i, h in enumerate(headers)}
    buyers: dict[str, dict] = {}

    for row in rows:
        get = _make_getter(norm_idx, row)
        buyer = get('buyer')
        if not buyer:
            continue

        if buyer not in buyers:
            buyers[buyer] = {
                'company_name': buyer,
                'company_country': get('buyer country'),
                'company_website': '',
                'contacts': [],
                'purchase_history': [],
            }

        quantity   = _decimal(get('quantity'))
        value_usd  = _decimal(get('value(usd)', 'value (usd)'))
        unit_price = _decimal(get('unit price'))

        record: dict = {
            'date':             _date_str(get('date')),
            'product_desc':     get('product description', 'product desc'),
            'hs_code':          get('hs code'),
            'unit':             get('unit'),
            'destination_port': get('destination port'),
        }
        if quantity is not None:
            record['quantity'] = float(quantity)
        if value_usd is not None:
            record['value_usd'] = float(value_usd)
        if unit_price is not None:
            record['unit_price'] = float(unit_price)

        buyers[buyer]['purchase_history'].append(record)

    return list(buyers.values())


# ─── Format 2: Panjiva ───────────────────────────────────────────────────────

def _parse_panjiva(headers: list[str], rows: list[list]) -> list[dict]:
    norm_idx = {_norm(h): i for i, h in enumerate(headers)}
    consignees: dict[str, dict] = {}

    for row in rows:
        get = _make_getter(norm_idx, row)
        company = get('consignee')
        if not company:
            continue

        if company not in consignees:
            address = get('consignee full address')
            country = ''
            if address:
                parts = [p.strip() for p in address.split(',') if p.strip()]
                country = parts[-1] if parts else ''

            website     = get('consignee website 1', 'consignee website 2')
            designation = get('consignee trade roles')

            contacts: list[dict] = []
            seen_emails: set[str] = set()
            for i in range(1, 4):
                email = get(f'consignee email {i}') or None
                phone = get(f'consignee phone {i}') or None
                if email and email in seen_emails:
                    email = None
                if email or phone:
                    contacts.append({
                        'email': email,
                        'phone': phone,
                        'designation': designation,
                        'first_name': '',
                        'last_name': '',
                    })
                    if email:
                        seen_emails.add(email)

            consignees[company] = {
                'company_name': company,
                'company_country': country,
                'company_website': website,
                'contacts': contacts,
                'purchase_history': [],
            }

        quantity  = _decimal(get('quantity'))
        value_usd = _decimal(get('value of goods (usd)', 'value(usd)', 'value (usd)'))

        record: dict = {
            'date':         _date_str(get('arrival date', 'date')),
            'product_desc': get('goods shipped', 'product description', 'product desc'),
            'hs_code':      get('hs code'),
            'destination':  get('shipment destination'),
        }
        if quantity is not None:
            record['quantity'] = float(quantity)
        if value_usd is not None:
            record['value_usd'] = float(value_usd)

        consignees[company]['purchase_history'].append(record)

    return list(consignees.values())


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_panjiva(file) -> tuple[list[dict], list[str]]:
    """
    Parse a Panjiva or Exim CSV/Excel file.

    Returns (leads, detected_headers).
    leads is empty when no recognised format was detected.
    detected_headers is included so callers can surface diagnostic info.
    """
    headers, rows = _read_file(file)
    if not headers:
        return [], []

    norm_set = {_norm(h) for h in headers}

    if 'consignee' in norm_set:
        return _parse_panjiva(headers, rows), list(headers)
    if 'buyer' in norm_set:
        return _parse_exim(headers, rows), list(headers)

    return [], list(headers)
