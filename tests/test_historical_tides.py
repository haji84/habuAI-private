"""Synthetic provider-shaped tide data; no field evidence or network calls."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
if importlib.util.find_spec('historical_tides'):
    import historical_tides as tides
else:
    tides = None

DAY = '2026-11-01'
STAMP = '2026-11-03T08:00:00+00:00'
PREDICTED = 'ASTRONOMICAL_TIDE_PREDICTION_RETRIEVED_RETROSPECTIVELY'


def jcg(values=None, *, day=DAY, station='4632'):
    values = list(range(-7, 17)) if values is None else values
    year, month, date = map(int, day.split('-'))
    form = ''.join(f'<input name={k} value="{v}">' for k, v in
                   [('area', station), ('year', year), ('month', month), ('day', date)])
    rows = []
    for first in (0, 12):
        hours = ['時'] + [f'{i:02d}' for i in range(first, first + 12)]
        height = ['(cm)'] + [str(v) for v in values[first:first + 12]]
        rows.extend('<TR>' + ''.join(f'<TD><B>{v}</B></TD>' for v in row) + '</TR>'
                    for row in (hours, height))
    return (f'<HTML><BODY>潮汐推算, Tidal prediction 古仁屋, KONIYA'
            f'<FORM>{form}</FORM><IMG SRC="../TidePred/tide_img/{station}_{day.replace("-", "")}.png">'
            '<TABLE>' + ''.join(rows) + '</TABLE></BODY></HTML>').encode()


def jma(values=None, *, day=DAY, station='O9'):
    values = list(range(-7, 17)) if values is None else values
    year, month, date = map(int, day.split('-'))
    return (''.join('   ' if v is None else f'{v:3d}' for v in values)
            + f'{year % 100:2d}{month:2d}{date:2d}{station}\n').encode('ascii')


def receipt(raw, provider):
    url = ('https://www1.kaiho.mlit.go.jp/TIDE/pred2/cgi-bin/TidePredCgi.cgi'
           '?area=4632&back=6&year=2026&month=11&day=1' if provider == 'JCG' else
           'https://www.data.jma.go.jp/kaiyou/data/db/tide/sokuho/202611/z_hry202611O9.txt')
    return dict(provider=provider, station_id='4632' if provider == 'JCG' else 'O9',
                station_name='古仁屋' if provider == 'JCG' else '奄美（名瀬小湊）',
                source_type=PREDICTED if provider == 'JCG' else 'OBSERVED_PROVISIONAL',
                requested_url=url, resolved_url=url, retrieved_at=STAMP,
                size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                licence_url='https://www.jma.go.jp/jma/kishou/info/coment.html',
                source_received_at=STAMP, derived_at=STAMP, materialized_at=STAMP, audited_at=STAMP)


def finalized(values=None, *, day=DAY, station='O9', tail=None):
    tail = (' 1 2-12' + '9999999' * 3 + '       ' * 4) if tail is None else tail
    return jma(values, day=day, station=station).rstrip(b'\n') + tail.encode('ascii') + b'\n'


def finalized_receipt(raw, month='2026-11'):
    rec = receipt(raw, 'JMA')
    stamp = month.replace('-', '')
    rec['source_type'] = 'OBSERVED_FINALIZED'
    rec['requested_url'] = rec['resolved_url'] = (
        f'https://www.data.jma.go.jp/kaiyou/data/db/tide/genbo/{stamp[:4]}/{stamp}/hry{stamp}O9.txt')
    return rec


class TideNormalizerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(tides, 'historical tide normalizer is not implemented')

    def parse(self, raw, provider='JCG', rec=None, **kwargs):
        rec = receipt(raw, provider) if rec is None else rec
        if provider == 'JCG':
            return tides.normalize_jcg_predictions(raw, day=kwargs.get('day', DAY), receipt=rec)
        return tides.normalize_jma_tide_observations(raw, month=kwargs.get('month', '2026-11'), receipt=rec)

    def test_predictions_are_not_observations_or_historical_issuance(self):
        value = self.parse(jcg())
        self.assertEqual(len(value['observations']), 24)
        item = value['observations'][0]
        self.assertEqual(item['values']['tide_height_cm']['value'], -7)
        self.assertEqual(item['values']['tide_height_cm']['kind'], 'PREDICTED')
        self.assertEqual(item['valid_start'], '2026-11-01T00:00:00+09:00')
        self.assertEqual(item['valid_start'], item['valid_end'])
        self.assertEqual(value['source']['source_type'], PREDICTED)
        self.assertFalse(value['historical_ex_ante_proven'])
        self.assertEqual(value['training_eligibility'], 'NOT_ASSESSED')
        self.assertEqual(value['geographic_support'], 'REFERENCE_STATION_ONLY')

    def test_observations_keep_negative_zero_and_partial_missing_distinct(self):
        result = self.parse(jma([-7, 0] + [12] * 9 + [None] * 13), 'JMA')
        cells = [o['values']['tide_height_cm'] for o in result['observations']]
        self.assertEqual([c['value'] for c in cells[:2]], [-7, 0])
        self.assertEqual(sum(c['value'] is not None for c in cells), 11)
        self.assertEqual(cells[-1]['raw_value'], '   ')
        self.assertEqual(cells[-1]['kind'], 'UNKNOWN')
        self.assertEqual(cells[-1]['quality'], 'MISSING')
        self.assertEqual(cells[0]['kind'], 'OBSERVED_PROVISIONAL')
        self.assertIn('line', cells[0]['source_cell'])

    def test_prediction_missing_is_not_imputed_zero(self):
        vals = list(range(24)); vals[0] = '--'; vals[1] = ''
        result = self.parse(jcg(vals))
        self.assertEqual([r['values']['tide_height_cm']['value'] for r in result['observations'][:2]], [None, None])

    def test_datums_and_station_locations_remain_separate(self):
        pred = self.parse(jcg()); obs = self.parse(jma(), 'JMA')
        self.assertNotEqual(pred['vertical_datum'], obs['vertical_datum'])
        self.assertEqual(pred['source']['station_id'], '4632')
        self.assertEqual(obs['source']['station_id'], 'O9')

    def test_receipt_snapshot_and_latest_readiness_are_preserved(self):
        raw = jcg(); rec = receipt(raw, 'JCG')
        rec['audited_at'] = '2026-11-03T18:00:00+09:00'
        result = self.parse(raw, rec=rec)
        self.assertEqual(result['usable_at'], '2026-11-03T09:00:00+00:00')
        rec['station_name'] = 'changed'
        self.assertEqual(result['source']['station_name'], '古仁屋')

    def test_bad_hash_size_and_missing_readiness_reject(self):
        raw = jcg()
        for key, bad in [('sha256', '0' * 64), ('size_bytes', len(raw) + 1), ('size_bytes', True),
                         ('audited_at', None), ('station_id', '4628'), ('source_type', 'OBSERVED')]:
            with self.subTest(key=key, bad=bad):
                rec = receipt(raw, 'JCG'); rec[key] = bad
                with self.assertRaises(ValueError): self.parse(raw, rec=rec)

    def test_naive_and_backdated_readiness_reject(self):
        raw = jcg()
        for key in ('retrieved_at', 'source_received_at', 'derived_at', 'materialized_at', 'audited_at'):
            with self.subTest(key=key):
                rec = receipt(raw, 'JCG'); rec[key] = '2026-11-03T08:00:00'
                with self.assertRaises(ValueError): self.parse(raw, rec=rec)
        rec = receipt(raw, 'JCG'); rec['derived_at'] = '2026-11-01T00:00:00+09:00'
        with self.assertRaises(ValueError): self.parse(raw, rec=rec)

    def test_source_urls_cannot_claim_another_provider_or_day(self):
        raw = jcg()
        for url in ('https://example.com/tides', receipt(raw, 'JCG')['requested_url'].replace('day=1', 'day=2'),
                    receipt(raw, 'JCG')['requested_url'] + '&area=4628'):
            rec = receipt(raw, 'JCG'); rec['resolved_url'] = url
            with self.assertRaises(ValueError): self.parse(raw, rec=rec)

    def test_wrong_day_station_and_missing_hour_html_reject(self):
        for raw in (jcg(day='2026-11-02'), jcg(station='4628'),
                    jcg().replace(b'<B>23</B>', b'<B>22</B>'),
                    jcg().replace(b'<TD><B>16</B></TD>', b''),
                    jcg().replace(b'(cm)', b'(m)')):
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(ValueError): self.parse(raw)

    def test_duplicated_or_malformed_html_tables_reject(self):
        raw = jcg(); table = raw[raw.index(b'<TABLE>'):raw.index(b'</TABLE>') + 8]
        for malformed in (raw + table, raw.replace(b'</TR>', b'', 1), raw.replace(b'<B>-7</B>', b'<B>NaN</B>')):
            with self.assertRaises(ValueError): self.parse(malformed)

    def test_fixed_width_wrong_station_month_and_dates_reject(self):
        for raw in (jma(station='NH'), jma(day='2026-10-31'), jma()[:-9] + b'261132O9\n',
                    jma()[:-9] + b'2511 1O9\n', jma() + jma(), jma()[:-2] + b' O9\n'):
            with self.subTest(raw=raw[-20:]):
                with self.assertRaises(ValueError): self.parse(raw, 'JMA')

    def test_fixed_width_symbols_and_invalid_encoding_reject(self):
        for raw in (b' --' + jma()[3:], b'NaN' + jma()[3:], b'\xff' + jma()[1:], jma() + b'\n'):
            with self.assertRaises(ValueError): self.parse(raw, 'JMA')

    def test_complete_blank_future_day_remains_unknown_but_future_observation_rejects(self):
        raw = jma([None] * 24, day='2026-11-30')
        self.assertTrue(all(o['values']['tide_height_cm']['value'] is None for o in self.parse(raw, 'JMA')['observations']))
        with self.assertRaises(ValueError): self.parse(jma(day='2026-11-30'), 'JMA')

    def test_monthly_rows_sorted_without_fabricating_absent_days(self):
        raw = jma(day='2026-11-02') + jma()
        result = self.parse(raw, 'JMA')
        self.assertEqual(len(result['observations']), 48)
        self.assertEqual(result['observations'][0]['valid_start'], '2026-11-01T00:00:00+09:00')

    def test_oversized_and_empty_payloads_reject(self):
        for raw in (b'', b' ' * (2 * 1024 * 1024 + 1)):
            with self.assertRaises(ValueError): self.parse(raw)

    def test_literal_script_controls_parse_without_execution(self):
        raw = jcg()
        start, end = raw.index(b'<FORM>'), raw.index(b'</FORM>') + 7
        script = b'<FORM><TABLE><TR><TH><SCRIPT><!--\n'
        for name, val in [('area', '4632'), ('year', '2026'), ('month', '11'), ('day', '1')]:
            script += ('document.write("<input name=' + name + ' value=\\"' + val + '\\">");\n').encode()
        script += b'// --></SCRIPT></TH></TR></TABLE></FORM>'
        self.assertEqual(len(self.parse(raw[:start] + script + raw[end:])['observations']), 24)

    def test_fixed_width_line_endings_are_only_lf_or_crlf(self):
        self.assertEqual(len(self.parse(jma().replace(b'\n', b'\r\n'), 'JMA')['observations']), 24)
        for separator in (b'\v', b'\f', b'\r'):
            with self.subTest(separator=separator):
                raw = jma().replace(b'\n', separator)
                with self.assertRaises(ValueError): self.parse(raw, 'JMA')

    def test_provisional_urls_and_same_day_future_numbers_reject(self):
        raw = jma()
        rec = receipt(raw, 'JMA')
        rec['requested_url'] = rec['requested_url'].replace('O9', 'NH')
        with self.assertRaises(ValueError): self.parse(raw, 'JMA', rec=rec)
        rec = receipt(raw, 'JMA')
        for key in ('retrieved_at', 'source_received_at', 'derived_at', 'materialized_at', 'audited_at'):
            rec[key] = '2026-11-01T10:00:00+09:00'
        with self.assertRaises(ValueError): self.parse(raw, 'JMA', rec=rec)

    def test_future_prediction_and_nonbytes_reject(self):
        raw = jcg()
        rec = receipt(raw, 'JCG')
        for key in ('retrieved_at', 'source_received_at', 'derived_at', 'materialized_at', 'audited_at'):
            rec[key] = '2026-10-31T10:00:00+09:00'
        with self.assertRaises(ValueError): self.parse(raw, rec=rec)
        for bad in (raw.decode(), bytearray(raw), None):
            with self.assertRaises(ValueError): self.parse(bad, rec=receipt(raw, 'JCG'))

    def test_nonunit_or_duplicate_cell_attributes_reject(self):
        for tag in (b'TD', b'TH'):
            original = jcg().replace(b'TD>', tag + b'>')
            for text in (b'00', b'-7', b'(cm)'):
                cell = b'<' + tag + b'><B>' + text + b'</B>'
                for attrs in (b'colspan=2', b'rowspan=2', b'rowspan=0', b'colspan',
                              b'colspan=1 COLSPAN=2', b'align=left ALIGN=right'):
                    with self.subTest(tag=tag, text=text, attrs=attrs):
                        raw = original.replace(cell, cell.replace(b'>', b' ' + attrs + b'>', 1), 1)
                        with self.assertRaises(ValueError): self.parse(raw)

    def test_unit_spans_and_header_cells_preserve_hour_mapping(self):
        raw = jcg().replace(b'<TD>', b'<TH colspan="1" rowspan="1">').replace(b'</TD>', b'</TH>')
        result = self.parse(raw)
        self.assertEqual([o['values']['tide_height_cm']['value'] for o in result['observations']], list(range(-7, 17)))

    def test_ambiguous_identity_attributes_and_hidden_heading_reject(self):
        raw = jcg()
        for bad in (raw.replace(b'name=area', b'name=day name=area'),
                    raw.replace(b'value="4632"', b'value="4628" value="4632"'),
                    raw.replace(b'SRC="', b'src="wrong.png" SRC="'),
                    raw.replace(b'<TABLE>', b'<TABLE width=600 WIDTH=800>'),
                    raw.replace('古仁屋, KONIYA'.encode(), b'OTHER <!--' + '古仁屋, KONIYA'.encode() + b'-->')):
            with self.subTest(raw=bad[:80]):
                with self.assertRaises(ValueError): self.parse(bad)

    def test_station_names_must_match_canonical_source_location(self):
        for provider, raw, wrong_name in [('JMA', jma(), '古仁屋'),
                                          ('JCG', jcg(), '奄美（名瀬小湊）')]:
            rec = receipt(raw, provider)
            rec['station_name'] = wrong_name
            with self.subTest(provider=provider):
                with self.assertRaises(ValueError): self.parse(raw, provider, rec=rec)

    def test_readiness_respects_source_and_derivation_causality(self):
        raw = jcg()
        for later_key in ('source_received_at', 'derived_at'):
            rec = receipt(raw, 'JCG')
            rec[later_key] = '2026-11-03T09:00:00+00:00'
            with self.subTest(later_key=later_key):
                with self.assertRaises(ValueError): self.parse(raw, rec=rec)
        for earlier_key in ('materialized_at', 'audited_at'):
            rec = receipt(raw, 'JCG')
            rec.update(derived_at='2026-11-03T09:00:00+00:00',
                       materialized_at='2026-11-03T10:00:00+00:00',
                       audited_at='2026-11-03T10:00:00+00:00')
            rec[earlier_key] = STAMP
            with self.subTest(earlier_key=earlier_key):
                with self.assertRaises(ValueError): self.parse(raw, rec=rec)

    def final_parse(self, raw, *, month='2026-11', rec=None):
        self.assertTrue(hasattr(tides, 'normalize_jma_finalized_tide_observations'))
        return tides.normalize_jma_finalized_tide_observations(
            raw, month=month, receipt=rec or finalized_receipt(raw, month))

    def test_finalized_preserves_missing_heights_and_unassessed_extrema(self):
        raw = finalized([-7, 0] + [12] * 9 + [None] * 13)
        result = self.final_parse(raw)
        cells = [o['values']['tide_height_cm'] for o in result['observations']]
        self.assertEqual(len(cells), 24)
        self.assertEqual([c['value'] for c in cells[:2]], [-7, 0])
        self.assertEqual(sum(c['value'] is not None for c in cells), 11)
        self.assertEqual(cells[0]['kind'], 'OBSERVED_FINALIZED')
        self.assertEqual(cells[-1]['kind'], 'UNKNOWN')
        self.assertEqual(result['extrema']['status'], 'PRESERVED_NOT_EVALUATED')
        self.assertEqual(result['extrema']['records'][0]['raw_value'], raw.decode('ascii')[80:136])
        self.assertFalse(result['historical_ex_ante_proven'])

    def test_finalized_and_provisional_bodies_and_source_types_cannot_mix(self):
        with self.assertRaises(ValueError): self.final_parse(jma())
        with self.assertRaises(ValueError): self.parse(finalized(), 'JMA')
        raw = finalized()
        with self.assertRaises(ValueError): self.final_parse(raw, rec=receipt(raw, 'JMA'))
        with self.assertRaises(ValueError): self.parse(raw, 'JMA', rec=finalized_receipt(raw))

    def test_finalized_extrema_invalid_tail_rejects(self):
        for token in ('24 0123', ' 060123', '12  NaN', '9999998', '   1123', '1234 --'):
            with self.subTest(token=token):
                with self.assertRaises(ValueError): self.final_parse(finalized(tail=token + '9999999' * 7))
        for raw in (finalized()[:-2] + b'\n', finalized()[:-1] + b'0\n'):
            with self.assertRaises(ValueError): self.final_parse(raw)

    def test_finalized_url_station_month_and_integrity_reject(self):
        for raw in (finalized(station='NH'), finalized(day='2026-10-31'), finalized() + finalized()):
            with self.assertRaises(ValueError): self.final_parse(raw)
        raw = finalized()
        for key, value in [('sha256', '0' * 64), ('station_name', '古仁屋'),
                           ('derived_at', '2026-11-03T07:00:00+00:00'),
                           ('resolved_url', finalized_receipt(raw)['resolved_url'].replace('/2026/', '/2025/')),
                           ('resolved_url', finalized_receipt(raw)['resolved_url'].replace('O9.txt', 'NH.txt')),
                           ('resolved_url', finalized_receipt(raw)['resolved_url'].replace('202611', '202610'))]:
            rec = finalized_receipt(raw); rec[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError): self.final_parse(raw, rec=rec)


if __name__ == '__main__':
    unittest.main()
