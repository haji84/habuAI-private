"""Fixed uniform/A1/A2 complete-domain diagnostic, never native prediction.

The existing context, validators and scalar kernels remain the executors.
No fit/backend/outcome reader, arbitrary callback, registry or writer is used.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

import g0_forecast_contract as g0
import prospective_inputs as pi
import research_candidate_config_source as config_old
import research_candidate_config_source_v2 as config_source
import research_model_adapter as adapter
from master_contracts import validate_night
from models import hba1_feature_candidate as hba1, hba2_feature_candidate as hba2
from models import research_selection as selection
from g0_full_universe_score_summary import (
    SEMANTICS, MAX_METADATA_BYTES, MAX_OUTPUT_BYTES, MAX_PROFILE_BYTES, MAX_MODEL_BYTES,
    MAX_AREAS, MAX_STATES, MAX_FRAME_BYTES, PROFILE_FIELDS, BOUND_FIELDS, AUTHORITY_KEYS,
    ScoreSummarySourceBlocked, _fields, _cap, _bounded, _encoded, _digest, _ref,
    _preflight, _ready, _lineage, _normalized_claim, _ExactMean)

VERSION='habu-g0-full-universe-score-summary-v2'
SOURCE_VERSION='habu-g0-full-universe-score-source-v2'
CANDIDATES=('uniform','HB-A1','HB-A2')
_CONSTRUCTION=object()  # Internal ownership binding, never source/issuer authority.


def _context(context):
    if not isinstance(context,pi.ProspectiveReadContext):
        raise ValueError('Existing actual prospective read context required')
    if type(context.max_bytes) is not int or not 0<context.max_bytes<=g0.MAX_TOTAL_READ_BYTES:
        raise ValueError('Existing byte allowance must be positive and at most2GiB')
    if type(context.bytes_read) is not int or context.bytes_read<0:
        raise ValueError('Existing nonnegative actual byte ledger required')
    context.check()
    if context.bytes_read>=context.max_bytes:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: existing summary allowance exhausted')
    if not 0<context.remaining_seconds<=300:
        raise ValueError('Existing remaining elapsed allowance must be positive and at most300s')


def _copy(value,check):
    # Bound before copying, preserve native child insertion order, separate aliases.
    _bounded(value,check);raw=bytearray()
    for part in json.JSONEncoder(sort_keys=False,separators=(',',':'),ensure_ascii=False,allow_nan=False).iterencode(value):
        check();data=part.encode('utf-8');_cap(len(raw)+len(data),MAX_OUTPUT_BYTES,'owned final bytes');raw.extend(data)
    check();result=json.loads(raw);check();return result


def _model(value,ident,config,night,fit,check):
    if ident=='uniform':model=adapter._validate_uniform_model(value,check)
    else:
        kernel=hba1 if ident=='HB-A1' else hba2
        model=kernel._model(value,check)
        recipe=config['hba1_recipe' if ident=='HB-A1' else 'hba2_recipe']
        if model['recipe']!=recipe or model['feature_names']!=list(kernel.FEATURES):
            raise ValueError('Full native recipe/feature order differs from cfgv3')
    field='training_cutoff' if ident=='uniform' else 'fit_cutoff'
    if pi._time(model[field])!=fit or ident!='uniform' and model['heldout_night']!=night:
        raise ValueError('Native model fit/night differs from source profile')
    return model,'training_selection_sha256'


class _ScoreReducerV2:
    """Only the fixed G0 internal consumer; never exported as a row interface."""
    __slots__=('root','context','reader','profile','config','config_receipt','models','lineage',
        'initial_bytes','source_ref','blockers','count','area_counts','states','hashes','raw_complete','_binding')

    def __setattr__(self,name,value):
        raise AttributeError('Fixed owned reducer attributes cannot be replaced')

    @property
    def check(self):
        return self.context.check

    def __init__(self,root,context,reader,profile,config,config_receipt,models,lineage,initial_bytes,source_ref,*,_owner):
        root=Path(root).absolute()
        if (_owner is not _CONSTRUCTION or type(reader) is not g0.G0ArtifactReader or
                reader.context is not context or reader.root!=root or
                set(reader.__dict__)!={'root','context','refs','_limits'} or
                type(reader.refs) is not dict or type(reader._limits) is not dict):
            raise ValueError('Fixed owned source reader/construction required')
        blockers=[]
        if lineage is None:blockers.append('MISSING_LABEL_FREE_TRAIN_IDENTITY')
        for ident,model in models.items():
            if model is None:blockers.append('MISSING_MODEL:'+ident)
        values=dict(root=root,context=context,reader=reader,profile=profile,config=config,config_receipt=config_receipt,
            models=models,lineage=lineage,initial_bytes=initial_bytes,source_ref=source_ref,blockers=blockers,
            count=0,area_counts={},states={},hashes={},raw_complete=False,_binding=(_CONSTRUCTION,root,context,reader))
        for name,value in values.items():object.__setattr__(self,name,value)

    def _admitted(self,root,context):
        if not all(hasattr(self,name) for name in _ScoreReducerV2.__slots__):return False
        binding=self._binding;reader=self.reader
        return (type(binding) is tuple and len(binding)==4 and binding[0] is _CONSTRUCTION and
            binding[1] is self.root and binding[2] is self.context and binding[3] is reader and
            self.context is context and self.root==Path(root).absolute() and type(reader) is g0.G0ArtifactReader and
            reader.context is context and reader.root==self.root and set(reader.__dict__)=={'root','context','refs','_limits'} and
            type(reader.refs) is dict and type(reader._limits) is dict)

    def _prepare(self,cells,definitions,cutoff):
        check=self.check
        if cutoff!=pi._time(self.profile['forecast_cutoff']):raise ValueError('G0/source profile cutoff mismatch')
        object.__setattr__(self,'raw_complete',set(hba1.FEATURES).issubset(definitions))
        if not set(definitions).issubset(hba1.FEATURES):raise ValueError('Extra raw feature outside fixed seven-column schema')
        if sorted(definitions)!=sorted(hba1.FEATURES):self.blockers.append('HB_A1_A2_REQUIRE_EXACT_SEVEN_RAW_FEATURE_SCHEMA')
        if self.lineage is not None and not set(self.lineage['feature_names']).issubset(hba1.FEATURES):
            raise ValueError('Extra TRAIN feature outside fixed seven-column schema')
        if self.lineage is not None and self.lineage['feature_names']!=sorted(hba1.FEATURES):
            self.blockers.append('HB_A1_A2_REQUIRE_EXACT_SEVEN_TRAIN_FEATURE_SCHEMA')
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
            self.hashes[ident]=hashlib.sha256(b'HABU-G0-SCORE-STREAM-V2\0')
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
        # Every supplied known field is cast even on whole-set NEED paths.
        for name,value in row['features'].items():
            check()
            if name in hba2.FEATURES:hba2._f32(value)
        area=selection.area_id(cx,cy)
        if area not in self.area_counts:raise ValueError('Scored row outside physical domain')
        _cap(self.count+1,g0.MAX_DOMAIN_ROWS,'whole unit count')
        self.area_counts[area]+=1
        # Validate all calculable supplied scalars even when an unrelated gap
        # prevents publication. Missing fields never get invented to do so.
        for ident,model in self.models.items():
            check()
            if model is None or ident!='uniform' and not self.raw_complete:continue
            if ident=='uniform':score=model['probability']
            elif ident=='HB-A1':score=hba1._score_owned_row(model,row,check)
            else:
                cast=[]
                for name in hba2.FEATURES:check();cast.append(hba2._f32(row['features'][name]))
                score=round(hba2._raw_prob(model['trees'],[cast],check)[1][0],8)
            score=selection._finite(score)
            if not 0<=score<=1:raise ValueError('Native probability outside [0,1]')
            if not self.blockers:
                self.states[ident][area].add(score)
                self._frame(ident,b'R',dict(ordinal=self.count,row_id=row['row_id'],native_score=score))
        object.__setattr__(self,'count',self.count+1);check()

    def _rescan_metadata(self):
        config_old.recheck_research_candidate_config(self.root,self.config_receipt,context=self.context)
        self.reader.rescan();self.check()

    def _finish(self,receipt,forecast_refs):
        check=self.check
        config_old._membership(self.root,set(self.config_receipt['code_sha256_by_path']),check)
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
        result=_copy(result,check)
        result['summary_sha256']=_digest(result,check,MAX_OUTPUT_BYTES)
        _encoded(result,check,MAX_OUTPUT_BYTES);check()
        return result


def score_g0_forecast_summary_v2(root,summary_manifest_ref,operational_night,as_of,*,
        expected_feature_definition_sha256,expected_candidate_config_sha256,context):
    """One complete fixed-three diagnostic; no mutable context/child rewriting."""
    source_ref=_ref(summary_manifest_ref,'profile')
    expected=hba1._hash(expected_feature_definition_sha256)
    expected_config=hba1._hash(expected_candidate_config_sha256)
    validate_night(operational_night)
    if not isinstance(as_of,datetime) or as_of.utcoffset() is None:
        raise ValueError('Aware actual as_of required')
    _context(context);initial=context.bytes_read
    def guard():context.check()
    guard();root=Path(root).absolute()
    _preflight(root,source_ref,'profile',guard)
    _cap(source_ref['size_bytes'],MAX_PROFILE_BYTES,'profile bytes')
    reader=g0.G0ArtifactReader(root,context)
    profile=reader.read(source_ref,small=True);_bounded(profile,guard);_fields(profile,PROFILE_FIELDS)
    config_old._stamps(profile,guard)
    fit,cutoff=pi._time(profile['fit_cutoff']),pi._time(profile['forecast_cutoff'])
    if (profile['schema_version']!=SOURCE_VERSION or profile['kind']!='UNCONNECTED_DEVELOPMENT_SCORE_SUMMARY' or
            profile['operational_night']!=operational_night or profile['feature_definition_sha256']!=expected or
            not fit<pi._time(operational_night+'T07:00:00+09:00') or not fit<cutoff or cutoff>as_of):
        raise ValueError('Score source version/time/definition mismatch')
    # Prevalidate only the delegated pure JST boundary conversion. Neither
    # the source loader nor any caller deadline check enters this catch.
    guard()
    try:
        config_old.cycle.training_boundary(operational_night,profile['fit_cutoff'],profile['forecast_cutoff'])
    except OverflowError as error:
        raise ValueError('Score-summary training boundary exceeds local datetime range') from error
    guard()
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
    if ids!=list(CANDIDATES):raise ValueError('Fixed ordered uniform/A1/A2 models required')
    for binding,purpose,maximum in bindings:
        guard();ref=_ref(binding['ref'],purpose)
        _cap(ref['size_bytes'],maximum,'metadata file bytes')
        config_old._stamps(binding,guard)
        hba1._hash(binding['model_sha256' if purpose=='model' else 'lineage_sha256'])
        pending_refs.append((ref,purpose))
    for ref,purpose in pending_refs:
        metadata_refs.append(_preflight(root,ref,purpose,guard))
    if len({r['path'] for r in metadata_refs})!=len(metadata_refs):raise ValueError('Metadata role/path alias')
    configured=config_source.load_research_candidate_config_v2(root,profile['candidate_config_manifest'],
        heldout_night=operational_night,fit_cutoff=profile['fit_cutoff'],forecast_cutoff=profile['forecast_cutoff'],
        expected_feature_definition_sha256=expected,context=context)
    config,config_receipt=configured['config'],configured['receipt']
    if config_receipt['config_sha256']!=expected_config:raise ValueError('Expected config canonical hash mismatch')
    choices=config['candidate_ids']
    if [e['candidate_id'] for e in profile['models']]!=choices:raise ValueError('Ordered model/config IDs mismatch')
    if choices!=list(CANDIDATES):raise ValueError('Only fixed cfgv3 candidates supported')
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
        native_names=sorted(model['feature_names']) if ident!='uniform' else None
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
            names=sorted(model['feature_names']) if ident!='uniform' else None
            if names is not None and names!=lineage['feature_names']:raise ValueError('Model/TRAIN feature projection mismatch')
        models[ident]=model;ready.append(_ready(binding,[config_ready,lineage_ready],guard))
    _encoded([profile,config,lineage,models],guard,MAX_METADATA_BYTES)
    usable=_ready(profile,ready,guard)
    late=usable>=cutoff
    reducer=_ScoreReducerV2(root,context,reader,profile,config,config_receipt,models,lineage,initial,source_ref,_owner=_CONSTRUCTION)
    # The existing physical validator owns all rows, completeness and joined SHA.
    result=g0._validate(root,profile['forecast_manifest'],operational_night,as_of,expected,
        context.remaining_seconds,False,context,_summary_v2=reducer)
    if late:raise ScoreSummarySourceBlocked('SOURCE_BLOCKED: metadata unavailable before forecast cutoff')
    guard()
    if context.bytes_read!=result['actual_read_bytes']:raise ValueError('Read ledger changed after final summary seal')
    return result
