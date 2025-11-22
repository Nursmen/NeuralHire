# Here we go. We got to parse jobs from
# SuperJob.ru
# It is russian site, but whatever. 
# I wrote it from scratch so I think it is amazing 🫠.

import csv
import requests
from bs4 import BeautifulSoup
import re
import time

def camel_case_split(s):
    words = [[s[0]]]
    for c in s[1:]:
        if words[-1][-1].islower() and c.isupper():
            words.append([c])
        else:
            words[-1].append(c)
    return [''.join(word) for word in words]
baseurl = 'https://russia.superjob.ru/'
urls = [f"https://russia.superjob.ru/vacancy/search/?page={i}" for i in range(1, 51)]

jobs = []
fieldnames = ['title','money','knoladge','company','addition','city','link']

with open('jobs.csv', 'w', encoding='utf8', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/50] Fetching: {url}")
        try:
            response = requests.get(url, timeout=10)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        found = 0
        for job in soup.find_all('div', {'class': 'f-test-search-result-item'}):
            try:
                title = job.find('a').text
            except:
                continue
            try:
                money = job.find('span', {'class':'kk-+S _1wD2J _3ixqx _3uDFj _2KByL'}).text
                if 'По договорённости' in money:
                    money = ['По договорённости']
                else:
                    old_money = re.findall(r'\d+', money)
                    money = []
                    for i in range(len(old_money)):
                        old_money[i] = int(old_money[i])
                        if old_money[i] > 0 and old_money[i] < 10000000:
                            money.append(old_money[i])
            except:
                money = []
            try:
                city = job.find('span', {'class':'wDNBJ _3ixqx _3uDFj _2KByL'}).text
            except:
                city = ''

            knoladge = ''
            for i in job.find_all('span', {'class':'wDNBJ _3ixqx _3uDFj _2KByL _2wD_q'}):
                # if len(i.text) > 100:
                knoladge = i.text
            knoladge = "".join(re.split(r"[^a-zA-Z\s]*", knoladge))
            knoladge = " ".join(knoladge.split()).upper()
            company = job.find('span', {'class':'_94I1l f-test-text-vacancy-item-company-name _2xwe3 _3ixqx _3uDFj _2KByL _2wD_q'})
            company = company.text if company else ''
            addition = job.find('div', {'class':'_1Zv0C EI3kW _1B3_w'})
            addition = camel_case_split(addition.text) if addition else ''
            link = job.find('a')['href']
            job_data = {
                'title': title,
                'money': (money[0] if money[0] == 'По договорённости' else (sum(money) / len(money))) if money else '',
                'knoladge': knoladge,
                'company': company,
                'addition': addition,
                'city': city,
                'link': baseurl + link
            }
            writer.writerow(job_data)
            jobs.append(job_data)
            found += 1

        print(f"  -> Found {found} jobs")
        time.sleep(1)

print(f"\nDone. Total jobs collected: {len(jobs)}. Saved to jobs.csv.")