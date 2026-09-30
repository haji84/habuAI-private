"""Deterministic, bounded learning builder in a derived evaluation workspace.

Never derives a forecast universe from observed tracks or overwrites an input.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from master_contracts import canonical_bytes,digest,file_hash,safe_path,validate_night
from evidence_audit import timestamp,unit_key,VERSION as AUDIT_VERSION

VERSION='learning-builder-v1'
MAX_FILE_BYTES=4*1024*1024
MAX_TOTAL_BYTES=10*1024*1024


def build_learning_snapshot(root,night,audit):
    root=Path(root);validate_night(night)
    result=dict(schema_version='1.0',implementation_version=VERSION,status='BLOCKED',evaluation_root=None,
                input_requirements=[],generated_artifacts=[],scientific_validation='NOT_VALIDATED')
    def need(code,criterion):result['input_requirements'].append(dict(code=code,kind='DATA_BLOCKED',criterion=criterion,evidence_needed=criterion))
    if audit.get('status')=='BLOCKED':
        result.update(reason='Upstream audit runtime blocked',input_requirements=audit.get('input_requirements',[]))
        return result
    if (root/'data/processed/model_learning.json').exists():
        result.update(status='NOT_APPLICABLE',reason='Existing immutable learning input retained',evidence_sha256=file_hash(root/'data/processed/model_learning.json'))
        return result
    request_path='features/learning_build.json'
    if not (root/request_path).exists():
        need('FORECAST_UNIVERSE','Explicit hash-bound ex-ante universe, protocol and availability receipts in features/learning_build.json')
        return result
    generated={};consumed={}
    try:
        from model_evaluation import _coordinates,_validate
        if audit['implementation_version']!=AUDIT_VERSION or audit.get('audit_sha256')!=digest({k:v for k,v in audit.items() if k!='audit_sha256'}):raise ValueError('INVALID_AUDIT_MANIFEST')
        if audit['status']=='FAIL':raise ValueError('UPSTREAM_AUDIT_FAILED')
        for path,sha in audit['input_hashes'].items():
            if file_hash(safe_path(root,path))!=sha:raise ValueError('AUDIT_INPUT_CHANGED')
        def read(path,expected=None):
            if Path(path).parts[0] not in {'features','protocols','evidence','policies'}:raise ValueError('UNAPPROVED_BUILDER_REFERENCE')
            p=safe_path(root,path)
            if p.stat().st_size>MAX_FILE_BYTES:raise ValueError('BUILDER_FILE_LIMIT')
            raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            if expected is not None and sha!=expected:raise ValueError('BUILDER_REFERENCE_HASH')
            consumed[path]=sha
            return raw
        def reference(ref,role):
            raw=read(ref['path'],ref['sha256']);value=json.loads(raw)
            receipt=json.loads(read(ref['receipt_ref']['path'],ref['receipt_ref']['sha256']))
            if receipt['raw_path']!=ref['path'] or receipt['sha256']!=ref['sha256'] or receipt['bytes']!=len(raw):raise ValueError('AVAILABILITY_RECEIPT_BINDING')
            available=timestamp(ref['available_at'])
            if available<timestamp(receipt['received_at_utc']):raise ValueError('AVAILABILITY_BACKDATED_BEFORE_RECEIPT')
            generated[ref['path']]=raw
            return value,dict(path=ref['path'],sha256=ref['sha256'],available_at=available.isoformat(),role=role)
        request=json.loads(read(request_path))
        if request['schema_version']!='1.0':raise ValueError('BUILD_REQUEST_SCHEMA')
        universe,universe_source=reference(request['universe'],'universe')
        protocol,protocol_source=reference(request['protocol'],'protocol')
        if universe['source_type']!='EX_ANTE_FORECAST' or not universe['geographic_domain']:raise ValueError('EX_ANTE_UNIVERSE_REQUIRED')
        feature_inputs=[];sources=[universe_source,protocol_source]
        for ref in request.get('features',[]):
            values,source=reference(ref,'feature')
            if values.get('use_role') not in ('static_predictor','forecast_predictor'):raise ValueError('FEATURE_ROLE_NOT_EX_ANTE')
            if timestamp(values['available_at'])>timestamp(source['available_at']):raise ValueError('FEATURE_AVAILABILITY_CONTRADICTION')
            feature_inputs.append((values,source));sources.append(source)
        observations={(u['cell_x'],u['cell_y'],u['window_start_jst']):u for u in audit['observation_units']}
        events=audit['outcome_ledger']['events'];keys={}
        for e in events:keys.setdefault(unit_key(e['latitude'],e['longitude'],timestamp(e['datetime_jst'])),[]).append(e)
        labels=dict(schema_version='1.0',audit_sha256=audit['audit_sha256'],input_hashes=audit['input_hashes'],
                    source_manifest=audit['source_manifest'],outcome_ledger=audit['outcome_ledger'],observation_units=audit['observation_units'])
        label_path='evidence/built_observations.json';generated[label_path]=canonical_bytes(labels)+b'\n'
        label_source=dict(path=label_path,sha256=hashlib.sha256(generated[label_path]).hexdigest(),available_at=audit['verified_at'],role='label')
        sources.append(label_source);rows=[];inside=set();seen=set()
        for unit in universe['rows']:
            x,y=_coordinates(unit);window=timestamp(unit['window_start_jst']);key=(math.floor(x/100),math.floor(y/100),window.isoformat())
            if key in seen:raise ValueError('DUPLICATE_FORECAST_UNIT')
            seen.add(key);o=observations.get(key,{});matches=keys.get(key,[])
            label=1 if matches else o.get('label');observed=label is not None
            ids=[e['event_id'] for e in matches];inside.update(ids)
            available=max([timestamp(audit['verified_at'])]+[timestamp(e['available_at']) for e in matches]).isoformat() if observed else None
            row=dict(row_id=unit['row_id'],universe_row_id=unit['row_id'],operational_night=unit['operational_night'],
                     cutoff_time=unit['cutoff_time'],window_start_jst=unit['window_start_jst'],cell_x=key[0],cell_y=key[1],
                     observed=observed,label=label,label_available_at=available,quality='AUDITED_OBSERVED' if observed else 'UNKNOWN',
                     capture_count=sum(e['capture_count'] for e in matches),capture_event_ids=ids,
                     features={},feature_available_at={},feature_source_refs={},source_refs=[universe_source['path']]+([label_path] if observed else []))
            for values,source in feature_inputs:
                name=values['feature_name'];value=values['values'][unit['row_id']]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('INVALID_FEATURE_VALUE')
                if name in row['features']:raise ValueError('DUPLICATE_FEATURE')
                row['features'][name]=value;row['feature_available_at'][name]=source['available_at']
                row['feature_source_refs'][name]=[source['path']];row['source_refs'].append(source['path'])
            for field in ('duration_seconds','distance_m','effort_method','observer_version'):
                if observed and o.get(field) is not None:row[field]=o[field]
            rows.append(row)
        ledger=dict(audit['outcome_ledger'],outside_universe_event_ids=sorted(e['event_id'] for e in events if e['event_id'] not in inside))
        snapshot=dict(schema_version='1.0',candidate_universe_sha256=request['universe']['sha256'],
                      universe={k:request['universe'][k] for k in ('path','sha256','available_at')},
                      protocol={k:request['protocol'][k] for k in ('path','sha256','available_at')},
                      source_manifest=sources,rows=rows,outcome_ledger=ledger,builder_version=VERSION)
        generated['data/processed/model_learning.json']=canonical_bytes(snapshot)+b'\n'
        if sum(map(len,generated.values()))>MAX_TOTAL_BYTES or any(len(raw)>MAX_FILE_BYTES for raw in generated.values()):raise ValueError('BUILDER_RECOVERY_BUDGET')
        relative=f'reports/learning_evaluation/{night}';destination=safe_path(root,relative)
        # Validate in an isolated scratch workspace before publishing any derived artifact.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='habu-learning-validation-') as temp:
            checked=Path(temp)
            for path,raw in generated.items():
                target=safe_path(checked,path);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            _validate(checked,'9999-12-30',{},lambda:None)
        for path,sha in {**audit['input_hashes'],**consumed}.items():
            if file_hash(safe_path(root,path))!=sha:raise ValueError('BUILDER_INPUT_CHANGED')
        for path,raw in sorted(generated.items()):
            target=safe_path(destination,path)
            if target.exists() and target.read_bytes()!=raw:raise ValueError('IMMUTABLE_DERIVED_ARTIFACT_CONFLICT')
        for path,raw in sorted(generated.items()):
            target=safe_path(destination,path);target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                with target.open('xb') as stream:stream.write(raw)
            result['generated_artifacts'].append({'path':relative+'/'+path,'sha256':hashlib.sha256(raw).hexdigest()})
        result.update(status='PASS',evaluation_root=relative,reason='Builder contract validated; scientific eligibility remains NOT_VALIDATED',
                      input_hashes=consumed,audit_sha256=audit['audit_sha256'])
    except FileNotFoundError as exc:need('MISSING_BUILDER_INPUT',str(exc))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        result.update(status='FAIL',reason=str(exc))
    return result
