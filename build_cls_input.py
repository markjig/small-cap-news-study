import json, os, re, glob, random, hashlib, datetime as dt, urllib.request
UA = open(os.path.expanduser('~/.sec_ua')).read().strip()
tk = json.load(urllib.request.urlopen(urllib.request.Request('https://www.sec.gov/files/company_tickers.json', headers={'User-Agent': UA})))
NAME = {v['ticker']: v['title'] for v in tk.values()}
WIRE = re.compile(r'newswire|business wire|globenewswire|press release|accesswire|newsfile|einpresswire|prweb|marketwired', re.I)
def nm(t):
    n = NAME[t]
    for _ in range(3): n = re.sub(r'[,\s]+(inc|corp|corporation|co|ltd|limited|plc|llc|lp)\.?$', '', n.strip(), flags=re.I)
    return n.strip(' ,.')
cut = (dt.date.today() - dt.timedelta(days=365)).isoformat(); out = []; seen = set()
for fp in sorted(glob.glob('out/pilot/rss_cache/*.json')):
    t = os.path.basename(fp)[:-5]; first = nm(t).lower().split()[:2]
    for ts, ti, so in json.load(open(fp)):
        if ts[:10] < cut or not so or WIRE.search(so): continue
        head = re.sub(r'\s+-\s+[^-]+$', '', ti); tl = head.lower()
        if not all(w in tl for w in first): continue
        k = (t, re.sub(r'\W+', ' ', tl))
        if k in seen: continue
        seen.add(k)
        out.append({'id': t + '-' + hashlib.md5(head.encode()).hexdigest()[:8], 'ticker': t, 'company': nm(t), 'date': ts[:10], 'source': so, 'headline': head})
random.Random(5).shuffle(out); out = sorted(out[:2400], key=lambda r: (r['ticker'], r['date']))
for f in glob.glob('data/cls/*'): os.remove(f)
for n in range(0, len(out), 100):
    with open(f'data/cls/in_{n // 100 + 1:04d}.jsonl', 'w') as f:
        for r in out[n:n + 100]: f.write(json.dumps(r) + '\n')
print('headlines', len(out), 'chunks', (len(out) + 99) // 100)
