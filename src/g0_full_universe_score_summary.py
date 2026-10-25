"""Complete-source diagnostic reduction, never native prediction/fit authority.

No target payload, public row iterator, arbitrary consumer or estimator is used.
Model/TRAIN declarations remain caller assertions even after byte verification.
"""
from __future__ import annotations

from fractions import Fraction
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

import g0_forecast_contract as g0
import prospective_inputs as pi
import research_candidate_config_source as config_source
import research_model_adapter as adapter
from master_contracts import validate_night
from master_inventory import local_path
from models import hba1_feature_candidate as hba1
from models import occupancy_shrinkage as a0
from models import research_selection as selection

VERSION = 'habu-g0-full-universe-score-summary-v1'
SOURCE_VERSION = 'habu-g0-full-universe-score-source-v1'
LINEAGE_VERSION = 'habu-g0-fitted-lineage-declaration-v1'
SEMANTICS = 'MEAN_NATIVE_UNIT_SPATIAL_SCORE'
MAX_METADATA_BYTES = 16*1024**2
MAX_OUTPUT_BYTES = 16*1024**2
MAX_PROFILE_BYTES = 256*1024
MAX_MODEL_BYTES = 4*1024**2
MAX_AREAS = 10_000
MAX_STATES = 30_000
MAX_SUM_BITS = 1097
MAX_FRAME_BYTES = 4096
PROFILE_FIELDS = {'schema_version','kind','operational_night','fit_cutoff','forecast_cutoff',
    'feature_definition_sha256','forecast_manifest','candidate_config_manifest','fit_lineage',
    'models','readiness','usable_at'}
LINEAGE_FIELDS = {'schema_version','kind','heldout_night','fit_cutoff','selection_sha256','corpus_sha256',
    'source_sha256','source_received_at','training_nights','training_window_start_max','counts','feature_names',
    'training_rows_sha256','training_row_ids_sha256','raw_feature_rows_sha256','model_sha256_by_id'}
BOUND_FIELDS = {'ref','readiness','usable_at'}
AUTHORITY_KEYS = ('fit_authorized','selection_authorized','promotion_authorized',
    'scientific_execution_authorized','official_issuance_authorized','production_activation_authorized',
    'confirmation_authorized','trusted_campaign_authorized','trusted_pre_reveal_authorized')


class ScoreSummarySourceBlocked(ValueError):
    """Missing or consistently unavailable metadata; never source authentication."""


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact score-summary declaration fields required')


def _cap(value, maximum, label):
    if value > maximum:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: score-summary '+label)


def _bounded(value, check):
    pending, count = [(value,0)], 0
    while pending:
        check()
        item,depth = pending.pop();count += 1
        _cap(count,2_000_000,'metadata nodes');_cap(depth,12,'metadata depth')
        kind = type(item)
        if kind in (dict,list):
            _cap(count+len(pending)+len(item),2_000_000,'pending metadata nodes')
            if kind is dict:
                for key in item:
                    check()
                    if type(key) is not str or len(key)>512:
                        raise ValueError('Bounded string metadata keys required')
            pending.extend((child,depth+1) for child in (item.values() if kind is dict else item))
        elif kind is str:
            if len(item)>4096 or len(item.encode('utf-8'))>4096:
                raise ValueError('Bounded score-summary string required')
        elif kind is int:
            if item.bit_length()>64:
                raise pi.InputCapacityError('CAPACITY_BLOCKED: metadata integer width')
        elif kind is float:
            if not math.isfinite(item):raise ValueError('Finite metadata required')
        elif kind not in (bool,type(None)):
            raise ValueError('JSON-only score-summary metadata required')


def _encoded(value, check, limit):
    encoder = json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    raw = bytearray()
    for chunk in encoder.iterencode(value):
        check()
        data=chunk.encode('utf-8')
        _cap(len(raw)+len(data),limit,'encoded bytes')
        raw.extend(data)
    check()
    return bytes(raw)


def _digest(value, check, limit=MAX_METADATA_BYTES):
    result=hashlib.sha256(_encoded(value,check,limit)).hexdigest()
    check()
    return result


