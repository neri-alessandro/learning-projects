from lxml.html import fromstring
import requests
import csv
import time
import os
import re
import math
import json

base_uri = 'https://www.tripadvisor.com'
headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML,' \
        ' like Gecko) Chrome/83.0.4103.97 Safari/537.36 OPR/69.0.3686.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*' \
        ';q=0.8,application/signed-exchange;v=b3;q=0.9', 'authority': base_uri.split('://')[-1]
}


def prepare_param(action, city, page=None):
    #setting search filters for restaurents and next pages
    params = [
        ('Action', action), ('ajax', '1'), ('availSearchEnabled', 'false'), ('sortOrder', 'relevance'),
        ('geo', re.findall(r"-g([0-9]+)-", city.xpath('./@href')[0])[0]), ('itags', '10591'),
        ('cat', '10651,20065,20064,10746,20075,10669,10654,10671,10683,10668,10648,4617,10639,' \
                '10649,20062,20074,20076,10345,20066,10682'), ('zfp', '10598,10599,10862'),
    ]
    
    if action != 'FILTER':
        params.append(('o', 'a{0}'.format(page)))
    
    return tuple(params)


def get_listing(listings, count=0):
    for listing in listings:
        #looping through restaurent links, if email is found we continue otherwise we skip onto next result right away
        tree = fromstring(requests.get(base_uri+listing, headers=headers).text)
        try: email = tree.xpath('//a[contains(@href, "mailto:")]/@href')[0].replace('mailto:', '').split('?')[0]
        except: continue
        
        ###FETCHING ALL REQUIRED ATTRIBUTES FROM JSON AND HTML RESPONSE
        count += 1
        scriptJson = json.loads(tree.xpath('//script[contains(text(), "@context") and contains(text(), "addressCountry")]/text()')[0])
        title = tree.xpath('//h1[@data-test-target="top-info-header"]/text()')[0]
        try: priceRange = scriptJson["priceRange"]
        except:
            try: priceRange = tree.xpath('//a[@class="_2mn01bsa" and contains(text(), "$")]/text()')[0]
            except: priceRange = ''
        try: ratings = scriptJson["aggregateRating"]["ratingValue"]
        except: ratings = 0
        try: total_comments = scriptJson["aggregateRating"]["reviewCount"]
        except: total_comments = 0
        categories = ', '.join(tree.xpath('//a[@class="_2mn01bsa" and not(contains(text(), "$"))]/text()'))
        try: phone = tree.xpath('//a[contains(@href, "tel:")]/@href')[0].replace('tel:', '')
        except: phone = ''
        address = tree.xpath('//a[@href="#MAPVIEW"]/text()')[0]
        
        #dumping data in csv file and flushing it for quick write
        with open('output.csv', 'a+', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter=',')
            writer.writerow([title, priceRange, email, ratings, total_comments, categories, phone, address, base_uri+listing])
            outfile.flush()
        
        #time.sleep(5)
        print("Restaurant({0}) ==> {1}".format(str(count).zfill(3), title))
        if count == 100:
            return count
    
    return count


def main(uri):
    #Accessing the main url and fetching city links
    tree = fromstring(requests.get(uri, headers=headers).text)
    cities = tree.xpath('//div[@class="geos_row"]/div[@class="geo_wrap"]//div[@class="geo_name"]/a')
    
    #Creating file with w+ mode and adding headers
    with open('output.csv', 'w+', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=',')
        writer.writerow(['Title', 'Price Range', 'Email', 'Ratings', 'Number of Comments', 'Categories', 'Phone', 'Address', 'Link'])
    
    #lopping through each city
    for _, city in enumerate(cities):
        city_name = city.xpath('./text()')[0]
        print("***City({0})*** ==> {1}".format(str(_+1).zfill(3), city_name))
        
        #fetching all restaurent links and paginating,
        #this logic works in sync with get_listing() method,
        #it continues getting new pages until we reach
        #the last page or we scrap 100 restaurents with email
        headers['referer'] = base_uri + city.xpath('./@href')[0]
        params = prepare_param('FILTER', city)
        tree = fromstring(requests.get(base_uri+'/RestaurantSearch', headers=headers, params=params).text)
        listings = tree.xpath('//div[contains(@data-test, "_list_item") and not(@data-test="SL_list_item")]/span/div/div/span/a/@href')
        count = get_listing(listings)
        
        if len(listings) == 30:
            i = 2
            
            #paginating until condition is correct to stop the loop
            while True:
                params = prepare_param('PAGE', city, page='{0}'.format((i-1)*30))
                tree = fromstring(requests.get(base_uri+'/RestaurantSearch', headers=headers, params=params).text)
                listings = tree.xpath('//div[contains(@data-test, "_list_item") and not(@data-test="SL_list_item")]/span/div/div/span/a/@href')
                count = get_listing(listings, count=count)
                #time.sleep(2)
                
                #condition continue until we reach 100 listins with email or all listings are exhuasted per city
                i += 1
                if count >= 100 or len(listings) == 0:
                    break
        #time.sleep(2)
        print()


if __name__ == '__main__':
    main('https://www.tripadvisor.com/Restaurants-g188553-The_Netherlands.html')
