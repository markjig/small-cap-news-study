import urllib.request, urllib.parse, re, json, os, csv, random, time, html, datetime as dt
from bisect import bisect_left, bisect_right
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime as pdt
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York'); O = 'out/pilot/'
UA = open(os.path.expanduser('~/.sec_ua')).read().strip()
today = dt.date.today(); NB = 60; NA = 150
def get(u, ua='Mozilla/5.0'):
    err = None
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua}), timeout=30).read()
        except Exception as e: err = e; time.sleep(3 * (i + 1))
    raise err
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def prices(t):
    time.sleep(0.3)
    j = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=3y&interval=1d'))['chart']['result'][0]
    off = j['meta'].get('gmtoffset', 0); q = j['indicators']['quote'][0]
    adj = ((j['indicators'].get('adjclose') or [{}])[0].get('adjclose')) or q['close']
    D, C, V = [], [], []
    for ts, c, v in zip(j['timestamp'], adj, q['volume']):
        if c is None: continue
        D.append(dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).date()); C.append(c); V.append(v or 0)
    return D, C, V
def univ():
    R = list(csv.DictReader(open('data/universe_mc.csv'))); cols = {c.lower(): c for c in R[0]}
    tc = next(cols[c] for c in cols if c in ('ticker', 'symbol'))
    mc = next((cols[c] for c in cols if 'mcap' in c or 'market' in c), None)
    out = set()
    for r in R:
        t = (r.get(tc) or '').strip().upper()
        if not t or '-' in t or '.' in t: continue
        if mc:
            try:
                if not 5e6 <= float(r[mc]) <= 2e9: continue
            except: continue
        out.add(t)
    return sorted(out)
TK = json.loads(get('https://www.sec.gov/files/company_tickers.json', UA))
BYT = {v['ticker']: (v['cik_str'], v['title']) for v in TK.values()}
random.seed(7)
U = [t for t in univ() if t in BYT]; random.shuffle(U); log('universe', len(U))
B = prices('IWM'); BD = B[0]
def bench(d): return B[1][max(0, bisect_right(BD, d) - 1)]
def car_at(P, i0, k):
    D, C, V = P
    if i0 < 1 or i0 + k > len(D) - 1: return None
    b = i0 - 1
    while b >= 0 and V[b] == 0: b -= 1
    if b < 0: return None
    e = i0 + k
    while e > b and V[e] == 0: e -= 1
    if e < i0: return None
    return (C[e] / C[b] - 1) - (bench(D[e]) / bench(D[b]) - 1)
P, CAR, K8, CAT = {}, {}, {}, {}
exc = {'no_cik_or_price': 0}
log('phase A: prices+8K')
for t in U:
    if len(P) >= NA: break
    try:
        p = prices(t)
        if len(p[0]) < 300: exc['no_cik_or_price'] += 1; continue
        cik = BYT[t][0]
        s = json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', UA))['filings']['recent']; time.sleep(0.15)
    except Exception: exc['no_cik_or_price'] += 1; continue
    P[t] = p; D = p[0]
    CAR[t] = {i: (car_at(p, i, 1), car_at(p, i, 5), p[2][i] == 0) for i in range(1, len(D) - 5)}
    cut = (today - dt.timedelta(days=1095)).isoformat(); K8[t] = []; CAT[t] = {}
    for f, d, acc, it in zip(s['form'], s['filingDate'], s['acceptanceDateTime'], s['items']):
        if f != '8-K' or d < cut: continue
        a = dt.datetime.fromisoformat(acc.replace('Z', '+00:00')).astimezone(ET)
        eff = a.date() if a.hour < 16 else a.date() + dt.timedelta(days=1)
        i0 = bisect_left(D, eff)
        if i0 >= len(D): continue
        its = [x.strip() for x in it.split(',') if x.strip() and x.strip() != '9.01']
        cat = 'earnings' if '2.02' in its else ('officer_5.02' if '5.02' in its else ('agreement_1.01' if '1.01' in its else ('disclosure_7.01_8.01' if any(x in ('7.01', '8.01') for x in its) else 'other')))
        CAT[t].setdefault(i0, set()).add(cat); K8[t].append(i0)
    if len(P) % 25 == 0: log('A firms', len(P))
