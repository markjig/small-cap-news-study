import sys, os, re, json, time, hashlib, threading, argparse, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
ap = argparse.ArgumentParser()
ap.add_argument('urls', nargs='*'); ap.add_argument('--file'); ap.add_argument('--workers', type=int, default=50)
ap.add_argument('--rate', type=float, default=10, help='max requests per second per host')
ap.add_argument('--grep'); ap.add_argument('--out', default='data/fetch'); ap.add_argument('--maxchars', type=int, default=400000)
a = ap.parse_args()
urls = list(a.urls)
if a.file: urls += [l.strip() for l in open(a.file) if l.strip() and not l.startswith('#')]
urls = list(dict.fromkeys(urls)); os.makedirs(a.out, exist_ok=True)
try: SECUA = open(os.path.expanduser('~/.sec_ua')).read().strip()
except Exception: SECUA = 'research-fetch'
class P(HTMLParser):
    def __init__(s): super().__init__(); s.t = []; s.skip = 0; s.title = ''; s.in_title = False
    def handle_starttag(s, tag, at):
        if tag in ('script', 'style', 'noscript', 'svg'): s.skip += 1
        if tag == 'title': s.in_title = True
        if tag in ('p', 'br', 'div', 'li', 'tr', 'h1', 'h2', 'h3'): s.t.append('\n')
    def handle_endtag(s, tag):
        if tag in ('script', 'style', 'noscript', 'svg'): s.skip = max(0, s.skip - 1)
        if tag == 'title': s.in_title = False
    def handle_data(s, d):
        if s.in_title: s.title += d
        elif not s.skip: s.t.append(d)
slots = {}; lock = threading.Lock()
def wait(h):
    with lock:
        now = time.time(); t = max(now, slots.get(h, 0)); slots[h] = t + 1 / a.rate
    if t > now: time.sleep(t - now)
def one(u):
    h = urllib.parse.urlparse(u).netloc
    ua = SECUA if h.endswith('sec.gov') else 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'
    err = ''
    for k in range(3):
        wait(h)
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua, 'Accept-Language': 'en-US,en'}), timeout=25)
            raw = r.read(3000000); ct = r.headers.get('content-type', '')
            if raw[:4] == b'%PDF': return {'url': u, 'status': 'pdf_skipped'}
            txt = raw.decode('utf8', 'ignore'); title = ''
            if 'json' not in ct and '<' in txt[:2000]:
                p = P(); p.feed(txt)
                txt = re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', ''.join(p.t))); title = re.sub(r'\s+', ' ', p.title).strip()
            txt = txt[:a.maxchars]; f = os.path.join(a.out, hashlib.sha1(u.encode()).hexdigest()[:12] + '.txt')
            open(f, 'w').write(txt)
            return {'url': u, 'status': r.status, 'chars': len(txt), 'file': f, 'title': title[:90], 'text': txt}
        except urllib.error.HTTPError as e:
            if e.code in (429, 503): err = str(e.code); time.sleep(5 * (k + 1)); continue
            return {'url': u, 'status': e.code}
        except Exception as e: err = str(e)[:60]; time.sleep(2)
    return {'url': u, 'status': 0, 'err': err}
t0 = time.time()
with ThreadPoolExecutor(a.workers) as ex: R = list(ex.map(one, urls))
pat = re.compile(a.grep, re.I) if a.grep else None; ok = 0
with open(os.path.join(a.out, 'index.jsonl'), 'a') as ix:
    for r in R:
        txt = r.pop('text', ''); ix.write(json.dumps(r) + '\n'); ok += r['status'] == 200
        print(r['status'], r.get('chars', ''), r.get('file', ''), r['url'][:100], '|', r.get('title', ''))
        if pat and txt:
            for m in list(pat.finditer(txt))[:5]: print('   ...' + txt[max(0, m.start() - 120):m.end() + 120].replace('\n', ' '))
dt_ = time.time() - t0; print(f'SUMMARY {len(R)} urls, ok {ok}, failed {len(R) - ok}, {dt_:.1f}s, {len(R) / max(dt_, 0.01):.1f} req/s')
