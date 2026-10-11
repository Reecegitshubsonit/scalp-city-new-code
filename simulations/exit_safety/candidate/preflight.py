"""Read-only release preflight. Never places/cancels orders or edits the live checkout.
Usage: .venv/bin/python simulations/exit_safety/candidate/preflight.py
"""
import json,hashlib,sys
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'simulations/exit_safety/evidence'

def evaluate():
    reconciliation=json.loads((EVIDENCE/'broker-reconciliation.json').read_text())
    quotes=json.loads((EVIDENCE/'quote-replay.json').read_text())
    manifest=json.loads((EVIDENCE/'candidate-manifest.json').read_text())
    altered=[name for name,sha in manifest.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    suite=ET.parse(EVIDENCE/'integration-junit.xml').getroot().find('testsuite')
    smoke_path=ROOT/'data/exit-safety/shadow-minute-smoke-20261009/summary.json'
    smoke=json.loads(smoke_path.read_text()) if smoke_path.exists() else {}
    counts=smoke.get('counts',{})
    checks={
        'candidate_files_match_tested_manifest':not altered,
        'integration_tests_passed':int(suite.attrib['tests'])>0 and int(suite.attrib['failures'])==0 and int(suite.attrib['errors'])==0,
        'legacy_non_server_tests_passed':'75 passed' in (EVIDENCE/'legacy-without-server.txt').read_text(),
        'server_tests_passed':'3 passed' in (EVIDENCE/'server-regression.txt').read_text(),
        'captured_quote_pnl_accounting_passed':all(r['accounting_matches'] for r in quotes['results']),
        'read_only_shadow_runner_passed':smoke.get('mode')=='shadow' and smoke.get('remote_order_calls')==0 and counts.get('bar',0)>0 and counts.get('underlying',0)>0 and counts.get('options',0)>0 and counts.get('error',1)==0,
        'broker_positions_match_log':not reconciliation['position_mismatches'],
        'legacy_fills_unambiguously_reconciled':not reconciliation['unmatched_sequences'] and not reconciliation['ambiguous_sequences'],
        'dedicated_options_account':not reconciliation['other_account_instruments'],
        'representative_strategy_quote_validation':False,
        'fresh_startup_broker_reconciliation':False,
        'paper_order_adapter_smoke_test':False,
    }
    # This file cannot turn sample accounting validation into full strategy validation.
    return {'ready_for_shadow_use':all(checks[k] for k in list(checks)[:6]),'ready_for_paper_order_activation':all(checks.values()),'checks':checks,'modified_candidate_files':altered}

if __name__=='__main__':
    report=evaluate();print(json.dumps(report,indent=2))
    sys.exit(0 if report['ready_for_paper_order_activation'] else 2)
