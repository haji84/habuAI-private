"""Bounded, offline normalization of two explicitly different tide sources.

JCG 4632 is a retrospectively retrieved astronomical prediction at Koniya.
JMA O9 is a provisional observation at Amami (Naze Kominato). Neither the
locations nor their vertical datums are interchangeable. No datum conversion,
training admission, historical publication proof, or local inference is made.
"""
from datetime import date, datetime, time, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
import re
from urllib.parse import parse_qs, urlsplit


_JST = timezone(timedelta(hours=9))
_MAX_BYTES = 2 * 1024 * 1024
_PREDICTION = 'ASTRONOMICAL_TIDE_PREDICTION_RETRIEVED_RETROSPECTIVELY'
_READY = ('source_received_at', 'derived_at', 'materialized_at', 'audited_at')


def _timestamp(value):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError('receipt timestamps must be aware ISO datetimes')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid receipt timestamp') from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('receipt timestamps must be timezone aware')
    return result.astimezone(timezone.utc)


def _source(raw, receipt, provider, period):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_BYTES:
        raise ValueError('source must be nonempty bytes of at most 2 MiB')
    if not isinstance(receipt, dict):
        raise ValueError('receipt must be a dictionary')
    try:
        encoded = json.dumps(receipt, allow_nan=False)
        if len(encoded) > 65536:
            raise ValueError('receipt is too large')
        source = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError('receipt must contain bounded JSON data') from exc
    station, kind = ('4632', _PREDICTION) if provider == 'JCG' else ('O9', 'OBSERVED_PROVISIONAL')
    if (source.get('provider'), source.get('station_id'), source.get('source_type')) != (provider, station, kind):
        raise ValueError('receipt provider, station, or source type mismatch')
    for name in ('station_name', 'licence_url', 'requested_url', 'resolved_url'):
        if not isinstance(source.get(name), str) or not source[name].strip():
            raise ValueError('receipt requires ' + name)
    if type(source.get('size_bytes')) is not int or source['size_bytes'] != len(raw):
        raise ValueError('receipt byte size mismatch')
    if source.get('sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('receipt SHA-256 mismatch')
    retrieved = _timestamp(source.get('retrieved_at'))
    ready = [_timestamp(source.get(key)) for key in _READY]
    if any(stamp < retrieved for stamp in ready):
        raise ValueError('readiness cannot precede this source retrieval')
    for key in ('requested_url', 'resolved_url'):
        url = urlsplit(source[key])
        if url.scheme != 'https' or url.username or url.password or url.port not in (None, 443) or url.fragment:
            raise ValueError('source URL must be an official HTTPS URL')
        if provider == 'JCG':
            if url.hostname != 'www1.kaiho.mlit.go.jp' or url.path != '/TIDE/pred2/cgi-bin/TidePredCgi.cgi':
                raise ValueError('unexpected JCG source endpoint')
            query = parse_qs(url.query, keep_blank_values=True)
            expected = dict(area='4632', year=str(period.year), month=str(period.month), day=str(period.day))
            if any(query.get(k) != [v] for k, v in expected.items()):
                raise ValueError('JCG URL station or date mismatch')
        else:
            stamp = period.strftime('%Y%m')
            path = f'/kaiyou/data/db/tide/sokuho/{stamp}/z_hry{stamp}O9.txt'
            if url.hostname not in ('www.data.jma.go.jp', 'ds.data.jma.go.jp') or url.path != path or url.query:
                raise ValueError('unexpected JMA station/month endpoint')
    return source, retrieved, max([retrieved] + ready).isoformat()


def _envelope(source, usable_at, observations, datum):
    return dict(schema_version='historical-environment-source-v1', source=source,
                observations=observations, usable_at=usable_at,
                geographic_support='REFERENCE_STATION_ONLY', vertical_datum=datum,
                datum_conversion='NOT_PERFORMED', historical_ex_ante_proven=False,
                training_eligibility='NOT_ASSESSED')


def _observation(day, hour, raw_value, kind, source_cell, *, missing=('',)):
    text = raw_value.strip()
    if text in missing:
        value, quality, kind = None, 'MISSING', 'UNKNOWN'
    elif re.fullmatch(r'-?\d{1,5}', text, flags=re.ASCII):
        value, quality = int(text), 'NUMERIC_AS_PUBLISHED'
    else:
        raise ValueError('unsupported tide value or quality symbol')
    at = datetime.combine(day, time(hour), _JST).isoformat()
    # Tide height is an hourly instant sample, not a one-hour accumulation.
    return dict(valid_start=at, valid_end=at, support_kind='HOURLY_REFERENCE_STATION',
                values={'tide_height_cm': dict(value=value, unit='cm', kind=kind,
                        quality=quality, raw_value=raw_value, source_cell=source_cell)})


def _unique_attributes(attrs):
    names = [name for name, _ in attrs]
    if len(names) != len(set(names)):
        raise ValueError('duplicate HTML attributes are ambiguous')
    return dict(attrs)


class _Tables(HTMLParser):
    """Read table cells without executing the provider's document.write code."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = self.row = self.cell = None
        self.cell_tag = None
        self.cell_attrs = None
        self.images = []
        self.visible_text = []
        self.hidden_tag = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden_tag = tag
        if tag == 'img':
            self.images.append(_unique_attributes(attrs).get('src', ''))
        if tag == 'table':
            _unique_attributes(attrs)
            if self.table is not None:
                raise ValueError('nested tide tables are unsupported')
            self.table = []
        elif tag == 'tr' and self.table is not None:
            _unique_attributes(attrs)
            if self.row is not None:
                raise ValueError('unclosed table row')
            self.row = []
        elif tag in ('td', 'th') and self.table is not None:
            if self.row is None or self.cell is not None:
                raise ValueError('malformed table cell')
            self.cell, self.cell_tag = [], tag
            # Keep the original list until candidate-table validation so that
            # duplicate attributes cannot be silently collapsed by dict().
            self.cell_attrs = list(attrs)

    def handle_data(self, text):
        if self.hidden_tag is None:
            self.visible_text.append(text)
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag == self.hidden_tag:
            self.hidden_tag = None
        if tag in ('td', 'th') and self.table is not None:
            if self.cell is None or self.cell_tag != tag:
                raise ValueError('unmatched table cell')
            self.row.append(dict(text=''.join(self.cell), tag=self.cell_tag,
                                 attrs=self.cell_attrs))
            self.cell = self.cell_tag = None
            self.cell_attrs = None
        elif tag == 'tr' and self.table is not None:
            if self.row is None or self.cell is not None:
                raise ValueError('malformed table row')
            self.table.append(self.row)
            self.row = None
        elif tag == 'table':
            if self.table is None or self.row is not None or self.cell is not None:
                raise ValueError('malformed table closure')
            self.tables.append(self.table)
            self.table = None


class _Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attrs = _unique_attributes(attrs)
            if attrs.get('name') in ('area', 'year', 'month', 'day'):
                self.fields.setdefault(attrs['name'], []).append(attrs.get('value'))


def normalize_jcg_predictions(raw_bytes, *, day: str, receipt: dict) -> dict:
    """Normalize Koniya 4632 predictions retrieved on or after the requested day."""
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day, re.ASCII):
        raise ValueError('day must be YYYY-MM-DD')
    requested = date.fromisoformat(day)
    # The historical training scope uses the Gregorian calendar only.
    if requested.year < 2000:
        raise ValueError('only modern Gregorian dates are supported')
    source, retrieved, usable = _source(raw_bytes, receipt, 'JCG', requested)
    if requested > retrieved.astimezone(_JST).date():
        raise ValueError('this source type requires retrospective retrieval')
    try:
        html = raw_bytes.decode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ValueError('JCG source must be UTF-8') from exc
    parser = _Tables()
    parser.feed(html)
    parser.close()
    if parser.table is not None:
        raise ValueError('unclosed table')
    image = f'../TidePred/tide_img/4632_{requested:%Y%m%d}.png'
    heading = ' '.join(parser.visible_text)
    if parser.images.count(image) != 1 or 'KONIYA' not in heading or '古仁屋' not in heading:
        raise ValueError('JCG station/date identity is absent or inconsistent')
    # The current provider embeds date controls inside JavaScript string literals.
    # Parse only literal input tags, never evaluate that JavaScript.
    inputs = _Inputs()
    for literal in re.findall(r'<input\b[^>]*>', html, flags=re.IGNORECASE):
        inputs.feed(literal.replace('\\"', '"'))
    expected = dict(area=['4632'], year=[str(requested.year)],
                    month=[str(requested.month)], day=[str(requested.day)])
    if inputs.fields != expected:
        raise ValueError('JCG form station/date mismatch')
    candidates = [(i, table) for i, table in enumerate(parser.tables, 1)
                  if any(row and row[0]['text'].strip() in ('時', '(cm)') for row in table)]
    if len(candidates) != 1:
        raise ValueError('expected exactly one hourly tide table')
    table_index, rows = candidates[0]
    if len(rows) != 4 or any(len(row) != 13 for row in rows):
        raise ValueError('expected two complete twelve-hour tide blocks')
    for row in rows:
        for cell in row:
            attrs = _unique_attributes(cell['attrs'])
            for name in ('colspan', 'rowspan'):
                if name in attrs and attrs[name] != '1':
                    raise ValueError('hourly tide cells require unit row and column spans')
    rows = [[cell['text'] for cell in row] for row in rows]
    observations = []
    for first, row_index in ((0, 0), (12, 2)):
        if [v.strip() for v in rows[row_index]] != ['時'] + [f'{hour:02d}' for hour in range(first, first + 12)]:
            raise ValueError('hour columns must be complete and ordered')
        if rows[row_index + 1][0].strip() != '(cm)':
            raise ValueError('tide height units must be cm')
        for offset, raw in enumerate(rows[row_index + 1][1:]):
            observations.append(_observation(requested, first + offset, raw, 'PREDICTED',
                                dict(table=table_index, row=row_index + 2, column=offset + 2),
                                missing=('', '--')))
    return _envelope(source, usable, observations, 'JCG_4632_LOCAL_PREDICTION_DATUM')


def normalize_jma_tide_observations(raw_bytes, *, month: str, receipt: dict) -> dict:
    """Normalize O9 provisional 80-column daily records (24 three-byte heights).

    Blank future slots present in monthly files remain UNKNOWN; future numeric
    observations are rejected. Two-digit years are supported only in 2000-2099.
    """
    if not isinstance(month, str) or not re.fullmatch(r'20\d{2}-\d{2}', month, re.ASCII):
        raise ValueError('month must be YYYY-MM in 2000-2099')
    requested = date.fromisoformat(month + '-01')
    source, retrieved, usable = _source(raw_bytes, receipt, 'JMA', requested)
    try:
        content = raw_bytes.decode('ascii', errors='strict')
    except UnicodeError as exc:
        raise ValueError('JMA hourly tide file must be ASCII') from exc
    content = content.replace('\r\n', '\n')
    if any(ord(char) < 32 and char != '\n' for char in content):
        raise ValueError('unexpected control character in fixed-width data')
    lines = content.removesuffix('\n').split('\n')
    if not 1 <= len(lines) <= 31:
        raise ValueError('expected one to thirty-one daily rows')
    observations, days = [], set()
    for number, line in enumerate(lines, 1):
        if len(line) != 80 or line[78:80] != 'O9':
            raise ValueError('invalid JMA row width or station code')
        if any(not re.fullmatch(r' ?\d{1,2}', line[start:start + 2], re.ASCII) for start in (72, 74, 76)):
            raise ValueError('invalid fixed-width date')
        year, mm, dd = (int(line[start:start + 2]) for start in (72, 74, 76))
        current = date(2000 + year, mm, dd)
        if (current.year, current.month) != (requested.year, requested.month) or current in days:
            raise ValueError('JMA row month mismatch or duplicate day')
        days.add(current)
        for hour in range(24):
            raw = line[hour * 3:hour * 3 + 3]
            item = _observation(current, hour, raw, 'OBSERVED_PROVISIONAL',
                                dict(line=number, column_start=hour * 3 + 1, column_end=hour * 3 + 3))
            if item['values']['tide_height_cm']['value'] is not None and _timestamp(item['valid_start']) > retrieved:
                raise ValueError('numeric observation occurs after source retrieval')
            observations.append(item)
    observations.sort(key=lambda item: item['valid_start'])
    return _envelope(source, usable, observations, 'JMA_O9_LOCAL_OBSERVATION_DATUM')
