import requests
from bs4 import BeautifulSoup
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r=requests.get('https://www.ifanr.com', headers=headers, timeout=10)
print('status', r.status_code)
soup=BeautifulSoup(r.text,'lxml')
# Find article links
# Ifanr homepage has article list with class maybe
links=[]
for a in soup.select('a[href*="ifanr.com/"]'):
    href=a.get('href')
    text=a.get_text(strip=True)
    if href and text and len(text)>5 and 'ifanr.com' in href and href.count('/')>3:
        # filter
        if any(x in href for x in ['/category/','/author/','/tag/','javascript']):
            continue
        links.append((text, href))
        if len(links)>10:
            break
print('found', len(links))
for t,h in links[:5]:
    print(t[:40], h[:80])

# Try fetch one article
if links:
    t,h = links[0]
    print('\nfetch', h)
    r2=requests.get(h, headers=headers, timeout=10)
    print('r2', r2.status_code, len(r2.text))
    soup2=BeautifulSoup(r2.text,'lxml')
    # Try find content
    for sel in ['article', '.article-content', '.content', '#content', '.post-content', '.entry-content']:
        el=soup2.select_one(sel)
        if el:
            print('found', sel, len(el.get_text()))
            # find images
            imgs=el.find_all('img')
            print('imgs', len(imgs))
            for img in imgs[:3]:
                src=img.get('src') or img.get('data-src')
                print('img src', src[:80] if src else 'none')
            break
    print('title', soup2.title.get_text(strip=True)[:60] if soup2.title else 'none')
