"""Fixed report-only Git persistence of unauthenticated job accounting."""
from master_contracts import canonical_bytes, digest
from development_handoff import (_fields, _hash, _report_tree, _read_report_blob,
    _report_json, _report_bytes, MAX_REPORT_FILES, MAX_REPORT_READ_BYTES)
from development_job_ledger import FLAGS, _validated

VERSION = 'habu-development-job-report-v1'


def _publication_records(ledger, source):
    ledger,_ = _validated(ledger)
    source = _hash(source,40)
    origin = ledger['origin']; job = origin['job_id']; night = origin['anchor_night']
    branch = 'pdca/development-'+job
    prefix = f'reports/pdca/{night}/bridge/development/{job}/'
    common = dict(schema_version=VERSION,job_id=job,root_command_id=origin['root_command_id'],
        anchor_night=night,root_report_source_commit=source,**FLAGS)
    zero = dict(ledger,events=[],tip_sha256=digest(origin))
    record = dict(common,kind='ORIGIN',origin=origin,proposal_sha256=digest(zero))
    origin_sha = digest(record)
    records = {prefix+'origin.json':_report_bytes(record)}
    for sequence,event in enumerate(ledger['events'],1):
        prior = dict(ledger,events=ledger['events'][:sequence],tip_sha256=event['event_sha256'])
        records[prefix+f"events/{sequence:04d}-{event['event_sha256']}.json"] = _report_bytes(
            dict(common,kind='EVENT',origin_record_sha256=origin_sha,proposal_sha256=digest(prior),event=event))
    records[prefix+'state.json'] = _report_bytes(dict(common,kind='STATE',
        origin_record_sha256=origin_sha,proposal_sha256=digest(ledger),proposal=ledger))
    if len(records)>MAX_REPORT_FILES or sum(map(len,records.values()))>MAX_REPORT_READ_BYTES:
        raise ValueError('CAPACITY_BLOCKED: development report record bytes/paths')
    return branch,prefix,records


def _view(transport, head, source, origin, budget):
    head,source = _hash(head,40),_hash(source,40)
    prefix = f"reports/pdca/{origin['anchor_night']}/bridge/development/{origin['job_id']}/"
    if _report_tree(transport,source,prefix):
        raise ValueError('Existing development job in report base cannot reset')
    transport.assert_report_tree(head,source)
    tree = _report_tree(transport,head,prefix)
    state_path = prefix+'state.json'
    if state_path not in tree:
        raise ValueError('Existing development branch lacks fixed job state')
    state = _report_json(_read_report_blob(transport,head,state_path,tree[state_path],budget))
    _fields(state,{'schema_version','kind','job_id','root_command_id','anchor_night',
        'root_report_source_commit','origin_record_sha256','proposal_sha256','proposal',*FLAGS})
    ledger,_ = _validated(state['proposal'])
    if canonical_bytes(ledger['origin']) != canonical_bytes(origin):
        raise ValueError('Development origin/job/anchor cannot change')
    _,_,expected = _publication_records(ledger,source)
    if set(tree)!=set(expected):
        raise ValueError('Development report path set changed')
    changed = [p.decode('utf-8') for p in transport.git('diff','--name-only','--no-renames',
        '-z',source,head,'--').split(b'\0') if p]
    if len(changed)!=len(set(changed)) or set(changed)!=set(expected):
        raise ValueError('Development report contains foreign source/job/report edits')
    for path,raw in expected.items():
        if _read_report_blob(transport,head,path,tree[path],budget)!=raw:
            raise ValueError('Development immutable/canonical record bytes changed')
    lines = transport.git('rev-list','--first-parent','--reverse','--parents',head,'^'+source).decode('ascii').splitlines()
    if len(lines)!=len(ledger['events'])+1:
        raise ValueError('Exactly bootstrap plus one commit per development event required')
    previous = source
    for index,line in enumerate(lines):
        words = line.split()
        if len(words)!=2 or words[1]!=previous:
            raise ValueError('Merged/divergent development report history')
        commit = _hash(words[0],40)
        prior = dict(ledger,events=ledger['events'][:index],
            tip_sha256=ledger['events'][index-1]['event_sha256'] if index else digest(origin))
        _,_,records = _publication_records(prior,source)
        snapshot = _report_tree(transport,commit,prefix)
        if set(snapshot)!=set(records):
            raise ValueError('Historical development report is not exact prefix')
        if _read_report_blob(transport,commit,state_path,snapshot[state_path],budget)!=records[state_path]:
            raise ValueError('Historical development state/accounting was rewritten')
        delta = transport.git('diff','--name-status','--no-renames','-z',previous,commit,'--').split(b'\0')
        if delta and delta[-1]==b'': delta.pop()
        if len(delta)%2:
            raise ValueError('Malformed development commit delta')
        changes = {delta[i+1].decode('utf-8'):delta[i].decode('ascii') for i in range(0,len(delta),2)}
        if index:
            event = ledger['events'][index-1]
            expected_changes = {state_path:'M',prefix+f"events/{index:04d}-{event['event_sha256']}.json":'A'}
        else:
            expected_changes = {state_path:'A',prefix+'origin.json':'A'}
        if changes!=expected_changes:
            raise ValueError('Development commit rewrites history or unrelated paths')
        previous = commit
    return ledger


