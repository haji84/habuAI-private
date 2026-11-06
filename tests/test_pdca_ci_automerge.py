import copy
import unittest

from scripts.pdca_ci_automerge import eligible

RID='a'*64
NIGHT='2026-10-20'
REPO='haji84/habuAI-private'
HEAD='b'*40
BASE={'repo':{'full_name':REPO},'ref':'main'}


def fixture():
    event={'action':'completed','repository':{'full_name':REPO},
           'workflow_run':{'name':'data-intake-tests','event':'pull_request',
                           'conclusion':'success','head_sha':HEAD,'head_repository':{'full_name':REPO},
                           'pull_requests':[{'number':300}]}}
    pr={'number':300,'state':'open','draft':False,'base':BASE,
        'head':{'ref':'pdca/run-'+RID,'sha':HEAD,'repo':{'full_name':REPO}},
        'title':'PDCA evidence: '+NIGHT,'requested_reviewers':[],'requested_teams':[],'labels':[]}
    paths=[f'reports/pdca/{NIGHT}/runs/{RID}/run_manifest.json',
           f'reports/pdca/{NIGHT}/runs/{RID}/evidence_manifest.json',
           f'reports/pdca/{NIGHT}/bridge/recovery-{RID}.json']
    changes=[{'filename':p,'status':'added'} for p in paths]
    return event,pr,changes


class AutoMergeGateTests(unittest.TestCase):
    def test_healthy_report_only_pr(self):
        self.assertEqual(eligible(*fixture(),REPO),(True,'ALLOW_REPRODUCIBLE_REPORT_ONLY'))

    def test_reject_unsafe_scope_and_missing_proof(self):
        for item in ('data/raw/gpx/private.gpx','src/master_orchestrator.py',
                     'predictions/original/2026-10-20/P0/prediction.json',
                     'reports/pdca/2026-10-18/runs/elsewhere.md'):
            with self.subTest(item=item):
                ev,pr,changes=fixture(); changes.append({'filename':item,'status':'added'})
                self.assertFalse(eligible(ev,pr,changes,REPO)[0])
        ev,pr,changes=fixture();changes.pop()
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])

    def test_reject_incomplete_ci_wrong_head_and_gate(self):
        ev,pr,changes=fixture(); ev['workflow_run']['conclusion']='failure'
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])
        ev,pr,changes=fixture();pr['head']['sha']='c'*40
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])
        ev,pr,changes=fixture();pr['draft']=True
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])
        ev,pr,changes=fixture();pr['labels']=[{'name':'human-gate'}]
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])
        ev,pr,changes=fixture();pr['head']['ref']='data/october'
        self.assertFalse(eligible(ev,pr,changes,REPO)[0])


if __name__=='__main__': unittest.main()
