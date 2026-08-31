import requests, re, urllib.parse
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://weixin.sogou.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}
s = requests.Session()
s.headers.update(headers)
q='爱范儿 ifanr'
url = f'https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(q)}&ie=utf8'
print('GET search', url)
r = s.get(url, timeout=10)
print('search status', r.status_code)
soup = BeautifulSoup(r.text, 'lxml')
a = soup.select_one('ul.news-list li h3 a')
href = a.get('href')
print('href', href[:200])
sogou_url = 'https://weixin.sogou.com' + href
print('sogou_url', sogou_url[:200])
r2 = s.get(sogou_url, timeout=10, allow_redirects=True)
print('r2 url', r2.url[:200])
print('r2 status', r2.status_code)
# save html
open('C:/Users/ADMINI~1/AppData/Local/Temp/antispider.html','w',encoding='utf-8').write(r2.text)
print('html len', len(r2.text))
print('contains url +=', 'url +=' in r2.text)
parts = re.findall(r"url\s*\+=\s*['\"]([^'\"]+)['\"]", r2.text)
print('parts count', len(parts))
print('parts', parts[:10])
constructed = "".join(parts)
print('constructed', constructed[:200])
print('contains mp?', 'mp.weixin.qq.com' in constructed)
# also try direct regex for mp
m = re.search(r"https://mp\.weixin\.qq\.com[^\s'\"<>]+", r2.text)
print('direct m', m.group(0)[:200] if m else None)
# try find all https mp
all_m = re.findall(r"https://mp\.weixin\.qq\.com[^\s'\"<>]+", r2.text)
print('all_m', all_m[:2])
