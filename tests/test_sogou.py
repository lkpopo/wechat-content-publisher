import requests
from bs4 import BeautifulSoup
import re, urllib.parse

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://weixin.sogou.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}
s = requests.Session()
s.headers.update(headers)
q='爱范儿 ifanr'
url = f'https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(q)}&ie=utf8'
print('GET', url)
r = s.get(url, timeout=10)
print('status', r.status_code, 'cookies', s.cookies.get_dict())
soup = BeautifulSoup(r.text, 'lxml')
a = soup.select_one('ul.news-list li h3 a')
if a:
    href = a.get('href')
    print('href', href[:200])
    sogou_url = 'https://weixin.sogou.com' + href if href.startswith('/') else href
    print('sogou_url', sogou_url[:200])
    r2 = s.get(sogou_url, headers=headers, allow_redirects=True, timeout=10)
    print('r2 url', r2.url[:200])
    print('r2 status', r2.status_code)
    print('contains mp?', 'mp.weixin.qq.com' in r2.text)
    print('snippet', r2.text[:800])
    if 'antispider' in r2.url:
        print('antispider in url')
    m = re.search(r'url\s*=\s*["\'](https://mp\.weixin\.qq\.com[^"\']+)["\']', r2.text)
    if m:
        print('found js url', m.group(1)[:200])
