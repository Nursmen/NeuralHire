# Here we go. We got to parse jobs from
# SuperJob.ru
# It is russian site, but whatever. 
# I wrote it from scratch so I think it is amazing 🫠.

import csv
import requests
from bs4 import BeautifulSoup
import re

def camel_case_split(str):
    words = [[str[0]]]

    for c in str[1:]:
        if words[-1][-1].islower() and c.isupper():
            words.append(list(c))
        else:
            words[-1].append(c)

    return [''.join(word) for word in words]

# Make a request to the website
# There are 55 jobs on one page
urls = ['https://russia.superjob.ru/vacancy/search/?keywords=python', 'https://russia.superjob.ru/vacancy/search/?keywords=python&page=2', 'https://www.superjob.ru/vacancy/search/?keywords=data%20science&noGeo=1'
        , 'https://www.superjob.ru/vacancy/search/?keywords=js&noGeo=1', 'https://www.superjob.ru/vacancy/search/?keywords=js&noGeo=1&page=2']
jobs = []
for url in urls:
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract the desired data
    for job in soup.find_all('div', {'class': 'f-test-search-result-item'}):
        try:
            title = job.find('a').text
            print(title)
        except:
            continue

        # money = re.findall(r'\d+', job.find('span', {'class':'_2eYAG _3xCPT rygxv _17lam _3GtUQ'}).text)
        
        try:
            money = job.find('div', {'class':'f-test-text-company-item-salary'}).text
            print('money:', money)
        except:
            continue

        city = job.find('span', {'class':'_94I1l f-test-text-vacancy-item-company-name _2xwe3 _3ixqx _3uDFj _2KByL _2wD_q'}).find('div', {'class':'V4aa2'}).text
        knoladge_temp = job.find_all('span')

        for i in knoladge_temp:
            if len(i.text) > 100:
                knoladge = i.text        
        knoladge = "".join(re.split(r"[^a-zA-Z\s]*", knoladge))
        knoladge = " ".join(knoladge.split()).upper() 

        company = job.find('div', {'class':'_1d4Tz _2hVr3 _3aFAO _2hnju'})
        if company:
            company = company.text
        else:
            company = ''

        addition = job.find('div', {'class':'_5RkIk _3MV7d _28VU-'})
        if addition:
            addition = camel_case_split(addition.text)
        else:
            addition = ''

        link = job.find('a')['href']
        jobs.append({'title': title, 'money':money[0] if len(money) > 0 else '','knoladge':knoladge,'company':company,'addition':addition,'city':city, 'link': url+link})

# Write the data to a CSV file
with open('jobs.csv', 'w',encoding='utf8',newline='') as csvfile:
    fieldnames = ['title','money','knoladge','company','addition','city','link']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for job in jobs:
        writer.writerow(job)