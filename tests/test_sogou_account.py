import requests, urllib.parse, re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://weixin.sogou.com/',
}
s = requests.Session()
s.headers.update(headers)
q='爱范儿'
url = f'https://weixin.sogou.com/weixin?type=1&query={urllib.parse.quote(q)}&ie=utf8'
print('GET', url)
r = s.get(url, timeout=10)
print('status', r.status_code)
# save
open('C:/Users/ADMINI~1/AppData/Local/Temp/sogou_account.html','w',encoding='utf-8').write(r.text)
print('len', len(r.text))
soup = BeautifulSoup(r.text, 'lxml')
# try find account link
# Sogou account result has .news-box .txt-box
a = soup.select_one('.news-box .txt-box a')
if a:
    print('found', a.get_text(strip=True), a.get('href')[:120])
else:
    print('not found txt-box a')
    print(r.text[:2000])
# also try other selectors
print('selectors', [c.get_text(strip=True)[:30] for c in soup.select('.news-box')[:2]])
