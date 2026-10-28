"""Explicit development dispatch through both strict gates, without reveal.

Only the fixed config request enables this path. Complete diagnostic candidate
sets receive a content-addressed REPLAY after source rechecks; no confirmation
reader, selection metric, official issuer or production activation is provided.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid

import g0_forecast_contract as g0
import g0_training_source_contract as training
from master_contracts import SCHEMA_VERSION, canonical_bytes, digest, stage, validate_night
from master_inventory import local_path, has_research_request, RESEARCH_REQUEST_PATH
import prospective_inputs as pi
import research_model_adapter as models

VERSION = 'habu-research-model-request-v1'
STAGE1_VERSION = 'habu-research-model-request-v2'
CONFIG_VERSION = 'habu-research-model-request-v3'
CONFIG_STAGE1_VERSION = 'habu-research-model-request-v4'
CALIBRATION_VERSION = 'habu-research-model-request-v5'
REQUEST_PATH = RESEARCH_REQUEST_PATH
NAMES = ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')
FIELDS = {'schema_version', 'mode', 'operational_night', 'fit_cutoff', 'forecast_as_of',
          'forecast_cutoff', 'feature_definition_sha256', 'training_manifest', 'forecast_manifest', 'exposed_nights'}
MAX_REPLAY_BYTES = 64 * 1024**2
POSIX_CLEANUP_SUPPORTED = (os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY') and
    all(function in os.supports_dir_fd for function in
        (os.open, os.stat, os.unlink, os.rename, os.mkdir, os.rmdir, os.link)))


def _request(root, reader):
    path = local_path(root, REQUEST_PATH)
    raw = pi._bounded_bytes(path, pi._LocalByteBudget(reader.context, g0.MAX_SMALL_BYTES), reader.context.check)
    ref = dict(path=REQUEST_PATH, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    value = reader.read(ref, small=True)
    if type(value) is not dict:
        raise ValueError('Exact development-only research request fields required')
    version = value.get('schema_version')
    fields = (FIELDS if version == VERSION else FIELDS | {'stage1_manifest'} if version == STAGE1_VERSION
              else FIELDS | {'stage1_manifest', 'candidate_config_manifest'}
              if version in (CONFIG_VERSION, CONFIG_STAGE1_VERSION) else
              FIELDS | {'stage1_manifest', 'candidate_config_manifest', 'calibration_manifest'}
              if version == CALIBRATION_VERSION else set())
    if not fields or set(value) != fields or value['mode'] != 'DEVELOPMENT_ONLY':
        raise ValueError('Exact development-only research request fields required')
    exposed = value['exposed_nights']
    if type(exposed) is not list or any(type(night) is not str for night in exposed):
        raise ValueError('Exposed nights must be a JSON array of nights')
    for night in exposed:
        reader.context.check()
        validate_night(night)
    if len(set(exposed)) != len(exposed):
        raise ValueError('Exposed nights must be unique')
    training._reference(value['training_manifest'], 'manifest')
    g0._input_ref(value['forecast_manifest'])
    if version == STAGE1_VERSION:
        from evaluation.stage1_source_adapter import input_ref
        input_ref(value['stage1_manifest'])
    if version in (CONFIG_VERSION, CONFIG_STAGE1_VERSION, CALIBRATION_VERSION):
        from research_candidate_config_source import input_ref, RESERVED
        input_ref(value['candidate_config_manifest'])
        if value['stage1_manifest'] is not None:
            from evaluation.stage1_source_adapter import input_ref as stage1_ref
            stage1_ref(value['stage1_manifest'])
        refs = [value['training_manifest'], value['forecast_manifest'], value['candidate_config_manifest']]
        if value['stage1_manifest'] is not None:
            refs.append(value['stage1_manifest'])
        for item in refs:
            if any(part.casefold() in RESERVED for part in item['path'].split('/')):
                raise ValueError('Reserved v3 source namespace')
    if version == CALIBRATION_VERSION:
        from evaluation.feature_candidate_calibration_source import input_ref
        if value['stage1_manifest'] is not None:
            raise ValueError('Calibration v5 cannot co-dispatch Stage1')
        input_ref(value['calibration_manifest'])
    # Transport accepts arbitrary local refs. This caller must exclude reveal
    # namespaces before either gate opens any requested payload/code source.
    for item in (value['training_manifest'], value['forecast_manifest']):
        if any(part.casefold() in {'sealed', 'confirmation'} for part in item['path'].split('/')):
            raise ValueError('Sealed confirmation reference forbidden')
    return value, ref


def _preflight_forecast(reader, ref, *, reserved=frozenset({'sealed', 'confirmation'})):
    """Exclude reveal paths even in nested source/code refs before the loader."""
    manifest = reader.read(ref, small=True)
    pending = [manifest]
    while pending:
        reader.context.check()
        item = pending.pop()
        if type(item) is dict:
            path = item.get('path')
            if type(path) is str and any(part.casefold() in reserved for part in path.split('/')):
                raise ValueError('Sealed confirmation reference forbidden')
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def _v4_stage1_admission(config, forecast, prepared, expected, definitions, context):
    """Admit native bindings before manifest preflight, under the same budget."""
    from evaluation import stage1_source_adapter as source
    from evaluation import full_ledger_stage1 as pure
    context.check()
    try:
        source._configured_prepared(config, forecast, prepared, expected, definitions, context.check)
    except (pure.Stage1CapacityBlocked, models.ResearchCapacityBlocked,
            models.ResearchInputCapacity, models._hba1.HBA1CapacityBlocked) as exc:
        raise pi.InputCapacityError(str(exc)) from exc
    except pure.Stage1BudgetBlocked as exc:
        raise TimeoutError(str(exc)) from exc
    context.check()


def _publish(root, night, content, context, *, _ownership=None):
    """A single complete immutable artifact; never overwrite an existing replay."""
    content_sha = digest(content)
    relative = f'predictions/replay/{night}/research/{content_sha}.json'
    path = local_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.research-replay-', dir=path.parent)
    temporary_identity = os.fstat(fd) if _ownership is not None else None
    sha, count = hashlib.sha256(), 0
    try:
        with os.fdopen(fd, 'wb') as stream:
            for text in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).iterencode(content):
                context.check()
                raw = text.encode('utf-8')
                count += len(raw)
                if count > MAX_REPLAY_BYTES:
                    raise pi.InputCapacityError('CAPACITY_BLOCKED: complete REPLAY bytes')
                stream.write(raw)
                sha.update(raw)
            stream.write(b'\n')
            sha.update(b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        context.check()
        local_path(root, relative)
        if _ownership is not None:
            owned = (relative, temporary_identity.st_dev, temporary_identity.st_ino)
            # Register the possible native link before the syscall: an
            # interruption can occur after creation but before Python returns.
            _ownership.append(owned)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _ownership is not None:
                _ownership.remove(owned)  # Reuse is never owned by this call.
            existing = g0.G0ArtifactReader(root, context)
            existing.read(dict(path=relative, sha256=sha.hexdigest(), size_bytes=count + 1), parse=False)
        else:
            if _ownership is not None:
                # Bind the actual newly-linked bytes too, under the same
                # guarded transport and cumulative output-read budget.
                verified = g0.G0ArtifactReader(root, context)
                verified.read(dict(path=relative, sha256=sha.hexdigest(), size_bytes=count + 1), parse=False)
        context.check()
        return dict(path=relative, sha256=sha.hexdigest(), content_sha256=content_sha,
                    trust='DEVELOPMENT_REPLAY_NOT_OFFICIAL_OR_TRUSTED_SEAL')
    finally:
        if _ownership is None:
            os.unlink(temporary)
        else:
            temporary_relative = Path(temporary).relative_to(root).as_posix()
            residual = _cleanup_owned(root, [(temporary_relative, temporary_identity.st_dev, temporary_identity.st_ino)])
            if residual:
                raise ValueError('Untrusted residual temporary REPLAY; safe ownership could not be re-established: ' + ', '.join(residual))


def _unlink_owned_windows(target, device, inode):
    """Delete the verified open file, never resolve its pathname again to delete."""
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    disposition = kernel.SetFileInformationByHandle
    disposition.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    disposition.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes, close.restype = (wintypes.HANDLE,), wintypes.BOOL
    name = str(target.absolute())
    name = '\\\\?\\UNC\\' + name[2:] if name.startswith('\\\\') else '\\\\?\\' + name
    # DELETE | FILE_READ_ATTRIBUTES; share read/write/delete, open final
    # reparse point itself. Ancestor swaps can only change which handle is
    # obtained: its identity must still match before any deletion is requested.
    handle = create(name, 0x10000 | 0x80, 1 | 2 | 4, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    try:
        identity = os.fstat(descriptor)
        if (not stat.S_ISREG(identity.st_mode) or
                (identity.st_dev, identity.st_ino) != (device, inode)):
            raise ValueError('Untrusted cleanup handle identity')
        # FILE_DISPOSITION_INFO.DeleteFile is a one-byte BOOLEAN. The native
        # operation applies to this verified handle even after ancestor rename.
        delete = ctypes.c_ubyte(1)
        if not disposition(handle, 4, ctypes.byref(delete), ctypes.sizeof(delete)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        os.close(descriptor)  # Owns and closes the original Win32 handle.


def _unlink_owned_posix(target, device, inode):
    """Pin ancestors and atomically claim a leaf before checking/deleting it."""
    if not POSIX_CLEANUP_SUPPORTED:
        raise ValueError('Handle-relative cleanup capability unavailable')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    target = target.absolute()
    descriptor = os.open(target.anchor, flags)
    quarantine = None
    quarantine_fd = None
    quarantine_created = False
    claimed = False
    try:
        for component in target.parts[1:-1]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        quarantine = '.research-cleanup-' + uuid.uuid4().hex
        os.mkdir(quarantine, mode=0o700, dir_fd=descriptor)
        quarantine_created = True
        quarantine_fd = os.open(quarantine, flags, dir_fd=descriptor)
        claimed = True
        os.rename(target.name, 'claimed', src_dir_fd=descriptor, dst_dir_fd=quarantine_fd)
        identity = os.stat('claimed', dir_fd=quarantine_fd, follow_symlinks=False)
        if not stat.S_ISREG(identity.st_mode) or (identity.st_dev, identity.st_ino) != (device, inode):
            # A different public leaf won the race before atomic claim. Restore
            # its public name only if absent; keep its recovery link intact.
            try:
                os.link('claimed', target.name, src_dir_fd=quarantine_fd,
                        dst_dir_fd=descriptor, follow_symlinks=False)
            except OSError:
                pass
            return [target.parent / quarantine / 'claimed']
        os.unlink('claimed', dir_fd=quarantine_fd)
        claimed = False
        return []
    except (ValueError, OSError) as exc:
        if claimed:
            try:
                os.stat('claimed', dir_fd=quarantine_fd, follow_symlinks=False)
            except FileNotFoundError:
                claimed = False
                raise exc
            except OSError:
                pass  # Retain the potential claim and report recovery path.
            return [target.parent / quarantine / 'claimed']
        raise
    finally:
        try:
            if quarantine_fd is not None:
                os.close(quarantine_fd)
            if quarantine_created and not claimed:
                os.rmdir(quarantine, dir_fd=descriptor)
        finally:
            os.close(descriptor)


def _cleanup_owned(root, ownership):
    """Only v2-owned links; unsupported safe deletion reports a residual."""
    residual = []
    for relative, device, inode in ownership:
        try:
            target = local_path(root, relative)
            if os.name == 'nt':
                _unlink_owned_windows(target, device, inode)
            else:
                recovery = _unlink_owned_posix(target, device, inode)
                if recovery:
                    residual.extend(path.relative_to(root).as_posix() for path in recovery)
                    residual.append(relative)
                    continue
            # Deletion itself was handle-relative. A changed pathname is still
            # reported honestly, without following it for another deletion.
            if os.path.lexists(local_path(root, relative)):
                residual.append(relative)
        except FileNotFoundError:
            pass
        except (ValueError, OSError):
            residual.append(relative)
    return residual


def evaluate_research_request(root, night, budget_seconds=300, *, _read_context=None):
    validate_night(night)
    root = Path(root).absolute()
    result = dict(schema_version=SCHEMA_VERSION, stages=[], candidates=[], folds=[], replay=[],
        implementation_blockers=['Independent confirmation selection/consumption lock and trusted runner',
            'Feature-aware retraining ablation, count/detection/activity/route/rerouting executors'],
        data_blockers=[], decision=dict(decision='NEED_MORE_DATA', reasons=[]),
        scientific_fit_authorized=False, production_activation_authorized=False,
        official_issuance_authorized=False, confirmation_labels_used=False)
    status, kind = 'BLOCKED', 'DATA_BLOCKED'
    reason = 'Required qualified TRAIN_ONLY evidence and complete strict forecast inputs'
    prepared = None
    context = None
    ownership = []
    stage1 = None
    config_source = None
    config_loader = None
    stage1_dispatch = None
    pending_content = None
    calibration = None
    calibration_loader = None
    calibration_admission = None
    try:
        if budget_seconds == 0:
            raise TimeoutError('Parent cumulative budget exhausted')
        context = _read_context or pi.ProspectiveReadContext(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
        if not isinstance(context, pi.ProspectiveReadContext):
            raise ValueError('Shared prospective read context required')
        context.restrict(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
        reader = g0.G0ArtifactReader(root, context)
        request, request_ref = _request(root, reader)
        if request['operational_night'] != night:
            raise ValueError('Research request night mismatch')
        cutoff, as_of, fit = (pi._time(request[key]) for key in ('forecast_cutoff', 'forecast_as_of', 'fit_cutoff'))
        if pi._night(cutoff) != night or fit >= cutoff or as_of < cutoff:
            raise ValueError('Research request fit/forecast boundaries inconsistent')
        expected = request['feature_definition_sha256']
        if type(expected) is not str or not pi.SHA256.fullmatch(expected):
            raise ValueError('Strict registered feature-definition digest required')
        if request['schema_version'] in (CONFIG_VERSION, CONFIG_STAGE1_VERSION, CALIBRATION_VERSION):
            import research_candidate_config_source as config_loader
            config_source = config_loader.load_research_candidate_config(root, request['candidate_config_manifest'],
                heldout_night=night, fit_cutoff=request['fit_cutoff'], forecast_cutoff=request['forecast_cutoff'],
                expected_feature_definition_sha256=expected, context=context)
            _preflight_forecast(reader, request['training_manifest'], reserved=config_loader.RESERVED)
            _preflight_forecast(reader, request['forecast_manifest'], reserved=config_loader.RESERVED)
        if request['schema_version'] == CALIBRATION_VERSION:
            from evaluation import feature_candidate_calibration_source as calibration_loader
            if 'HB-A1' not in config_source['config']['candidate_ids']:
                raise ValueError('Calibration v5 requires configured HB-A1')
            calibration_admission = calibration_loader.preflight(root, request['calibration_manifest'], context=context)
        selected = training.select_g0_training_rows(root, request['training_manifest'], night,
            request['fit_cutoff'], request['forecast_cutoff'], expected_feature_definition_sha256=expected,
            exposed_nights=request['exposed_nights'], budget_seconds=context.remaining_seconds, _read_context=context)
        _preflight_forecast(reader, request['forecast_manifest'])
        forecast = g0.load_g0_forecast_rows(root, request['forecast_manifest'], night, as_of,
            expected_feature_definition_sha256=expected, budget_seconds=context.remaining_seconds, _read_context=context)
        if pi._time(forecast['receipt']['cutoff_time']) != cutoff:
            raise ValueError('Request cutoff differs from strict forecast cutoff')
        if config_source is not None:
            if any(receipt['feature_definition_sha256'] != expected for receipt in (selected['receipt'], forecast['receipt'])):
                raise ValueError('Configured/selected training/forecast strict definitions differ')
            remaining = context.remaining_seconds
            if remaining <= 0:
                raise TimeoutError('Parent cumulative budget exhausted before configured preparation')
            context.check()
            prepare = (calibration_loader.prepare if calibration_loader is not None else models.prepare_research_candidates_v2)
            prepare_options = ({'context': context} if calibration_loader is not None else
                               {'budget_seconds': remaining, 'check': context.check})
            prepared = prepare(selected['selection'], forecast['rows'],
                candidate_config=config_source['config'], expected_config_sha256=config_source['receipt']['config_sha256'],
                feature_definition_sha256=expected, cutoff_time=request['forecast_cutoff'],
                joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
                **prepare_options)
            config_loader.recheck_research_candidate_config(root, config_source['receipt'], context=context)
            stage1_dispatch = dict(status='NOT_REQUESTED' if request['stage1_manifest'] is None else 'NOT_RUN_DATA_BLOCKED',
                registry='habu-stage1-scores-v1', trusted_pre_reveal_authorized=False,
                trusted_campaign_authorized=False, source_issuer_authenticated=False,
                loaded_bytecode_authenticated=False, confirmation_authorized=False)
            if request['schema_version'] == CONFIG_STAGE1_VERSION:
                stage1_dispatch.update(registry='habu-stage1-scores-v2',
                    source_contract_version='habu-stage1-source-contract-v2',
                    candidate_config_sha256=config_source['receipt']['config_sha256'],
                    feature_definition_sha256=expected,
                    candidate_ids=list(config_source['config']['candidate_ids']))
            elif request['stage1_manifest'] is not None and config_source['config']['candidate_ids'] != list(models.CANDIDATES):
                stage1_dispatch.update(status='IMPLEMENTATION_BLOCKED',
                    reason='Stage1 v1 registry supports only exact ordered uniform/HB-A0/HB-B1; configured registry integration unavailable')
        else:
            prepared = models.prepare_research_candidates(selected['selection'], forecast['rows'],
                cutoff_time=request['forecast_cutoff'],
                joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
                budget_seconds=context.remaining_seconds)
        context.check()
        if request['schema_version'] == STAGE1_VERSION and prepared['status'] != 'NEED_MORE_DATA':
            from evaluation.stage1_source_adapter import evaluate_stage1_sources
            stage1 = evaluate_stage1_sources(root, request['stage1_manifest'], forecast, prepared, context=context)
        if config_source is not None and prepared['status'] != 'NEED_MORE_DATA' and request['stage1_manifest'] is not None:
            if request['schema_version'] == CONFIG_STAGE1_VERSION:
                from evaluation.stage1_source_adapter import evaluate_stage1_sources_v2
                _v4_stage1_admission(config_source['config'], forecast, prepared,
                    config_source['receipt']['config_sha256'], expected, context)
                _preflight_forecast(reader, request['stage1_manifest'], reserved=config_loader.RESERVED)
                stage1 = evaluate_stage1_sources_v2(root, request['stage1_manifest'], forecast, prepared,
                    candidate_config=config_source['config'], expected_config_sha256=config_source['receipt']['config_sha256'],
                    feature_definition_sha256=expected, context=context)
                stage1_dispatch['status'] = stage1['status']
            elif stage1_dispatch['status'] != 'IMPLEMENTATION_BLOCKED':
                from evaluation.stage1_source_adapter import evaluate_stage1_sources
                _preflight_forecast(reader, request['stage1_manifest'], reserved=config_loader.RESERVED)
                stage1 = evaluate_stage1_sources(root, request['stage1_manifest'], forecast, prepared, context=context)
                stage1_dispatch['status'] = stage1['status']
            config_loader.recheck_research_candidate_config(root, config_source['receipt'], context=context)
        if calibration_loader is not None and prepared['status'] != 'NEED_MORE_DATA':
            calibration = calibration_loader.evaluate(root, calibration_admission, forecast, prepared, selected,
                config_source['config'], expected_config_sha256=config_source['receipt']['config_sha256'],
                feature_definition_sha256=expected, context=context)
        consumed = {}
        receipts = [selected['receipt'], forecast['receipt']]
        if config_source is not None:
            receipts.append(config_source['receipt'])
        if stage1 is not None:
            receipts.append(stage1['source_receipt'])
        if calibration is not None:
            receipts.append(calibration['source_receipt'])
        for receipt in receipts:
            for path, expected_sha in receipt['consumed_sha256'].items():
                context.check()
                if path in consumed and consumed[path] != expected_sha:
                    raise ValueError('Conflicting training/forecast source binding')
                consumed[path] = expected_sha
        # Recheck all earlier training and forecast sources after fitting; a
        # per-gate scan alone would miss mutations during later model calls.
        config_refs = ({ref['path']: ref for ref in config_source['receipt']['consumed_refs']}
                       if config_source is not None else {})
        if calibration is not None:
            config_refs.update({ref['path']: ref for ref in calibration['source_receipt']['consumed_refs']})
        for path, expected_sha in consumed.items():
            if path in config_refs:
                ref = config_refs[path]
            else:
                target = local_path(root, path)
                ref = dict(path=path, sha256=expected_sha, size_bytes=target.stat().st_size)
            reader.read(ref, parse=False)
        reader.rescan()
        context.check()
        result['evidence'] = dict(request_ref=request_ref, training=selected['receipt'], forecast=forecast['receipt'],
            consumed_inputs=dict(consumed, **{REQUEST_PATH: request_ref['sha256']}),
            source_authentication='NOT_ATTESTED', actual_read_bytes=context.bytes_read)
        if config_source is not None:
            result['evidence']['candidate_config_source'] = config_source['receipt']
            result['stage1_dispatch'] = stage1_dispatch
            result.update(selection_authorized=False, promotion_authorized=False,
                trusted_campaign_authorized=False, trusted_pre_reveal_authorized=False,
                loaded_bytecode_authenticated=False, source_issuer_authenticated=False,
                confirmation_authorized=False)
            result['implementation_blockers'] = [
                'Trusted cumulative campaign budget/candidate-set ledger and pre-reveal consumption lock',
                'Source issuer, loaded Python/native runtime and confirmation authentication',
                'Scientific model comparison, winner selection and production activation authority']
            if stage1_dispatch['status'] == 'IMPLEMENTATION_BLOCKED':
                result['implementation_blockers'].append(stage1_dispatch['reason'])
        if prepared['status'] == 'NEED_MORE_DATA':
            reason = 'DATA_BLOCKED: ' + '; '.join(prepared['blockers'])
        else:
            content = dict(schema_version=VERSION, scope='DEVELOPMENT_ONLY', request_ref=request_ref,
                training_receipt=selected['receipt'], forecast_receipt=forecast['receipt'], prepared=prepared,
                confirmation_labels_used=False, scientific_fit_authorized=False,
                official_issuance_authorized=False, production_activation_authorized=False)
            if stage1 is not None:
                content.update(schema_version=STAGE1_VERSION, stage1_diagnostic=stage1)
            if config_source is not None:
                content.update(schema_version=request['schema_version'], candidate_config_source=config_source['receipt'],
                    stage1_dispatch=stage1_dispatch,
                    parent_dispatch=dict(status=('CONFIG_SOURCE_STAGE1_V4_SOFTWARE_ONLY'
                        if request['schema_version'] == CONFIG_STAGE1_VERSION else 'CONFIG_SOURCE_V3_SOFTWARE_ONLY'),
                        source_authentication='NOT_ATTESTED',
                        trusted_campaign_authorized=False, trusted_pre_reveal_authorized=False,
                        loaded_bytecode_authenticated=False, confirmation_authorized=False))
            if calibration is not None:
                content['calibration'] = calibration
                content['parent_dispatch']['status'] = 'CALIBRATION_V5_SOFTWARE_ONLY'
            if request['schema_version'] in (STAGE1_VERSION, CONFIG_VERSION, CONFIG_STAGE1_VERSION, CALIBRATION_VERSION):
                # Build v2 stages and check the result before native publish.
                pending_content = content
                replay = None
            else:
                replay = _publish(root, night, content, context)
            context.check()
            result['replay'] = [replay] if replay is not None else []
            result['candidates'] = prepared['candidates']
            if stage1 is not None:
                result['stage1_diagnostic'] = stage1
            if calibration is not None:
                result['calibration'] = calibration
            status, kind = 'NOT_VALIDATED', None
            reason = 'Complete diagnostic candidates prepared; independent evaluation and promotion gates unmet'
            if stage1_dispatch is not None and stage1_dispatch['status'] == 'IMPLEMENTATION_BLOCKED':
                reason += '; IMPLEMENTATION_BLOCKED: configured Stage1 registry unavailable'
    except (TimeoutError, models.ResearchBudgetExhausted, pi.InputCapacityError, models.ResearchCapacityBlocked) as exc:
        status, kind, reason = 'BLOCKED', 'RUNTIME_BLOCKED', str(exc)
    except (FileNotFoundError, training.G0TrainingInputBlocked, g0.ForecastCapabilityError) as exc:
        status, kind, reason = 'BLOCKED', 'DATA_BLOCKED', str(exc)
        if calibration_loader is not None and isinstance(exc, calibration_loader.ObservationBlocked):
            result['calibration_observation_blockers'] = exc.details
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as exc:
        if ((config_loader is not None and isinstance(exc, config_loader.CandidateConfigSourceBlocked)) or
                (type(exc) is ValueError and str(exc) == 'Missing prospective input')):
            # Legacy prospective transport represents absent files as this
            # ValueError, rather than a FileNotFoundError. Preserve its API.
            status, kind, reason = 'BLOCKED', 'DATA_BLOCKED', str(exc)
        else:
            status, kind, reason = 'FAIL', None, f'INVALID_RESEARCH_EVIDENCE: {exc}'
            result['decision']['decision'] = 'REJECT_CANDIDATE'
    except BaseException as exc:
        if calibration_loader is not None and isinstance(exc, calibration_loader.CallerFailure):
            raise exc.origin
        raise
    if status != 'NOT_VALIDATED':
        result['candidates'], result['replay'] = [], []
        result.pop('stage1_diagnostic', None)
        result.pop('stage1_dispatch', None)
    result['data_blockers'] = [reason, 'Source authenticity and independent prospective confirmation remain unvalidated']
    result['decision']['reasons'] = [reason]
    for name in NAMES:
        item_status, item_kind = status, kind
        if status == 'NOT_VALIDATED':
            item_status = 'PASS' if name == 'candidate_generation' else 'BLOCKED' if name == 'candidate_validation' else 'NOT_VALIDATED'
            item_kind = 'DATA_BLOCKED' if name == 'candidate_validation' else None
            if (name == 'candidate_validation' and stage1_dispatch is not None and
                    stage1_dispatch['status'] == 'IMPLEMENTATION_BLOCKED'):
                item_kind = 'IMPLEMENTATION_BLOCKED'
        result['stages'].append(stage(name, item_status, reason, evidence=[r['path'] for r in result['replay']],
            metrics={'diagnostic_candidates': len(result['candidates'])}, blocker_kind=item_kind))
    if status != 'FAIL' and isinstance(context, pi.ProspectiveReadContext):
        try:
            context.check()
        except (TimeoutError, pi.InputCapacityError) as exc:
            result['candidates'], result['replay'] = [], []
            result.pop('stage1_diagnostic', None)
            result.pop('stage1_dispatch', None)
            result['decision'] = dict(decision='NEED_MORE_DATA', reasons=[str(exc)])
            result['data_blockers'].append(str(exc))
            result['stages'] = [stage(name, 'BLOCKED', str(exc), blocker_kind='RUNTIME_BLOCKED') for name in NAMES]
    if pending_content is not None and result['candidates']:
        try:
            context.check()
            if config_source is not None:
                reader.rescan()
                config_loader.recheck_research_candidate_config(root, config_source['receipt'], context=context)
            if calibration is not None:
                calibration_loader.recheck(calibration, prepared, context)
            replay = _publish(root, night, pending_content, context, _ownership=ownership)
            for item in result['stages']:
                context.check()
                item['evidence'] = [replay['path']]
            context.check()
            result['replay'] = [replay]
        except (TimeoutError, pi.InputCapacityError, ValueError, OSError) as exc:
            runtime = isinstance(exc, (TimeoutError, pi.InputCapacityError))
            result['candidates'], result['replay'] = [], []
            result.pop('stage1_diagnostic', None)
            result.pop('stage1_dispatch', None)
            result['decision'] = dict(decision='NEED_MORE_DATA' if runtime else 'REJECT_CANDIDATE', reasons=[str(exc)])
            result['data_blockers'].append(str(exc))
            result['stages'] = [stage(name, 'BLOCKED' if runtime else 'FAIL', str(exc),
                blocker_kind='RUNTIME_BLOCKED' if runtime else None) for name in NAMES]
    if 'evidence' in result and isinstance(context, pi.ProspectiveReadContext):
        result['evidence']['actual_read_bytes'] = context.bytes_read
    if config_source is not None and not any(item['status'] == 'FAIL' for item in result['stages']):
        try:
            context.check()  # v3 result construction and final ledger update.
        except (TimeoutError, pi.InputCapacityError) as exc:
            result['candidates'], result['replay'] = [], []
            result.pop('stage1_diagnostic', None)
            result.pop('stage1_dispatch', None)
            result['decision'] = dict(decision='NEED_MORE_DATA', reasons=[str(exc)])
            result['data_blockers'].append(str(exc))
            result['stages'] = [stage(name, 'BLOCKED', str(exc), blocker_kind='RUNTIME_BLOCKED') for name in NAMES]
    if ownership and not result['replay']:
        residual = _cleanup_owned(root, ownership)
        if residual:
            result['data_blockers'].append('Untrusted residual REPLAY; safe ownership could not be re-established: ' + ', '.join(residual))
    if calibration is not None and not result['replay']:
        result.pop('calibration', None)
    return result
