"""Bounded pure CompositeModel v2 execution, never an issuer or trusted context.

Model identity hashes every field except model_id/model_sha256. Referenced state
and config artifacts are supplied as SHA-keyed JSON in the inference bundle.
Their content and declared availability are checked, not authenticated. No file
reader, writer, confirmation labels, arbitrary callbacks or import strings exist.
"""
import output_adapters as adapters

MAX_COMPONENTS = 16
MAX_BINDINGS = 32
MODEL_FIELDS = {'schema_version','kind','recipe_id','protocol_sha256','policy_sha256',
    'training_cutoff','code_manifest','components','output_bindings','mandatory_capabilities',
    'model_id','model_sha256'}
COMPONENT_FIELDS = {'component_id','adapter_id','adapter_version','role','state_sha256',
    'config_sha256','input_schema_sha256','output_schema_sha256','dependencies'}
BUNDLE_FIELDS = {'schema_version','operational_night','cutoff_time','forecast_end','artifacts',
                 'artifact_available_at','inputs','input_available_at'}


def _blocked_port(status, reason):
    return dict(schema_version='habu-adapter-output-v1',execution_status=status,
        validity_status='NOT_VALIDATED',missing_requirements=[reason],payload=None,payload_sha256=None)


def _failure(status, reason):
    result=dict(schema_version='habu-composite-prediction-v1',status=status,
        missing_requirements=[reason],component_receipts=[],outputs={},produced_outputs=[],
        code_identity='SUPPLIED_CLOSURE_NOT_ATTESTED',**adapters._flags())
    result['prediction_sha256']=adapters._digest(result)
    return result


def _reference(value):
    adapters._fields(value,{'component_id','output'})
    adapters._name(value['component_id']);adapters._name(value['output'])