def _ref(ref, purpose):
    _fields(ref,g0.REF_FIELDS)
    g0._ref(ref)
    path=ref['path']
    if (any(part.casefold() in config_source.RESERVED or part.casefold() in {'raw','outcome','outcomes'}
            for part in path.split('/')) or any(ord(c)<32 or ord(c)==127 for c in path)):
        raise ValueError('Reserved score-summary metadata namespace')
    if purpose=='forecast':g0._input_ref(ref)
    elif purpose=='model':
        if not path.startswith('models/candidates/') or not path.endswith('.json'):
            raise ValueError('Model artifact namespace required')
    else:config_source.input_ref(ref)
    return dict(ref)


def _preflight(root, ref, purpose, check):
    ref=_ref(ref,purpose)
    check();target=local_path(root,ref['path']);check()
    if not target.is_file():raise ScoreSummarySourceBlocked('SOURCE_BLOCKED: missing '+ref['path'])
    check()
    return ref


def _ready(node, parents, check):
    _fields(node['readiness'],pi.READINESS_FIELDS)
    stamps=[]
    for key in sorted(pi.READINESS_FIELDS):
        check();stamps.append(pi._time(node['readiness'][key]))
    usable=pi._time(node['usable_at'])
    if usable != max(*stamps,*parents):raise ValueError('Score-summary usable_at differs from readiness maximum')
    return usable


def _counts(value):
    _fields(value,{'accepted_rows','rejected_rows','nights','positives','negatives'})
    if (any(type(n) is not int or not 0<=n<=20_000 for n in value.values()) or
            value['positives']+value['negatives']!=value['accepted_rows'] or
            value['accepted_rows']+value['rejected_rows']>20_000 or value['nights']>value['accepted_rows']):
        raise ValueError('Contradictory TRAIN count declaration')


def _lineage(value, choices, night, fit, check):
    _fields(value,LINEAGE_FIELDS)
    if (value['schema_version']!=LINEAGE_VERSION or value['kind']!='LABEL_FREE_TRAIN_IDENTITY_DECLARATION' or
            value['heldout_night']!=night or pi._time(value['fit_cutoff'])!=fit):
        raise ValueError('TRAIN identity version/night/fit mismatch')
    for key in ('selection_sha256','corpus_sha256','training_rows_sha256','training_row_ids_sha256','raw_feature_rows_sha256'):
        check();hba1._hash(value[key])
    names=selection._names(value['feature_names'])
    if names!=sorted(names):raise ValueError('TRAIN sidecar feature schema must be sorted')
    _counts(value['counts'])
    nights=value['training_nights']
    if type(nights) is not list or not nights or len(nights)>20_000:
        raise ValueError('Bounded declared TRAIN nights required')
    for earlier in nights:
        check();validate_night(earlier)
        if earlier>=night or pi._time(earlier+'T07:00:00+09:00')>=fit:
            raise ValueError('Declared TRAIN night conflicts with fit/heldout')
    if nights!=sorted(set(nights)) or len(nights)!=value['counts']['nights']:
        raise ValueError('TRAIN night ordering/count mismatch')
    if selection._window(value['training_window_start_max'],nights[-1])>=fit:
        raise ValueError('Latest TRAIN window must precede fit')
    selection._sources(value['source_sha256'],value['source_received_at'],fit,check=check)
    # The legacy selection retains unused/rejected later sources. This NEW
    # label-free strict declaration, unlike that legacy boundary, asserts all
    # retained received times precede fit. Never change the legacy semantics.
    for stamp in value['source_received_at'].values():
        check()
        if pi._time(stamp)>=fit:raise ValueError('Declared TRAIN source received time must strictly precede fit')
    _fields(value['model_sha256_by_id'],set(choices))
    for sha in value['model_sha256_by_id'].values():
        check()
        if sha is not None:hba1._hash(sha)


