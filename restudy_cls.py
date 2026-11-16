import glob, hashlib
exec(open('pilot.py').read().split("WIRE = re.compile")[0])
WIRE = re.compile(r'newswire|business wire|globenewswire|press release|accesswire|newsfile|einpresswire|prweb|marketwired', re.I)
def nm(t):
    n = BYT[t][1]
    for _ in range(3): n = re.sub(r'[,\s]+(inc|corp|corporation|co|ltd|limited|plc|llc|lp)\.?$', '', n.strip(), flags=re.I)
    return n.strip(' ,.')
CLS = {}
for fp in glob.glob('data/cls/out_*.jsonl'):
    for l in open(fp):
        if l.strip(): r = json.loads(l); CLS[r['id']] = r
RC = {}
if os.path.exists('data/cls/recheck_out.jsonl'):
    for l in open('data/cls/recheck_out.jsonl'):
        if l.strip(): r = json.loads(l); RC[r['id']] = r
BF = list(P)[:NB]; G = {}; EV = {}; unc = cov = 0
for t in BF:
    D = P[t][0]; first = nm(t).lower().split()[:2]; seen = []; last = {}
    for ts, ti, so in sorted(json.load(open(O + 'rss_cache/' + t + '.json'))):
        d = dt.datetime.fromisoformat(ts).astimezone(ET); eff = d.date() if d.hour < 16 else d.date() + dt.timedelta(days=1)
        if eff < today - dt.timedelta(days=365): continue
        i0 = bisect_left(D, eff)
        if i0 >= len(D): continue
        head = re.sub(r'\s+-\s+[^-]+$', '', ti); tl = head.lower()
        if not all(w in tl for w in first): continue
        tok = set(w for w in re.findall(r'[a-z]+', tl) if len(w) > 2)
        if any(abs((d - sd).total_seconds()) < 72 * 3600 and len(tok & st) / max(1, len(tok | st)) > 0.6 for sd, st in seen): continue
        seen.append((d, tok))
        if WIRE.search(so) or not so: continue
        c = CLS.get(t + '-' + hashlib.md5(head.encode()).hexdigest()[:8])
        if not c: unc += 1; continue
        cov += 1; n_, p_, s_ = c['nature'], c['polarity'], c['severity']; neg = p_ in ('NEG', 'MIXED'); g = None
        rc = RC.get(c['id'])
        if rc and rc['strict_severity'] == 'NONE': continue
        if rc and rc['strict_severity'] == 'CLEARLY_NEGATIVE' and c['third_party_voice'] is not False: g = 'fact_clearly_neg'
        elif rc and rc['subtype'] == 'EARNINGS_RESULT': g = 'earnings_result_neg'
        elif not RC and n_ == 'FACT_EVENT' and s_ == 'CLEARLY_NEGATIVE' and c['third_party_voice'] is not False: g = 'fact_clearly_neg'
        elif n_ == 'FACT_EVENT' and neg: g = 'fact_mild_neg'
        elif n_ == 'ANALYST_ACTION' and neg: g = 'analyst_neg'

        elif n_ == 'OPINION_COMMENTARY' and neg: g = 'opinion_neg'
        elif n_ == 'HIT_PIECE': g = 'hit_piece'
        elif n_ == 'PRICE_RECAP' and p_ == 'NEG': g = 'price_recap_neg'
        elif n_ == 'FACT_EVENT' and p_ == 'POS': g = 'fact_pos'
        if not g: continue
        g2 = g + ('_with8k' if any(abs(i0 - j) <= 1 for j in K8[t]) else '_clean')
        if g2 in last and (eff - last[g2]).days < 30: continue
        last[g2] = eff; G.setdefault(g2, []).append((t, i0, head, c['reason'])); EV.setdefault(t, set()).add(i0)
excl = {t: set(K8[t]) | EV.get(t, set()) for t in BF}; lo12 = lambda t: len(P[t][0]) - 250; rows = []
for g in sorted(G):
    for r in summ(g, [(t, i) for t, i, _, _ in G[g]], excl, lo12):
        wi = 0 if r[1] == '0_1' else 1; v = sorted(CAR[t][i][wi] for t, i, _, _ in G[g] if i in CAR[t] and CAR[t][i][wi] is not None)
        k = max(1, len(v) // 50); tr = v[k:len(v) - k] or v
        rows.append(r + ([round(100 * v[len(v) // 2], 3), round(100 * sum(tr) / len(tr), 3)] if v else ['', '']))
with open(O + 'summary_cls.csv', 'w', newline='') as f: w = csv.writer(f); w.writerow(H + ['median_pct', 'trim2_pct']); w.writerows(rows)
with open(O + 'events_cls.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ticker', 'trade_date', 'group', 'headline', 'reason', 'abn_0_1', 'abn_0_5'])
    for g, ev in G.items():
        for t, i, h, rs in ev: w.writerow([t, P[t][0][i], g, h, rs, CAR[t].get(i, (None, None))[0], CAR[t].get(i, (None, None))[1]])
print('classified headlines used', cov, 'unclassified', unc, '| classes seen', len(CLS)); print('DONE restudy')
