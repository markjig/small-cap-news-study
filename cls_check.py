import json, sys
NAT = {'FACT_EVENT', 'ANALYST_ACTION', 'OPINION_COMMENTARY', 'HIT_PIECE', 'PRICE_RECAP', 'ROUTINE', 'SOLICITATION', 'UNCLEAR'}
POL = {'NEG', 'POS', 'NEUTRAL', 'MIXED'}; SEV = {'CLEARLY_NEGATIVE', 'MILD_NEGATIVE', 'NONE'}
def fail(m): print('BAD', m); sys.exit(1)
ids = [json.loads(l)['id'] for l in open(sys.argv[1]) if l.strip()]
try: rows = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
except Exception as e: fail(e)
if [r.get('id') for r in rows] != ids: fail('ids differ')
for r in rows:
    if r.get('nature') not in NAT or r.get('polarity') not in POL or r.get('severity') not in SEV: fail(r.get('id'))
    if r.get('third_party_voice') not in (True, False, None): fail('voice')
    c = r.get('confidence')
    if not isinstance(c, (int, float)) or not 0 <= c <= 1: fail('conf')
    if not isinstance(r.get('reason'), str) or len(r['reason']) > 120: fail('reason')
    if r['severity'] != 'NONE' and r['polarity'] not in ('NEG', 'MIXED'): fail('sev/pol ' + r['id'])
    if r['severity'] == 'CLEARLY_NEGATIVE' and r['nature'] != 'FACT_EVENT': fail('clearly needs FACT_EVENT ' + r['id'])
print('OK', len(rows))
