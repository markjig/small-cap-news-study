import urllib.request, urllib.parse, re, json, os, datetime as dt, time
from email.utils import parsedate_to_datetime as pd
UA = open(os.path.expanduser('~/.sec_ua')).read().strip()
def get(u, ua='Mozilla/5.0'):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua}), timeout=30).read()
T = {'LIVE': 'Live Ventures', 'DIT': 'AMCON Distributing', 'BGS': 'B&G Foods'}
today = dt.date.today(); R = {}
def gn(q, a, b):
    u = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(f'"{q}" after:{a} before:{b}') + '&hl=en-US&gl=US&ceid=US:en'
    x = get(u).decode('utf8', 'ignore')
    items = re.findall(r'<item>.*?</item>', x, re.S)
    ds = [pd(re.search(r'<pubDate>(.*?)</pubDate>', i).group(1)).date() for i in items if '<pubDate>' in i]
    ti = [re.search(r'<title>(.*?)</title>', i, re.S).group(1) for i in items]
    return len(items), (min(ds).isoformat() if ds else None), (max(ds).isoformat() if ds else None), len(set(ti))
for t, n in T.items():
    r = {}
    a = (today - dt.timedelta(days=1095)).isoformat()
    r['gn_full_3y'] = gn(n, a, today.isoformat())
    wins = []
    for k in range(12):
        e = today - dt.timedelta(days=90 * k); s = e - dt.timedelta(days=90)
        try: wins.append(gn(n, s.isoformat(), e.isoformat())[:1][0])
        except Exception as ex: wins.append(str(ex)[:40])
        time.sleep(2)
    r['gn_12x90d_counts'] = wins
    y = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=3y&interval=1d'))['chart']['result'][0]
    c = y['indicators']['quote'][0]
    r['yahoo'] = {'rows': len(y['timestamp']), 'null_close': sum(v is None for v in c['close']), 'zero_vol': sum((v or 0) == 0 for v in c['volume'])}
    R[t] = r
tk = json.loads(get('https://www.sec.gov/files/company_tickers.json', UA))
for t in T:
    cik = [v['cik_str'] for v in tk.values() if v['ticker'] == t][0]
    s = json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', UA))['filings']['recent']
    cut = (today - dt.timedelta(days=1095)).isoformat()
    k8 = [(f, d, i) for f, d, i in zip(s['form'], s['filingDate'], s['items']) if f == '8-K' and d >= cut]
    R[t]['sec_8k_3y'] = len(k8); R[t]['sec_8k_item202'] = sum('2.02' in i for _, _, i in k8)
    R[t]['sec_oldest_in_recent'] = min(s['filingDate'])
json.dump(R, open('out/claims_test.json', 'w'), indent=1)
print(json.dumps(R, indent=1))
