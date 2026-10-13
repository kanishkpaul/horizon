"""Read-only audit of originals; mutations are confined to temporary DB snapshots.
Run from repo root: backend/.venv/bin/python docs/analysis-2026-10-10/probes.py
"""
from pathlib import Path
import copy, hashlib, importlib.util, json, sqlite3, tempfile, math
import numpy as np
from horizon import service as S, research_ingest as RI, execution as E
from horizon.db import ROOT, connect
from horizon.sim import analysis as A
from horizon.sim.engine import Simulator
from horizon.sim.params import Dist

OUT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('helpers', ROOT/'backend/tests/test_sim_validation.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
tmp = Path(tempfile.mkdtemp(prefix='horizon-deep-audit-'))
src = sqlite3.connect(f'file:{ROOT}/data/horizon.sqlite3?mode=ro', uri=True)
src.row_factory = sqlite3.Row
dst = sqlite3.connect(tmp/'snapshot.sqlite3'); src.backup(dst); dst.close()
c = connect(tmp/'snapshot.sqlite3')
result = {'snapshot': str(tmp/'snapshot.sqlite3'), 'inventory': {}, 'probes': {}}
inv = result['inventory']; p = result['probes']
for table in ['opportunity','claim','source','organization','person','event','hypothesis','outreach_target','parameter','strategy','objective_profile','sim_run','action_item','outcome','forecast','media','doc_embedding','doc_fts','shortlist','edge']:
    inv[table] = src.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
for field, table in [('origin','parameter'),('origin','opportunity'),('status','claim')]:
    inv[f'{table}_by_{field}'] = dict(src.execute(f'SELECT {field}, COUNT(*) FROM {table} GROUP BY {field}').fetchall())
inv['integrity'] = src.execute('PRAGMA integrity_check').fetchone()[0]
inv['foreign_key_check'] = [list(r) for r in src.execute('PRAGMA foreign_key_check')]
inv['raw_checksums'] = []
for line in (ROOT/'data/raw/SHA256SUMS').read_text().splitlines():
    sha, rel = line.split('  ',1); f = ROOT/'data/raw'/rel
    inv['raw_checksums'].append({'path':rel,'exists':f.exists(),'matches':f.exists() and hashlib.sha256(f.read_bytes()).hexdigest()==sha})
inv['archives'] = [{'id':r['id'],'exists':bool(r['archive_path'] and (ROOT/r['archive_path']).exists())} for r in src.execute('SELECT id,archive_path FROM sim_run')]
inv['media_files'] = [{'id':r['id'],'status':r['status'],'exists':bool(r['path'] and (ROOT/'media/renders'/r['path']).exists())} for r in src.execute('SELECT id,status,path FROM media')]
inv['assessment_dates'] = [list(r) for r in src.execute('SELECT computed_at,COUNT(*) FROM opportunity_assessment GROUP BY computed_at')]
m = S.build_model(c); inv['actions']=len(m.actions); inv['fingerprint']=m.fingerprint()
inv['unused_parameters'] = [k for k in m.params if k not in (ROOT/'data/seed/actions.yaml').read_text() and k not in (ROOT/'backend/horizon/sim/engine.py').read_text()]

# Two 15h tasks, same half-week deadline, 40h/week -> only 20h before deadline.
acts=[{'id':i,'name':i,'effort':[15]*3,'deadline':'2026-10-12T12:00:00+05:30'} for i in ['a','b']]
r=h.run(h.mk(acts),h.S('a','b'),n=10)
p['shared_fractional_capacity']={'hours_before_deadline':20,'hours_used':r['metrics']['hours_used'][0],'a_done':r['action_stats']['a']['p_done'],'b_done':r['action_stats']['b']['p_done']}
# A one-day window within a weekly step must not receive a whole week's capacity.
acts=[{'id':'a','name':'a','effort':[30]*3,'start':'2026-10-15T00:00:00+05:30','deadline':'2026-10-16T00:00:00+05:30'}]
r=h.run(h.mk(acts),h.S('a'),n=10)
p['fractional_start']={'available_expected':40/7,'p_done':r['action_stats']['a']['p_done'],'hours_used':r['metrics']['hours_used'][0]}
# Fingerprint collision after an actual behavior-changing edit.
m1=h.mk([{'id':'a','name':'a','effort':[50]*3}]); m2=copy.deepcopy(m1);m2.actions[0].max_hours_week=1
p['fingerprint_collision']={'before':m1.fingerprint(),'after':m2.fingerprint(),'completion_before':h.run(m1,h.S('a'),n=10)['action_stats']['a']['mean_completion_week'],'completion_after':h.run(m2,h.S('a'),n=10)['action_stats']['a']['mean_completion_week']}
# Offer after graduation still counted by graduation.
m1=h.mk([{'id':'a','name':'a','effort':[1]*3,'stages':[{'name':'s','delay':2,'outcomes':[{'label':'offer','p':1,'metrics':{'offer':'job'}}]}]}],offers={'job':{'position':True}},horizon=10);m1.graduation_week=2
r=h.run(m1,h.S('a'),n=10)
p['graduation_grace']={'graduation_week':2,'offer_week':float(r['offer_week']['job'][0]),'position_by_grad':r['metrics']['position_by_grad'][0]}
# Risk ranking comparison is against mean, not CVaR.
rr={'risky':{'metrics':{'cash_lpa':np.array([0.]*20+[10.]*80)}},'safe':{'metrics':{'cash_lpa':np.full(100,4.)}}}
ev=A.evaluate(rr,{'weights':{'cash_lpa':1},'risk':{'measure':'cvar','alpha':.2}},{'caps':{'cash_lpa':100}})
p['risk_comparison']={'ranking':ev['ranking'],'comparison':ev['top_vs_runner_up']}
# Ties are reported as infinitely statistically separated.
ev=A.evaluate({'a':rr['safe'],'b':rr['safe']},{'weights':{'cash_lpa':1}}, {})
p['identical_strategies_comparison']=ev['top_vs_runner_up']
from horizon.eligibility import assess
p['nationality_matching']=assess({'name':'Example','eligibility_text':'US citizens only','country':'USA'}, {'citizenship':'US','graduation':'2027-06','relocation':'yes'})
# invalid calibration: committed outcome and status before validation error.
aid=E.upsert_action(c,{'title':'audit action','status':'todo'})['id']
before=c.execute('SELECT COUNT(*) FROM outcome').fetchone()[0]
try:E.record_outcome(c,{'action_id':aid,'mark_done':True,'param_name':'p_reply_faculty','successes':6,'trials':5})
except Exception as e:p['non_atomic_outcome']={'error':str(e),'outcomes_added':c.execute('SELECT COUNT(*) FROM outcome').fetchone()[0]-before,'action_status':c.execute('SELECT status FROM action_item WHERE id=?',(aid,)).fetchone()[0]}
p['invalid_distributions_accepted']=[v for v in ['beta(-1,2)','normal(0,-1)','bernoulli(2)','fixed(nan)'] if Dist.parse(v)]
# Real state scenario regression: feasibility dropped from minimax regret.
from horizon.analysis_jobs import scenario_regret
reg=scenario_regret(c,None,'robust',1000)
p['robust_minimax']={'choice':reg['regret']['minimax_choice'],'feasibility_by_scenario':{sc:next(r['feasible'] for r in d['ranking'] if r['strategy']==reg['regret']['minimax_choice']) for sc,d in reg['detail'].items()}}
for fn in [RI.ingest_verify,RI.ingest_discovery]:
    before=c.execute('SELECT COUNT(*) FROM edge').fetchone()[0]
    try:
        fn(c); mid=c.execute('SELECT COUNT(*) FROM edge').fetchone()[0];fn(c);after=c.execute('SELECT COUNT(*) FROM edge').fetchone()[0]
        p[fn.__name__]={'edges_before':before,'after_once':mid,'after_twice':after}
    except Exception as e:p[fn.__name__]={'error':str(e)}
# Fact corrections don't change curated model.
before=S.build_model(c).fingerprint(); S.update_profile_item(c,'geography.relocation',{'value':'no'})
p['profile_model_link']={'profile_keys':[r[0] for r in c.execute('SELECT id FROM profile_item')],'fingerprint_before':before,'fingerprint_after':S.build_model(c).fingerprint()}
# Regenerating a plan preserves the completed row but also creates a fresh todo copy.
rid='RUN-20261009-183650-9248'
plan=E.generate_plan(c,rid,None)
first=plan['items'][0]
E.upsert_action(c,{'id':first['id'],'status':'done'})
E.generate_plan(c,rid,plan['strategy'])
p['plan_regeneration']={'action':first['strategy_action'],'copies':c.execute('SELECT COUNT(*) FROM action_item WHERE strategy_action=? AND sim_run_id=?',(first['strategy_action'],rid)).fetchone()[0]}
# JSONResponse cannot encode the native infinity returned for identical strategies.
from horizon.api import _json
try:_json({'comparison':ev['top_vs_runner_up']})
except Exception as e:p['identical_json_error']=str(e)
def strict(obj):
    if isinstance(obj,np.generic):return strict(obj.item())
    if isinstance(obj,float) and not math.isfinite(obj):return str(obj)
    if isinstance(obj,dict):return {k:strict(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [strict(v) for v in obj]
    if isinstance(obj,Path):return str(obj)
    return obj
def clean(obj):
    if isinstance(obj,np.generic):return obj.item()
    if isinstance(obj,Path):return str(obj)
    raise TypeError(type(obj))
result=strict(result)
(OUT/'evidence.json').write_text(json.dumps(result,indent=2,default=clean,allow_nan=False))
print(json.dumps(result,indent=2,default=clean,allow_nan=False))
src.close();c.close()