def clean8(t, i):
    return not any('earnings' in CAT[t].get(j, ()) for j in range(i - 1, i + 2))
def pool(t, excl, lo):
    bad = set()
    for i in excl: bad.update(range(i - 3, i + 4))
    return [i for i, v in CAR[t].items() if i not in bad and i > lo(t) and v[0] is not None and v[1] is not None]
def summ(label, evs, scope_excl, lo=lambda t: 250):
    rows = []; rng = random.Random(1)
    for wi, wn in ((0, '0_1'), (1, '0_5')):
        vals = [(f, CAR[f][i][wi], CAR[f][i][2]) for f, i in evs if i in CAR[f] and CAR[f][i][wi] is not None]
        if not vals: rows.append([label, wn, 0, 0, '', '', '', '', '']); continue
        byf = {}
        for f, v, _ in vals: byf.setdefault(f, []).append(v)
        allv = [v for _, v, _ in vals]; m = sum(allv) / len(allv); fl = list(byf); bs = []
        for _ in range(1000):
            s = []
            for f in [rng.choice(fl) for _ in fl]: s += byf[f]
            bs.append(sum(s) / len(s))
        bs.sort(); pbs = []
        PL = {f: pool(f, scope_excl[f], lo) for f in byf}
        for _ in range(500):
            s = []
            for f in byf:
                if PL[f]: s += [CAR[f][rng.choice(PL[f])][wi] for _ in byf[f]]
            if s: pbs.append(sum(s) / len(s))
        pm = sum(pbs) / len(pbs) if pbs else 0
        p = (1 + sum(abs(x - pm) >= abs(m - pm) for x in pbs)) / (len(pbs) + 1) if pbs else ''
        rows.append([label, wn, len(vals), len(byf), round(100 * m, 3), round(100 * bs[25], 3), round(100 * bs[974], 3), p, round(sum(x[2] for x in vals) / len(vals), 3)])
    return rows
H = ['group', 'window', 'n_events', 'n_firms', 'mean_abn_ret_pct', 'ci95_lo_pct', 'ci95_hi_pct', 'placebo_p', 'stale_share']
log('phase A stats'); groups = {}
for t in P:
    for i, cs in CAT[t].items():
        for c in cs:
            if c == 'earnings' or clean8(t, i): groups.setdefault(c, []).append((t, i))
        if 'earnings' not in cs and clean8(t, i): groups.setdefault('any_non_earnings_clean', []).append((t, i))
excl8 = {t: set(K8[t]) for t in P}; rowsA = []
for g in sorted(groups): rowsA += summ(g, groups[g], excl8)
with open(O + 'summary_8k.csv', 'w', newline='') as f: w = csv.writer(f); w.writerow(H); w.writerows(rowsA)
with open(O + 'events_8k.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ticker', 'event_trade_date', 'group', 'abn_0_1', 'abn_0_5', 'stale'])
    for g, ev in groups.items():
        for t, i in ev:
            c = CAR[t].get(i)
            if c: w.writerow([t, P[t][0][i], g, c[0], c[1], c[2]])
log('PHASE A DONE firms', len(P)); [print(r) for r in rowsA]
open('data/pilotA.done', 'w').write('ok')
WIRE = re.compile(r'newswire|business wire|globenewswire|press release|accesswire|newsfile|einpresswire|prweb|marketwired', re.I)
NEG = set('lawsuit sues sued probe investigation investigated downgrade downgrades cut cuts plunge plunges falls fall drops drop loss losses misses miss recall fraud bankruptcy default delisting warning slump tumble tumbles plummets layoffs halts subpoena resigns impairment weak decline declines lowers slashes concern concerns'.split()) | {'class action', 'short seller', 'going concern', 'guidance cut'}
POS = set('upgrade upgrades beats beat surges surge soars soar record raises raise wins win jumps jump gains gain rallies rally strong growth'.split())
def sent(t):
    tl = t.lower(); w = set(re.findall(r'[a-z]+', tl))
    n = bool(w & NEG) or any(x in tl for x in NEG if ' ' in x); p = bool(w & POS)
    return 'neg' if n and not p else ('pos' if p and not n else 'neu')