def _model(value, ident, config, night, fit, check):
    if ident=='uniform':result=adapter._validate_uniform_model(value,check)
    elif ident=='HB-A0':result=a0._validate_model(value,check=check)
    else:
        result=hba1._model(value,check)
        if result['recipe']!=config['hba1_recipe'] or result['feature_names']!=list(hba1.FEATURES):
            raise ValueError('Full native HB-A1 recipe/feature order differs from config')
    selection_field='selection_sha256' if ident=='HB-A0' else 'training_selection_sha256'
    fit_field='training_cutoff' if ident=='uniform' else 'fit_cutoff'
    if pi._time(result[fit_field])!=fit or ident!='uniform' and result['heldout_night']!=night:
        raise ValueError('Native model fit/night differs from source profile')
    return result,selection_field


class _ExactMean:
    """Bounded exact binary64 probability mean; no retained unit list."""
    def __init__(self,check):
        self.check,self.count,self.total=check,0,0

    def add(self,score):
        self.check();score=selection._finite(score)
        if not 0<=score<=1:raise ValueError('Native probability outside [0,1]')
        _cap(self.count+1,g0.MAX_DOMAIN_ROWS,'area unit count')
        numerator,denominator=score.as_integer_ratio()
        shift=1074-(denominator.bit_length()-1)
        _cap(numerator.bit_length()+shift if numerator else 0,MAX_SUM_BITS,'exact probability sum width')
        self.check();term=numerator<<shift;maximum=(1<<MAX_SUM_BITS)-1
        if self.total>maximum-term:raise pi.InputCapacityError('CAPACITY_BLOCKED: exact probability sum width')
        self.check();self.total+=term;self.count+=1

    def value(self):
        self.check()
        if not self.count:raise ValueError('No invented mean for empty score state')
        result=float(Fraction(self.total,self.count<<1074))
        self.check()
        return result


def _normalized_claim(key,value,check):
    if key=='training_window_start_max':return pi._time(value)
    if key=='source_received_at':
        normalized={}
        for path,stamp in value.items():
            check();normalized[path]=pi._time(stamp)
        return normalized
    return value


