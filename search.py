import sys, json, re, html, argparse, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
ap = argparse.ArgumentParser(); ap.add_argument('queries', nargs='+'); ap.add_argument('--src', default='openalex,arxiv,wikipedia'); ap.add_argument('--n', type=int, default=8)
a = ap.parse_args()
def jget(u):
    import time
    for k in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'research-search'}), timeout=25).read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and k < 3: time.sleep(4 * (k + 1)); continue
            raise
def openalex(q):
    for w in jget('https://api.openalex.org/works?search=' + urllib.parse.quote(q) + f'&per-page={a.n}')['results']:
        ab = w.get('abstract_inverted_index') or {}; pos = sorted((p, k) for k, v in ab.items() for p in v)
        yield {'title': w['title'], 'year': w.get('publication_year'), 'cites': w.get('cited_by_count'), 'url': w.get('doi') or w['id'], 'abs': ' '.join(k for _, k in pos)[:300]}
def arxiv(q):
    x = urllib.request.urlopen('http://export.arxiv.org/api/query?search_query=all:' + urllib.parse.quote(q) + f'&max_results={a.n}', timeout=25).read().decode()
    for e in re.findall(r'<entry>.*?</entry>', x, re.S):
        g = lambda t: re.sub(r'\s+', ' ', re.search(f'<{t}>(.*?)</{t}>', e, re.S).group(1)).strip()
        yield {'title': g('title'), 'year': g('published')[:4], 'url': g('id'), 'abs': g('summary')[:300]}
def wikipedia(q):
    for r in jget('https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=' + str(a.n) + '&srsearch=' + urllib.parse.quote(q))['query']['search']:
        yield {'title': r['title'], 'url': 'https://en.wikipedia.org/wiki/' + r['title'].replace(' ', '_'), 'abs': html.unescape(re.sub('<[^>]+>', '', r['snippet']))[:300]}
def semantic(q):
    for p in jget('https://api.semanticscholar.org/graph/v1/paper/search?fields=title,year,citationCount,abstract,url&limit=' + str(a.n) + '&query=' + urllib.parse.quote(q)).get('data', []):
        yield {'title': p['title'], 'year': p.get('year'), 'cites': p.get('citationCount'), 'url': p.get('url'), 'abs': (p.get('abstract') or '')[:300]}
B = {'openalex': openalex, 'arxiv': arxiv, 'wikipedia': wikipedia, 'semantic': semantic}
def job(qs):
    q, s = qs
    try: return [dict(src=s, q=q, **r) for r in B[s](q)]
    except Exception as e: return [{'src': s, 'q': q, 'error': str(e)[:80]}]
with ThreadPoolExecutor(16) as ex:
    for res in ex.map(job, [(q, s) for q in a.queries for s in a.src.split(',')]):
        for r in res: print(json.dumps(r, ensure_ascii=False))