def _prefix(proposed, latest):
    return (canonical_bytes(proposed['origin'])==canonical_bytes(latest['origin']) and
        len(proposed['events'])<=len(latest['events']) and
        canonical_bytes(proposed['events'])==canonical_bytes(latest['events'][:len(proposed['events'])]))


def _ack(head, ledger, source, budget):
    return dict(schema_version='habu-development-job-report-transport-observation-v1',
        status='TRANSPORT_ACK_ONLY',observed_head=head,latest_tip=ledger['tip_sha256'],latest_ledger=ledger,
        root_report_source_commit=source,actual_blob_bytes_read=budget['bytes'],blob_reads=budget['reads'],
        persistence='OBSERVED_GIT_REPORT_HISTORY_NOT_AUTHENTICATED_JOB_OR_EXECUTION',
        limitations=['NO_ROOT_REQUEST_OR_SOURCE_ADMISSION','NO_CLOCK_OR_ACTUAL_RUNTIME_ATTESTATION',
            'NO_LIVE_LEASE_OR_EXECUTION_PERMISSION','NO_CI_RESULT_AUTHENTICATION_OR_BACKEND_CONTINUATION',
            'SCIENCE_FIT_REQUIRES_SEPARATE_CUMULATIVE_BUDGET',
            'NONFORCE_SIBLING_PROTECTION_NOT_SERVER_EXACT_CAS_AGAINST_ADMIN_REF_RESET',
            'GIT_METADATA_NETWORK_SUBPROCESS_NOT_HARD_PREEMPTIBLE',
            'COMMIT_AUTHOR_TEXT_NOT_CONTROLLER_AUTHENTICATION'],**FLAGS)


def _publish_development_job(transport, ledger, *, root_report_source_commit, expected_remote_head, expected_tip):
    """Explicit private transport seam; never exposed through flags or a CLI."""
    ledger,_ = _validated(ledger)
    source = _hash(root_report_source_commit,40); _hash(expected_tip)
    if expected_remote_head is not None: _hash(expected_remote_head,40)
    branch,prefix,records = _publication_records(ledger,source)
    budget = dict(bytes=0,reads=[],cache={})
    head = transport.head(branch)
    if head is not None:
        latest = _view(transport,head,source,ledger['origin'],budget)
        if _prefix(ledger,latest):
            predecessors = {ledger['tip_sha256']}
            if ledger['events']: predecessors.add(ledger['events'][-1]['previous_sha256'])
            if expected_tip not in predecessors:
                raise ValueError('Expected development semantic predecessor mismatch')
            return _ack(head,latest,source,budget)
        if expected_remote_head is None or expected_remote_head!=head:
            raise ValueError('Development report conflict; reconcile actual remote history')
        if (expected_tip!=latest['tip_sha256'] or len(ledger['events'])!=len(latest['events'])+1 or
                not _prefix(latest,ledger)):
            raise ValueError('Development report must append one exact event')
        event = ledger['events'][-1]
        event_path = prefix+f"events/{event['sequence']:04d}-{event['event_sha256']}.json"
        files = {prefix+'state.json':records[prefix+'state.json'],event_path:records[event_path]}
    else:
        if expected_remote_head is not None or ledger['events'] or expected_tip!=ledger['tip_sha256']:
            raise ValueError('Only absent zero-event development job may bootstrap')
        if _report_tree(transport,source,prefix):
            raise ValueError('Preexisting job in report base cannot be reset')
        files = records
    failure = None
    try:
        transport.publish(branch,source,head,files)
    except Exception as exc:
        failure = exc
    observed = transport.head(branch)
    if observed is None:
        raise ValueError('Development publication unconfirmed; no execution authorized') from failure
    latest = _view(transport,observed,source,ledger['origin'],budget)
    if not _prefix(ledger,latest):
        raise ValueError('Development publication diverged; no automatic retry/reset') from failure
    return _ack(observed,latest,source,budget)


def publish_development_job(root, ledger, *, root_report_source_commit, expected_remote_head, expected_tip):
    """Observe fixed origin/report-only transport, without job execution authority."""
    from pdca_bridge import GitTransport
    return _publish_development_job(GitTransport(root,'origin'),ledger,
        root_report_source_commit=root_report_source_commit,
        expected_remote_head=expected_remote_head,expected_tip=expected_tip)