def nm(t):
    n = BYT[t][1]
    for _ in range(3): n = re.sub(r'[,\s]+(inc|corp|corporation|co|ltd|limited|plc|llc|lp)\.?$', '', n.strip(), flags=re.I)
    return n.strip(' ,.')
FAILS = {}
def one(w):
    n, s, e = w
    u = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(f'"{n}" after:{s} before:{e}') + '&hl=en-US&gl=US&ceid=US:en'
    time.sleep(random.uniform(0.1, 0.5))
    try: x = get(u).decode('utf8', 'ignore')
    except Exception: return None
    res = []
    for it in re.findall(r'<item>.*?</item>', x, re.S):
        m = re.search(r'<pubDate>(.*?)</pubDate>', it); ti = re.search(r'<title>(.*?)</title>', it, re.S); so = re.search(r'<source[^>]*>(.*?)</source>', it, re.S)
        if m and ti: res.append([pdt(m.group(1)).astimezone(dt.timezone.utc).isoformat(), html.unescape(ti.group(1)), html.unescape(so.group(1)) if so else ''])
    return res
def rss(t):
    fp = O + 'rss_cache/' + t + '.json'
    if os.path.exists(fp): return json.load(open(fp))
    n = nm(t); wins = [(n, today - dt.timedelta(days=14 * (k + 1)), today - dt.timedelta(days=14 * k)) for k in range(27)]
    with ThreadPoolExecutor(30) as ex: R = list(ex.map(one, wins))
    for j, r in enumerate(R):
        if r is None: time.sleep(5); R[j] = one(wins[j])
    FAILS[t] = sum(r is None for r in R)
    out = [x for r in R if r for x in r]
    json.dump(out, open(fp, 'w')); return out
BF = list(P)[:NB]; NEWS = {}; log('phase B firms', len(BF))
for n_, t in enumerate(BF):
    items = rss(t); D = P[t][0]; first = nm(t).lower().split()[:2]; seen = []; rows = []
    for ts, ti, so in sorted(items):
        d = dt.datetime.fromisoformat(ts).astimezone(ET); eff = d.date() if d.hour < 16 else d.date() + dt.timedelta(days=1)
        if eff < today - dt.timedelta(days=365): continue
        i0 = bisect_left(D, eff)
        if i0 >= len(D): continue
        head = re.sub(r'\s+-\s+[^-]+$', '', ti); tl = head.lower()
        if not all(w in tl for w in first): continue
        tok = set(w for w in re.findall(r'[a-z]+', tl) if len(w) > 2)
        if any(abs((d - sd).total_seconds()) < 72 * 3600 and len(tok & st) / max(1, len(tok | st)) > 0.6 for sd, st in seen): continue
        seen.append((d, tok)); wire = bool(WIRE.search(so)) or not so
        rows.append((i0, head, so, wire, sent(head), eff))
    NEWS[t] = rows
    if (n_ + 1) % 5 == 0: log('B firm', n_ + 1, 'items kept', sum(len(v) for v in NEWS.values()), 'failed windows', sum(FAILS.values()))