class _ScoreReducer:
    """Only the fixed G0 internal consumer; never exported as a row interface."""
    def __init__(self,root,context,check,reader,profile,config,config_receipt,models,lineage,initial_bytes,source_ref):
        self.root,self.context,self.check,self.reader=root,context,check,reader
        self.profile,self.config,self.config_receipt=profile,config,config_receipt
        self.models,self.lineage,self.initial_bytes=models,lineage,initial_bytes
        self.source_ref=source_ref
        self.blockers=[]
        if lineage is None:self.blockers.append('MISSING_LABEL_FREE_TRAIN_IDENTITY')
        for ident,model in models.items():
            if model is None:self.blockers.append('MISSING_MODEL:'+ident)
        self.count=0;self.area_counts={};self.states={};self.hashes={}
        self.raw_complete=False

    def _prepare(self,cells,definitions,cutoff):
        check=self.check
        if cutoff!=pi._time(self.profile['forecast_cutoff']):raise ValueError('G0/source profile cutoff mismatch')
        self.raw_complete=set(hba1.FEATURES).issubset(definitions)
        if sorted(definitions)!=sorted(hba1.FEATURES):self.blockers.append('HB_A1_REQUIRES_EXACT_SEVEN_RAW_FEATURE_SCHEMA')
        if self.lineage is not None and self.lineage['feature_names']!=sorted(hba1.FEATURES):
            self.blockers.append('HB_A1_REQUIRES_EXACT_SEVEN_TRAIN_FEATURE_SCHEMA')
        for cx,cy in cells:
            check();area=selection.area_id(cx,cy)
            if area not in self.area_counts:
                _cap(len(self.area_counts)+1,MAX_AREAS,'area count');self.area_counts[area]=0
        if self.blockers:return
        _cap(3*len(self.area_counts),MAX_STATES,'model-area states')
        for ident,model in self.models.items():
            check();self.states[ident]={}
            for area in self.area_counts:
                check();self.states[ident][area]=_ExactMean(check)
            header=dict(candidate_id=ident,model_sha256=model['model_sha256'],
                recipe_sha256=model.get('recipe_sha256'),candidate_config_sha256=self.config_receipt['config_sha256'],
                feature_definition_sha256=self.profile['feature_definition_sha256'],
                training_selection_sha256=self.lineage['selection_sha256'],fit_lineage_sha256=self.profile['fit_lineage']['lineage_sha256'],
                operational_night=self.profile['operational_night'],fit_cutoff=self.profile['fit_cutoff'],
                forecast_cutoff=self.profile['forecast_cutoff'],score_semantics=SEMANTICS)
            self.hashes[ident]=hashlib.sha256(b'HABU-G0-SCORE-STREAM-V1\0')
            self._frame(ident,b'H',header)

    def _frame(self,ident,tag,value):
        raw=_encoded(value,self.check,MAX_FRAME_BYTES)
        self.hashes[ident].update(tag+len(raw).to_bytes(8,'big')+raw);self.check()

    def _add(self,row):
        check=self.check;check()
        cx,cy=selection._future_coordinates(row)
        stamp=selection._window(row['window_start_jst'],self.profile['operational_night'])
        if stamp<=pi._time(self.profile['forecast_cutoff']):raise ValueError('Forecast row must follow cutoff')
        adapter._v2_supplied_hba1_raw_fields([row],check)
        area=selection.area_id(cx,cy)
        if area not in self.area_counts:raise ValueError('Scored row outside physical domain')
        _cap(self.count+1,g0.MAX_DOMAIN_ROWS,'whole unit count')
        self.area_counts[area]+=1
        # Validate all calculable supplied scalars even when an unrelated gap
        # prevents publication. Missing fields never get invented to do so.
        for ident,model in self.models.items():
            check()
            if model is None or ident=='HB-A1' and not self.raw_complete:continue
            if ident=='uniform':score=model['probability']
            elif ident=='HB-A0':score=a0._probability_for_area(model,area)
            else:score=hba1._score_owned_row(model,row,check)
            score=selection._finite(score)
            if not 0<=score<=1:raise ValueError('Native probability outside [0,1]')
            if not self.blockers:
                self.states[ident][area].add(score)
                self._frame(ident,b'R',dict(ordinal=self.count,row_id=row['row_id'],native_score=score))
        self.count+=1;check()

    def _rescan_metadata(self):
        config_source.recheck_research_candidate_config(self.root,self.config_receipt,context=self.context)
        self.reader.rescan();self.check()

    def _finish(self,receipt,forecast_refs):
        check=self.check
        config_source._membership(self.root,set(self.config_receipt['code_sha256_by_path']),check)
        if self.count!=receipt['row_count'] or sum(self.area_counts.values())!=self.count:
            raise ValueError('Summary/complete G0 count mismatch')
        summaries=[]
        if not self.blockers:
            for ident,model in self.models.items():
                check();areas=[]
                self._frame(ident,b'T',dict(row_count=self.count,canonical_joined_rows_sha256=receipt['canonical_joined_rows_sha256']))
                for area in sorted(self.area_counts):
                    check();state=self.states[ident][area]
                    if state.count!=self.area_counts[area] or not state.count:raise ValueError('Incomplete model-area score coverage')
                    score=state.value()
                    areas.append(dict(area_id=area,unit_count=state.count,mean_native_score=score))
                def key(item):check();return (-item['mean_native_score'],item['area_id'])
                top=[item['area_id'] for item in sorted(areas,key=key)[:10]]
                summaries.append(dict(candidate_id=ident,model_sha256=model['model_sha256'],recipe_sha256=model.get('recipe_sha256'),
                    score_semantics=SEMANTICS,score_stream_sha256=self.hashes[ident].hexdigest(),unit_count=self.count,
                    area_summaries=areas,top10_area_ids=top))
        refs={}
        for ref in [*self.config_receipt['consumed_refs'],*self.reader.refs.values(),*forecast_refs.values()]:
            check()
            if ref['path'] in refs and refs[ref['path']]!=ref:raise ValueError('Conflicting final source binding')
            refs[ref['path']]=dict(ref)
        result=dict(schema_version=VERSION,summary_kind='UNCONNECTED_DIAGNOSTIC_ONLY',
            status='NEED_MORE_DATA' if self.blockers else 'COMPLETE_DECLARED_SCORE_SUMMARY',blockers=list(self.blockers),
            source_manifest_ref=dict(self.source_ref),source_manifest_canonical_sha256=_digest(self.profile,check),
            operational_night=self.profile['operational_night'],fit_cutoff=self.profile['fit_cutoff'],forecast_cutoff=self.profile['forecast_cutoff'],
            candidate_ids=list(self.config['candidate_ids']),candidate_config_sha256=self.config_receipt['config_sha256'],
            candidate_config_source_receipt=self.config_receipt,feature_definition_sha256=self.profile['feature_definition_sha256'],
            fit_lineage=self.profile['fit_lineage'],training_selection_sha256=self.lineage['selection_sha256'] if self.lineage else None,
            model_bindings=self.profile['models'],forecast_receipt=receipt,
            full_counts=dict(cell_count=receipt['cell_count'],window_count=receipt['window_count'],shard_count=receipt['shard_count'],
                unit_count=self.count,area_count=len(self.area_counts)),model_summaries=summaries,
            consumed_refs=list(refs.values()),consumed_sha256={path:ref['sha256'] for path,ref in refs.items()},
            actual_read_bytes=self.context.bytes_read,summary_read_bytes=self.context.bytes_read-self.initial_bytes,
            source_authenticity='NOT_ATTESTED',source_authentication='CALLER_DEPENDENCY_REQUIRED',
            fit_lineage_authentication='CALLER_DEPENDENCY_REQUIRED',scientific_status='NOT_VALIDATED',
            authorities=dict.fromkeys(AUTHORITY_KEYS,False),limitations=[
                'CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY','DECLARED_DOMAIN_ONLY','MODEL_TRAIN_LINEAGE_IS_CALLER_ASSERTED',
                'NO_TARGET_PAYLOAD_FIT_CONFIRMATION_OR_EVALUATION','NOT_NATIVE_PREDICTION_PREPARED_STAGE1_OR_PARENT_TRANSPORT',
                'NO_TRUSTED_ISSUER_CAMPAIGN_PREREVEAL_OR_LOADED_RUNTIME_AUTHENTICATION'])
        result['summary_sha256']=_digest(result,check,MAX_OUTPUT_BYTES)
        _encoded(result,check,MAX_OUTPUT_BYTES);check()
        return result