def _validated(model, bundle, budget):
    adapters._fields(model,MODEL_FIELDS);adapters._fields(bundle,BUNDLE_FIELDS)
    if model['schema_version']!='2.0' or model['kind']!='registered_composite':
        adapters._fail('COMPOSITE_V2_REQUIRED')
    if bundle['schema_version']!='habu-composite-inference-input-v1':
        adapters._fail('INFERENCE_BUNDLE_VERSION')
    if type(bundle['operational_night']) is not str:
        adapters._fail('EXPLICIT_NIGHT_REQUIRED')
    adapters._time(bundle['forecast_end'])
    adapters._name(model['recipe_id'])
    for field in ('protocol_sha256','policy_sha256','model_id','model_sha256'):
        adapters._hash(model[field])
    body={k:v for k,v in model.items() if k not in ('model_id','model_sha256')}
    if model['model_id']!=model['model_sha256'] or model['model_sha256']!=adapters._digest(body,budget):
        adapters._fail('COMPOSITE_IDENTITY')
    cutoff,end,night=adapters._context(bundle['cutoff_time'],bundle['operational_night'],bundle['forecast_end'])
    train=adapters._time(model['training_cutoff'])
    if train>=cutoff:
        adapters._fail('TRAINING_NOT_BEFORE_CUTOFF')
    manifest=model['code_manifest']
    adapters._fields(manifest,adapters.required_code_paths())
    for sha in manifest.values():adapters._hash(sha)
    components=model['components'];bindings=model['output_bindings'];mandatory=model['mandatory_capabilities']
    if type(components) is not list or not 1<=len(components)<=MAX_COMPONENTS:
        adapters._fail('COMPONENT_CAPACITY')
    if type(bindings) is not dict or not 1<=len(bindings)<=MAX_BINDINGS:
        adapters._fail('OUTPUT_BINDING_CAPACITY')
    if type(mandatory) is not list or len(mandatory)>MAX_BINDINGS:
        adapters._fail('MANDATORY_CAPACITY')
    for name in mandatory:adapters._name(name)
    if len(set(mandatory))!=len(mandatory):adapters._fail('DUPLICATE_MANDATORY')
    by_id, contracts = {}, {}
    required_artifacts=set()
    for component in components:
        budget.check();adapters._fields(component,COMPONENT_FIELDS)
        identifier=adapters._name(component['component_id'])
        if identifier in by_id:adapters._fail('DUPLICATE_COMPONENT')
        adapters._name(component['adapter_id']);adapters._name(component['role'])
        if type(component['adapter_version']) is not str or component['adapter_version']!='1':
            adapters._fail('ADAPTER_VERSION')
        for field in ('state_sha256','config_sha256','input_schema_sha256','output_schema_sha256'):
            adapters._hash(component[field])
        required_artifacts.update((component['state_sha256'],component['config_sha256']))
        dependencies=component['dependencies']
        if type(dependencies) is not dict or len(dependencies)>MAX_COMPONENTS:
            adapters._fail('DEPENDENCY_FIELDS')
        for slot,ref in dependencies.items():adapters._name(slot);_reference(ref)
        contract=adapters.adapter_contract(component['adapter_id'])
        if contract is not None:
            if (component['input_schema_sha256']!=contract['input_schema_sha256'] or
                    component['output_schema_sha256']!=contract['output_schema_sha256']):
                adapters._fail('ADAPTER_SCHEMA_MISMATCH')
            if set(dependencies)-set(contract['input_schema']['allowed_dependency_slots']):
                adapters._fail('UNSUPPORTED_DEPENDENCY_SLOT')
        contracts[identifier]=contract;by_id[identifier]=component
    for component in components:
        for slot,ref in component['dependencies'].items():
            producer=ref['component_id']
            if producer not in by_id:adapters._fail('MISSING_DEPENDENCY_COMPONENT')
            contract=contracts[producer]
            if contract is not None and ref['output'] not in contract['output_schema']:
                adapters._fail('MISSING_DEPENDENCY_PORT')
            # Only a native HBA unit probability stream can feed the current
            # candidate selector. No implicit unit/semantics conversions.
            if contracts[component['component_id']] is not None and contract is not None:
                if (slot!='unit_predictions' or ref['output']!='unit_predictions' or
                    by_id[producer]['adapter_id'] not in ('hba1_unit_v1','hba2_unit_v1')):
                    adapters._fail('DEPENDENCY_SEMANTICS')
    order=[];remaining=set(by_id)
    while remaining:
        budget.check()
        ready=sorted(identifier for identifier in remaining if all(
            ref['component_id'] in order for ref in by_id[identifier]['dependencies'].values()))
        if not ready:adapters._fail('DEPENDENCY_CYCLE')
        order.extend(ready);remaining.difference_update(ready)
    writers=set()
    for capability,ref in bindings.items():
        adapters._name(capability);_reference(ref)
        if ref['component_id'] not in by_id:adapters._fail('UNKNOWN_OUTPUT_COMPONENT')
        # Public capability names are fixed ports, not caller aliases that
        # might rename a scenario as forecast or a proxy as biological activity.
        if capability!=ref['output']:adapters._fail('OUTPUT_RENAMING_FORBIDDEN')
        writer=(ref['component_id'],ref['output'])
        if writer in writers:adapters._fail('DUPLICATE_OUTPUT_WRITER')
        writers.add(writer)
        contract=contracts[ref['component_id']]
        if contract is not None and ref['output'] not in contract['output_schema']:
            adapters._fail('UNREGISTERED_OUTPUT_CAPABILITY')
    for field in ('artifacts','artifact_available_at','inputs','input_available_at'):
        if type(bundle[field]) is not dict:adapters._fail('BUNDLE_OBJECT_REQUIRED')
    artifacts=bundle['artifacts'];inputs=bundle['inputs']
    if set(artifacts)-required_artifacts or set(inputs)-set(by_id):
        adapters._fail('UNCONSUMED_BUNDLE_INPUT')
    if set(bundle['artifact_available_at'])!=set(artifacts) or set(bundle['input_available_at'])!=set(inputs):
        adapters._fail('AVAILABILITY_COVERAGE')
    for sha,artifact in artifacts.items():
        budget.check();adapters._hash(sha)
        if sha!=adapters._digest(artifact,budget):adapters._fail('ARTIFACT_HASH_MISMATCH')
        if adapters._time(bundle['artifact_available_at'][sha])>=cutoff:
            adapters._fail('ARTIFACT_NOT_EX_ANTE')
    for identifier,raw in inputs.items():
        budget.check()
        if type(raw) is not dict:adapters._fail('COMPONENT_INPUT_OBJECT')
        if adapters._time(bundle['input_available_at'][identifier])>=cutoff:
            adapters._fail('INPUT_NOT_EX_ANTE')
        if set(raw)&set(by_id[identifier]['dependencies']):
            adapters._fail('DEPENDENCY_INPUT_OVERRIDE')
        if 'cutoff_time' in raw and adapters._time(raw['cutoff_time'])!=cutoff:
            adapters._fail('COMPONENT_CUTOFF_MISMATCH')
        if 'forecast_end' in raw and adapters._time(raw['forecast_end'])!=end:
            adapters._fail('COMPONENT_HORIZON_MISMATCH')
        for field in ('universe_rows','forecast_rows','unit_predictions'):
            if field in raw:
                adapters._window_rows(raw[field],bundle['cutoff_time'],bundle['forecast_end'],
                    legacy=(field=='universe_rows'),budget=budget)
    # The composite cutoff is the latest actual component-state cutoff. Never
    # let a caller backdate the declared composite training time.
    cutoffs=[];complete=True
    for component in components:
        if component['adapter_id'] in ('time_target_candidates_v1','independent_opportunity_detection_v1'):continue
        sha=component['state_sha256']
        if sha not in artifacts:
            complete=False;continue
        state=artifacts[sha]
        if type(state) is not dict:adapters._fail('STATE_OBJECT_REQUIRED')
        if contracts[component['component_id']] is None:
            complete=False;continue
        field='training_cutoff' if component['adapter_id']=='legacy_spatial_v1' else 'fit_cutoff'
        t=adapters._time(state[field]);cutoffs.append(t)
        if t>adapters._time(bundle['artifact_available_at'][sha]):adapters._fail('STATE_AVAILABLE_BEFORE_FIT')
    if complete and cutoffs and max(cutoffs)!=train:
        adapters._fail('COMPOSITE_TRAINING_CUTOFF')
    return by_id,contracts,order