log('phase B stats'); evneg, evpos, evneg8, drops, val = [], [], [], [], []
excl = {t: set(K8[t]) | set(r[0] for r in NEWS[t]) for t in BF}
for t in BF:
    last = {'neg': None, 'pos': None}
    for i0, head, so, wire, s, eff in NEWS[t]:
        val.append([t, head, s])
        if wire or s == 'neu': continue
        if last[s] is not None and (eff - last[s]).days < 30: continue
        last[s] = eff; has8 = any(abs(i0 - j) <= 1 for j in K8[t])
        if s == 'neg': (evneg8 if has8 else evneg).append((t, i0))
        elif not has8: evpos.append((t, i0))
    D, C, V = P[t]
    for i in range(max(1, len(D) - 250), len(D)):
        if V[i] == 0 or V[i - 1] == 0: continue
        ar = (C[i] / C[i - 1] - 1) - (bench(D[i]) / bench(D[i - 1]) - 1)
        if ar <= -0.08:
            nn = [r for r in NEWS[t] if r[0] == i]
            drops.append([t, D[i], round(ar, 4), len(nn) > 0, any(not r[3] for r in nn), any(abs(i - j) <= 1 for j in K8[t])])
lo12 = lambda t: len(P[t][0]) - 250
rowsB = summ('news_negative_clean_third_party', evneg, excl, lo12) + summ('news_positive_clean_third_party', evpos, excl, lo12) + summ('news_negative_with_8k_pm1_NOT_CLEAN', evneg8, excl, lo12)
with open(O + 'summary_news.csv', 'w', newline='') as f: w = csv.writer(f); w.writerow(H); w.writerows(rowsB)
with open(O + 'events_news.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ticker', 'trade_date', 'group', 'headline', 'abn_0_1', 'abn_0_5', 'stale'])
    for g, ev in (('neg_clean', evneg), ('pos_clean', evpos), ('neg_8k', evneg8)):
        for t, i in ev:
            c = CAR[t].get(i); h = next((r[1] for r in NEWS[t] if r[0] == i), '')
            if c: w.writerow([t, P[t][0][i], g, h, c[0], c[1], c[2]])
with open(O + 'drops.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ticker', 'drop_date', 'abn_ret_1d', 'any_news_same_day', 'third_party_news_same_day', 'has_8k_pm1']); w.writerows(drops)
random.Random(3).shuffle(val)
with open(O + 'sentiment_validation.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ticker', 'headline', 'rule_label', 'hand_label_pos_neg_neu']); w.writerows([r + [''] for r in val[:100]])
nd = len(drops); a = sum(d[3] for d in drops); b = sum(d[5] for d in drops); c = sum((not d[3]) and (not d[5]) for d in drops)
open(O + 'README.txt', 'w').write(f"""PILOT README
Association only, NOT causation. Not exhaustive, not representative of all positive-OCF small caps.
Phase A: {len(P)} sampled small caps, SEC 8-K dates, 3y, abnormal return = stock minus IWM, trade-to-trade, base = last traded close before event day. After-4pm-ET filings roll to next trading day. The SEC 'recent' list may miss old 8-Ks for heavy filers.
Phase B: {len(BF)} firms, Google News RSS 14-day windows over last 365d. Recall decays with age and varies by firm. Wire releases excluded as company-issued. Dedupe: earliest per title cluster (Jaccard>0.6, 72h). Sentiment = small hand-made word list, NOT validated: label sentiment_validation.csv, then compute kappa.
Events: first per firm per 30 days; negative clean = no 8-K within +-1 trading day.
Placebo p: random non-event days of the same firms (+-3 days of any event/8-K excluded), 500 draws. CI = firm-cluster bootstrap, 1000 draws.
Big drops (<= -8% abnormal, 1 day, last 12m): n={nd}; with any RSS news same day {a}; with 8-K +-1 {b}; with neither {c} (neither = unexplained OR RSS miss). Conditioning on outcome biases this toward finding explanations.
Exclusions phase A: {exc}
RSS windows failed after retry: {sum(FAILS.values())} of {27*len(BF)}
""")
log('PHASE B DONE'); [print(r) for r in rowsB]; print(open(O + 'README.txt').read())
open('data/pilotB.done', 'w').write('ok')