def score_g0_forecast_summary(root,summary_manifest_ref,operational_night,as_of,*,
        expected_feature_definition_sha256,expected_candidate_config_sha256,
        budget_seconds=30,_read_context=None,check=None):
    """Return a sealed complete diagnostic or whole-set NMD; never rows/fit."""
    source_ref=_ref(summary_manifest_ref,'profile')
    if (type(budget_seconds) not in (int,float) or not 0<budget_seconds<=300 or
            not math.isfinite(budget_seconds)):
        raise ValueError('Elapsed budget must be finite, positive and at most 300 seconds')
    expected=hba1._hash(expected_feature_definition_sha256)
    expected_config=hba1._hash(expected_candidate_config_sha256)
    validate_night(operational_night)
    if check is not None and not callable(check):raise ValueError('Deadline check must be callable')
    if not isinstance(as_of,datetime) or as_of.utcoffset() is None:
        raise ValueError('Aware actual as_of required')
    context=_read_context
    if context is None:context=pi.ProspectiveReadContext(budget_seconds,g0.MAX_TOTAL_READ_BYTES)
    elif isinstance(context,pi.ProspectiveReadContext):context.restrict(budget_seconds,g0.MAX_TOTAL_READ_BYTES)
    else:raise ValueError('Shared prospective context required')
    initial=context.bytes_read
    previous=context.__dict__.get('check');native=context.check
    def guard():
        if check is not None:check()
        native()
    context.check=guard
    try:
        guard();root=Path(root).absolute()
        _preflight(root,source_ref,'profile',guard)
        _cap(source_ref['size_bytes'],MAX_PROFILE_BYTES,'profile bytes')
        reader=g0.G0ArtifactReader(root,context)
        profile=reader.read(source_ref,small=True);_bounded(profile,guard);_fields(profile,PROFILE_FIELDS)
        config_source._stamps(profile,guard)
        fit,cutoff=pi._time(profile['fit_cutoff']),pi._time(profile['forecast_cutoff'])
        if (profile['schema_version']!=SOURCE_VERSION or profile['kind']!='UNCONNECTED_DEVELOPMENT_SCORE_SUMMARY' or
                profile['operational_night']!=operational_night or profile['feature_definition_sha256']!=expected or
                not fit<pi._time(operational_night+'T07:00:00+09:00') or not fit<cutoff or cutoff>as_of):
            raise ValueError('Score source version/time/definition mismatch')
        metadata_refs=[source_ref];pending_refs=[]
        for key,purpose in (('forecast_manifest','forecast'),('candidate_config_manifest','profile')):
            pending_refs.append((_ref(profile[key],purpose),purpose))
        if type(profile['models']) is not list or len(profile['models'])!=3:raise ValueError('Exact three models required')
        bindings=[]
        if profile['fit_lineage'] is not None:
            _fields(profile['fit_lineage'],BOUND_FIELDS|{'lineage_sha256'})
            bindings.append((profile['fit_lineage'],'profile',MAX_PROFILE_BYTES))
        for entry in profile['models']:
            _fields(entry,{'candidate_id','artifact'})
            if entry['artifact'] is not None:
                _fields(entry['artifact'],BOUND_FIELDS|{'model_sha256'})
                bindings.append((entry['artifact'],'model',MAX_MODEL_BYTES))
        ids=[entry['candidate_id'] for entry in profile['models']]
        if (any(type(ident) is not str or ident not in {'uniform','HB-A0','HB-A1','HB-B1'} for ident in ids) or
                ids[0]!='uniform' or len(set(ids))!=3):
            raise ValueError('Unique known ordered model identities required')
        for binding,purpose,maximum in bindings:
            guard();ref=_ref(binding['ref'],purpose)
            _cap(ref['size_bytes'],maximum,'metadata file bytes')
            config_source._stamps(binding,guard)
            hba1._hash(binding['model_sha256' if purpose=='model' else 'lineage_sha256'])
            pending_refs.append((ref,purpose))
        for ref,purpose in pending_refs:
            metadata_refs.append(_preflight(root,ref,purpose,guard))
        if len({r['path'] for r in metadata_refs})!=len(metadata_refs):raise ValueError('Metadata role/path alias')
        configured=config_source.load_research_candidate_config(root,profile['candidate_config_manifest'],
            heldout_night=operational_night,fit_cutoff=profile['fit_cutoff'],forecast_cutoff=profile['forecast_cutoff'],
            expected_feature_definition_sha256=expected,context=context)
        config,config_receipt=configured['config'],configured['receipt']
        if config_receipt['config_sha256']!=expected_config:raise ValueError('Expected config canonical hash mismatch')
        choices=config['candidate_ids']
        if [e['candidate_id'] for e in profile['models']]!=choices:raise ValueError('Ordered model/config IDs mismatch')
        if set(choices)!={'uniform','HB-A0','HB-A1'}:
            raise g0.ForecastCapabilityError('IMPLEMENTATION_BLOCKED: native global/conditional HB-B1 ranks not supported')
        config_ready=pi._time(config_receipt['usable_at'])
        raw_forecast=reader.read(profile['forecast_manifest'],small=True)
        if 'usable_at' not in raw_forecast:raise ValueError('Forecast manifest usable_at is required')
        forecast_ready=pi._time(raw_forecast['usable_at'])
        lineage=None;lineage_ready=config_ready;ready=[config_ready,forecast_ready]
        if profile['fit_lineage'] is not None:
            binding=profile['fit_lineage'];lineage=reader.read(binding['ref'],small=True);_bounded(lineage,guard)
            if _digest(lineage,guard)!=hba1._hash(binding['lineage_sha256']):raise ValueError('TRAIN lineage canonical hash mismatch')
            _lineage(lineage,choices,operational_night,fit,guard)
            lineage_ready=_ready(binding,[config_ready],guard);ready.append(lineage_ready)
        raw_models={}
        for entry in profile['models']:
            guard();binding=entry['artifact']
            value=reader.read(binding['ref'],small=True) if binding is not None else None
            raw_models[entry['candidate_id']]=value
        # Reader payloads are already invocation-owned. Bound the COMBINED
        # tokens/bytes before any native guard makes an additional owned copy.
        _bounded([profile,config,lineage,raw_models],guard)
        _encoded([profile,config,lineage,raw_models],guard,MAX_METADATA_BYTES)
        models={};anchor=None;common_claims={}
        for entry in profile['models']:
            guard();ident=entry['candidate_id'];binding=entry['artifact'];models[ident]=None
            if binding is None:
                if lineage is not None and lineage['model_sha256_by_id'][ident] is not None:
                    raise ValueError('Missing model contradicts declared TRAIN model identity')
                continue
            value=raw_models[ident]
            model,selection_field=_model(value,ident,config,operational_night,fit,guard)
            if model['model_sha256']!=hba1._hash(binding['model_sha256']):raise ValueError('Model canonical/byte reference mismatch')
            claim=(model[selection_field],model['counts'])
            if anchor is not None and anchor!=claim:raise ValueError('Different models claim different common TRAIN')
            anchor=claim
            # A missing sidecar cannot hide contradictions between retained
            # native fields already supplied by different models.
            for key in ('corpus_sha256','source_sha256','source_received_at','training_nights','training_window_start_max',
                        'training_rows_sha256','training_row_ids_sha256','raw_feature_rows_sha256'):
                guard()
                if key not in model:continue
                retained=_normalized_claim(key,model[key],guard)
                if key in common_claims and common_claims[key]!=retained:
                    raise ValueError('Native models disagree on retained TRAIN field: '+key)
                common_claims[key]=retained
            native_names=model.get('selection_feature_names') if ident=='HB-A0' else sorted(model['feature_names']) if ident=='HB-A1' else None
            if native_names is not None:
                if 'feature_names' in common_claims and common_claims['feature_names']!=native_names:
                    raise ValueError('Native models disagree on TRAIN feature projection')
                common_claims['feature_names']=native_names
            if lineage is not None:
                if (model[selection_field]!=lineage['selection_sha256'] or model['counts']!=lineage['counts'] or
                        model['model_sha256']!=lineage['model_sha256_by_id'][ident]):
                    raise ValueError('Model differs from common TRAIN declaration')
                for key in ('corpus_sha256','source_sha256','source_received_at','training_nights','training_window_start_max',
                            'training_rows_sha256','training_row_ids_sha256','raw_feature_rows_sha256'):
                    guard()
                    if key not in model:continue
                    left,right=_normalized_claim(key,model[key],guard),_normalized_claim(key,lineage[key],guard)
                    if left!=right:raise ValueError('Retained model/TRAIN field mismatch: '+key)
                names=model.get('selection_feature_names') if ident=='HB-A0' else sorted(model['feature_names']) if ident=='HB-A1' else None
                if names is not None and names!=lineage['feature_names']:raise ValueError('Model/TRAIN feature projection mismatch')
            models[ident]=model;ready.append(_ready(binding,[config_ready,lineage_ready],guard))
        _encoded([profile,config,lineage,models],guard,MAX_METADATA_BYTES)
        usable=_ready(profile,ready,guard)
        late=usable>=cutoff
        reducer=_ScoreReducer(root,context,guard,reader,profile,config,config_receipt,models,lineage,initial,source_ref)
        # The existing physical validator owns all rows, completeness and joined SHA.
        result=g0._validate(root,profile['forecast_manifest'],operational_night,as_of,expected,
            min(budget_seconds,context.remaining_seconds),False,context,_summary=reducer)
        if late:raise ScoreSummarySourceBlocked('SOURCE_BLOCKED: metadata unavailable before forecast cutoff')
        guard()
        return result
    finally:
        if previous is None:del context.check
        else:context.check=previous
