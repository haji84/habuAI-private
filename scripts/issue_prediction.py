#!/usr/bin/env python3
"""Execute verified registered inference. Production authority is fail-closed.

The live sandbox context is Python-test-only and publishes exclusively below its
allocated sandbox namespace. No CLI switch or evidence flag enables it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import champion_registry as registry
from master_contracts import canonical_bytes, digest, file_hash, safe_path, validate_night
from model_evaluation import predict_model, _coordinates
from pdca_pipeline import JST, night_for
from freeze_prediction import _freeze_payload


def _snapshot(root, path, expected, night, now):
    consumed = {}
    def read(reference):
        target = safe_path(root, reference['path'])
        actual = file_hash(target)
        if actual != reference['sha256']:
            raise ValueError('Inference input hash mismatch')
        consumed[target] = actual
        raw = target.read_bytes()
        # Bind bytes actually decoded, not just a hash checked before a mutable read.
        import hashlib
        if hashlib.sha256(raw).hexdigest() != actual:
            raise ValueError('Inference input changed while reading')
        value = json.loads(raw)
        canonical_bytes(value)
        return value
    value = read({'path':path.relative_to(root).as_posix(), 'sha256':expected})
    if not isinstance(value,dict) or value['schema_version']!='1.0' or value['operational_night']!=night:
        raise ValueError('Invalid inference snapshot schema/night')
    cutoff = registry.timestamp(value['cutoff_time'])
    if cutoff > now:
        raise ValueError('Forecast cutoff is after actual issuance')
    universe = read(value['universe'])
    if registry.timestamp(value['universe']['available_at']) >= cutoff:
        raise ValueError('Universe must be available strictly before cutoff')
    if universe['schema_version']!='1.0' or universe['source_type']!='EX_ANTE_FORECAST' or not universe.get('geographic_domain'):
        raise ValueError('Explicit ex-ante geographic universe required')
    # Current baseline models have no feature-aware adapter; do not silently ignore covariates.
    if value['feature_schema_sha256'] != digest([]) or value.get('features') != {}:
        raise ValueError('Unsupported inference feature schema')
    for source in value['source_manifest']:
        if source.get('role') not in ('feature','universe'):
            raise ValueError('Inference source role must be feature/universe')
        if registry.timestamp(source['available_at']) >= cutoff:
            raise ValueError('Input source unavailable before cutoff')
        read(source)
    rows = universe['rows']
    if not isinstance(rows,list) or not rows:
        raise ValueError('Nonempty immutable forecast universe required')
    seen = set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('row_id'),str) or row['row_id'] in seen:
            raise ValueError('Invalid or duplicate inference row')
        seen.add(row['row_id'])
        if row['operational_night'] != night or registry.timestamp(row['cutoff_time']) != cutoff:
            raise ValueError('Universe cutoff/night mismatch')
        start = registry.timestamp(row['window_start_jst']).astimezone(JST)
        if night_for(start) != night or start <= now or start.minute%10 or start.second or start.microsecond:
            raise ValueError('Forecast windows must be prospective aligned ten-minute units')
        _coordinates(row)
    return value, rows, consumed


def issue_prediction(root, snapshot_path, snapshot_sha256, night, version=None, *, clock=None):
    validate_night(night)
    if registry._sandbox(root) is None:
        raise ValueError(registry.AUTHORITY_BLOCKER)
    clock = clock or (lambda:datetime.now(JST))
    with registry.registry_lock(root):
        initial = clock()
        if initial.tzinfo is None:
            raise ValueError('Issuer clock must be timezone aware')
        selected = registry._champion_locked(root, initial.isoformat())
        if selected is None:
            raise ValueError('No committed sandbox Champion at actual issuance time')
        model = registry.verify_model(selected['model'])
        value, rows, consumed = _snapshot(root.root, Path(snapshot_path), snapshot_sha256, night, initial)
        if registry.timestamp(model['training_cutoff']) >= registry.timestamp(value['cutoff_time']):
            raise ValueError('Model training must precede forecast information cutoff')
        outputs = predict_model(model, rows)
        canonical_bytes(outputs)
        payload = {'cutoff_time': value['cutoff_time'], 'grid_predictions':outputs,
                   'targets_100m_10min':[], 'formal_100m_10min_status':'NOT_PRODUCED',
                   'produced_outputs':model['produced_outputs'], 'training_cutoff':model['training_cutoff'],
                   'data_sha256':snapshot_sha256, 'feature_schema_sha256':model['feature_schema_sha256'],
                   'input_source_availability':{'universe':value['universe'], 'sources':value['source_manifest']}}
        lineage = {'qualification':registry.SCOPE, 'prediction_class':'SANDBOX', 'generated_by':'registered_inference',
                   'champion_id':model['model_id'], 'registry_event_id':selected['event']['event_sha256'],
                   'model_sha256':model['model_sha256'], 'inference_sha256':digest(outputs),
                   'inference_adapter':model['implementation_version']}
        def recheck(now):
            if now.tzinfo is None or now < initial:
                raise ValueError('Issuer clock reversed or lost timezone')
            if any(registry.timestamp(row['window_start_jst']) <= now for row in rows):
                raise ValueError('Forecast expired before publication')
            for path, expected in consumed.items():
                if not path.is_file() or file_hash(path) != expected:
                    raise ValueError('Inference input changed before publication')
            current = registry._champion_locked(root, now.isoformat())
            if current is None or current['event']['event_sha256'] != selected['event']['event_sha256']:
                raise ValueError('Champion changed during issuance')
            registry.verify_model(model)
        return _freeze_payload(root.root,payload,night,version,clock=clock,namespace='sandbox/predictions',
                               before_publish=recheck,lineage=lineage)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--snapshot-sha256',required=True)
    parser.add_argument('--night',required=True)
    parser.add_argument('--version')
    args=parser.parse_args()
    try:
        print(issue_prediction(args.root,args.snapshot,args.snapshot_sha256,args.night,args.version))
        return 0
    except ValueError as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
