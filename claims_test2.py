import urllib.request, urllib.parse, re, json, os, datetime as dt, time
from email.utils import parsedate_to_datetime as pd
UA = open(os.path.expanduser('~/.sec_ua')).read().strip()
def get(u, ua='Mozilla/5.0'):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua}), timeout=30).read()
T = {'LIVE': 'Live Ventures', 'DIT': 'AMCON Distributing', 'BGS': 'B&G Foods'}
today = dt.date.today(); R = {}
def gn(q, a, b):
    u = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(f'"{q}" after:{a} before:{b}') + '&hl=en-US&gl=US&ceid=US:en'
    time.sleep(2)
    x = get(u).decode('utf8', 'ignore')
    out = []
    for i in re.findall(r'<item>.*?</item>', x, re.S):
        m = re.search(r'<pubDate>(.*?)</pubDate>', i)
        if m: out.append(pd(m.group(1)).date())
    return out
tk = json.loads(get('https://www.sec.gov/files/company_tickers.json', UA))
for t, n in T.items():
    r = {}
    r['A_90d'] = []; r['A_30d'] = []
    for k in range(12):
        e = today - dt.timedelta(days=90 * k); s = e - dt.timedelta(days=90)
        r['A_90d'].append(len(gn(n, s, e)))
    for k in range(36):
        e = today - dt.timedelta(days=30 * k); s = e - dt.timedelta(days=30)
        r['A_30d'].append(len(gn(n, s, e)))
    r['A_sum90'] = sum(r['A_90d']); r['A_sum30'] = sum(r['A_30d'])
    cik = [v['cik_str'] for v in tk.values() if v['ticker'] == t][0]
    s = json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', UA))['filings']['recent']
    cut = (today - dt.timedelta(days=1095)).isoformat()
    d202 = [d for f, d, i in zip(s['form'], s['filingDate'], s['items']) if f == '8-K' and d >= cut and '2.02' in i]
    b = {'<1y': [0, 0], '1-2y': [0, 0], '2-3y': [0, 0]}
    for d in d202:
        D = dt.date.fromisoformat(d); age = (today - D).days
        k = '<1y' if age < 365 else '1-2y' if age < 730 else '2-3y'
        hit = any(abs((x - D).days) <= 3 for x in gn(n, D - dt.timedelta(days=3), D + dt.timedelta(days=4)))
        b[k][0] += hit; b[k][1] += 1
    r['B_recall_hit_total'] = b
    R[t] = r
    json.dump(R, open('out/claims_test2.json', 'w'), indent=1)
print(json.dumps({t: {k: v for k, v in r.items() if k in ('A_sum90', 'A_sum30', 'B_recall_hit_total')} for t, r in R.items()}, indent=1))
