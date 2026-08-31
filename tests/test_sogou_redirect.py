import requests, urllib.parse
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://weixin.sogou.com/weixin?type=2&query=%E7%88%B1%E8%8C%83%E5%84%BF%20ifanr&ie=utf8',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}
s = requests.Session()
s.headers.update(headers)
q='爱范儿 ifanr'
url = f'https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(q)}&ie=utf8'
print('GET search')
r = s.get(url, timeout=10)
print('search status', r.status_code)
soup = BeautifulSoup(r.text, 'lxml')
a = soup.select_one('ul.news-list li h3 a')
href = a.get('href') if a else None
print('href', href[:200] if href else 'none')
if href:
    sogou_url = 'https://weixin.sogou.com' + href
    print('sogou_url', sogou_url[:200])
    # Try with allow_redirects=False
    r2 = s.get(sogou_url, headers=headers, allow_redirects=False, timeout=10)
    print('r2 status', r2.status_code)
    print('r2 headers', dict(r2.headers))
    print('Location', r2.headers.get('Location','')[:500])
    print('r2 text snippet', r2.text[:1000])
    # Try with allow_redirects True but fresh session without cookies
    s2 = requests.Session()
    s2.headers.update(headers)
    r3 = s2.get(sogou_url, allow_redirects=True, timeout=10)
    print('r3 url', r3.url[:200])
    print('r3 status', r3.status_code)
    print('r3 snippet', r3.text[:800])