def _predict(model,bundle,budget):
    by_id,contracts,order=_validated(model,bundle,budget)
    executed,receipts={},[]
    for identifier in order:
        budget.check();component=by_id[identifier];dependencies={};inputs=dict(bundle['inputs'].get(identifier,{}))
        state_sha,config_sha=component['state_sha256'],component['config_sha256']
        missing=identifier not in bundle['inputs'] or state_sha not in bundle['artifacts'] or config_sha not in bundle['artifacts']
        dependency_blocked=False
        for slot,ref in component['dependencies'].items():
            previous=executed[ref['component_id']]
            if previous['status']!='EXECUTED' or ref['output'] not in previous['outputs']:
                dependency_blocked=True;continue
            port=previous['outputs'][ref['output']]
            inputs[slot]=port['payload']
            dependencies[slot]=dict(component_id=ref['component_id'],output=ref['output'],
                payload_sha256=port['payload_sha256'],execution_sha256=previous['execution_sha256'])
        if contracts[identifier] is None:
            result=adapters._blocked('IMPLEMENTATION_BLOCKED','ADAPTER_NOT_IMPLEMENTED')
        elif missing or dependency_blocked:
            result=adapters._blocked('DATA_BLOCKED','DEPENDENCY_NOT_EXECUTED' if dependency_blocked else 'ARTIFACT_OR_INPUT_MISSING')
        else:
            if component['adapter_id']=='independent_opportunity_detection_v1':
                config=bundle['artifacts'][config_sha]
                if adapters._time(config['protocol']['assessment_as_of'])>adapters._time(bundle['cutoff_time']):
                    adapters._fail('DETECTION_ASSESSMENT_AFTER_COMPOSITE_CUTOFF')
            result=adapters._execute(component['adapter_id'],component['adapter_version'],
                bundle['artifacts'][state_sha],inputs,bundle['artifacts'][config_sha],budget)
        if result['status']=='FAIL':adapters._fail('COMPONENT_INVALID')
        if component['adapter_id'] in ('gamma_poisson_planned_count_v1','gamma_poisson_planned_units_v1'):
            native=result['native_payload']
            if component['adapter_id']=='gamma_poisson_planned_units_v1' and type(native) is dict:
                native=native['aggregate_prediction']
            if type(native) is dict and 'cutoff_time' in native:
                if (adapters._time(native['cutoff_time'])!=adapters._time(bundle['cutoff_time']) or
                        native['operational_night']!=bundle['operational_night'] or
                        adapters._time(native['forecast_window']['end'])!=adapters._time(bundle['forecast_end'])):
                    adapters._fail('PLANNED_COUNT_COMPOSITE_SCOPE_MISMATCH')
        executed[identifier]=result
        receipts.append(dict(component_id=identifier,adapter_id=component['adapter_id'],adapter_version=component['adapter_version'],
            status=result['status'],state_sha256=state_sha,config_sha256=config_sha,
            input_sha256=adapters._digest(inputs,budget),dependencies=dependencies,
            execution_sha256=result['execution_sha256'],execution=result))
    outputs={}
    for capability,ref in model['output_bindings'].items():
        result=executed[ref['component_id']]
        if result['status'] in ('EXECUTED','PARTIAL') and ref['output'] in result['outputs']:
            outputs[capability]=result['outputs'][ref['output']]
        else:
            status='NOT_PRODUCED' if result['status']=='PARTIAL' else result['status']
            outputs[capability]=_blocked_port(status,result['missing_requirements'][0])
    for capability in model['mandatory_capabilities']:
        if capability not in outputs:outputs[capability]=_blocked_port('IMPLEMENTATION_BLOCKED','CAPABILITY_NOT_BOUND')
    produced=sorted(name for name,port in outputs.items() if port['execution_status'] in ('EXECUTED','PARTIAL'))
    missing=sorted(name for name in model['mandatory_capabilities'] if outputs[name]['execution_status']!='EXECUTED')
    result=dict(schema_version='habu-composite-prediction-v1',status='BLOCKED' if missing else 'EXECUTED',
        composite_sha256=model['model_sha256'],input_bundle_sha256=adapters._digest(bundle,budget),
        operational_night=bundle['operational_night'],cutoff_time=bundle['cutoff_time'],forecast_end=bundle['forecast_end'],
        component_receipts=receipts,outputs=outputs,produced_outputs=produced,missing_requirements=missing,
        code_identity='SUPPLIED_CLOSURE_NOT_ATTESTED',code_manifest_sha256=adapters._digest(model['code_manifest'],budget),
        **adapters._flags())
    result['prediction_sha256']=adapters._digest(result,budget);budget.check()
    return result


def predict_composite(model, inference_bundle, *, budget_seconds=30):
    """Execute one immutable recipe with one deadline; no fitting or selection."""
    try:
        budget=adapters._Budget(budget_seconds)
        model,bundle=adapters._owned([model,inference_bundle],budget)
        return _predict(model,bundle,budget)
    except adapters._Stop as error:
        return _failure(error.status,error.code)
    except TimeoutError:
        return _failure('BUDGET_BLOCKED','NATIVE_DEADLINE_EXCEEDED')
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError,UnicodeError):
        return _failure('FAIL','NATIVE_OR_SCHEMA_INVALID')
