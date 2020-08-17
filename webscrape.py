import requests
import openpyxl
from bs4 import BeautifulSoup as soup
import re
import os
from dotenv import load_dotenv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

search_type = input('Would you like to search by query (q) or link (l)? ').lower().strip()
while not (search_type == 'q' or search_type == 'l'):
    print('Invalid input.')
    search_type = input('Would you like to search by query (q) or link (l)? ').lower().strip()
if search_type == 'q':
    query = input('What item would you like to search for on Newegg.com? ').lower().strip()
    search_url = f'https://www.newegg.com/p/pl?d={query}'
elif search_type == 'l':
    link = input('Please insert a Newegg.com initial link to scrape: ').lower().strip()
    while not 'newegg.com' in link:
        print('Invalid Newegg link.')
        link = input('Please insert a Newegg.com link to scrape: ').lower().strip()
    search_url = link


save_data = input('Would you like to save scraped data? (y or n)? ').lower().strip()
while not (save_data == 'y' or save_data == 'n'):
    print('Invalid input.')
    save_data = input('Would you like to save scraped data? (y or n)? ').lower().strip()
if save_data == 'y':
    is_data_saved = True
elif save_data == 'n':
    is_data_saved = False


unfound_data_string = 'Not found'


# Get response from desired Newegg URL
page_headers = {
    'authority': 'www.newegg.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
    'method': 'GET',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9'
}
initial_response = requests.get(search_url, headers=page_headers)
response_html = initial_response.text

# Parse HTML
initial_soup = soup(response_html, 'html.parser')


def solveCaptcha(soup_, url, max_retries=5):
    driver = webdriver.Chrome(executable_path='./chromedriver.exe')
    driver.get(url)
    time.sleep(2)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'g-recaptcha')))
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="";')
        print('Found Google ReCaptcha.')
    except:
        print('Not a valid Google ReCaptcha. Restarting browser.')
        driver.close()
        solveCaptcha(soup_=soup_, url=url)

    captcha_form_data = {
        'method': 'userrecaptcha',
        'googlekey': '6Ld0av8SAAAAAA_bWcLCPqT109QEfdRp0w50GCsq',
        'key': os.getenv('2CAPTCHA_API_KEY'),
        'pageurl': url,
        'json': 1
    }

    captcha_post_response = requests.post('https://2captcha.com/in.php', data=captcha_form_data).json()
    print(f'Sent captcha to be solved using sitekey ({captcha_form_data["googlekey"]}) '
          f'for {captcha_form_data["pageurl"]}.')

    captcha_get_parameters = {
        'key': os.getenv('2CAPTCHA_API_KEY'),
        'action': 'get',
        'id': captcha_post_response['request'],
        'json': 1
    }

    time.sleep(15)
    print(f'Getting Captcha Response for Request ID: {captcha_get_parameters["id"]}.')
    captcha_get_response = requests.get('https://2captcha.com/res.php', params=captcha_get_parameters).json()
    captcha_token = captcha_get_response['request']
    print(f'Captcha Token Status: {captcha_get_response["status"]}, Response: {captcha_token}')

    retries = 0
    while captcha_token == 'CAPCHA_NOT_READY':
        if retries >= max_retries:
            driver.close()
            solveCaptcha(soup_=soup_, url=url)
        time.sleep(5)
        print(f'Getting Captcha Response for Request ID: {captcha_get_parameters["id"]}.')
        captcha_get_response = requests.get('https://2captcha.com/res.php', params=captcha_get_parameters).json()
        captcha_token = captcha_get_response['request']
        print(f'Captcha Token Status: {captcha_get_response["status"]}, Response: {captcha_token}')
        retries += 1

    print('Submitting Captcha')
    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_token}";')
    driver.execute_script(f'reCAPTCHACallBack();')

    # time.sleep(3)
    print(driver.page_source)
    exit()

    return soup(driver.text, 'html.parser')


# Check for CAPTCHA
if 'Are you a human?' in initial_soup.text:
    print('CAPTCHA REQUIRED! Launching browser.')
    solveCaptcha(initial_soup, initial_response.url)

# Get number of pages for results
pages = initial_soup.find(class_='list-tool-pagination-text')
page_amount = 1
if pages is not None:
    page_amount = int(pages.text.split("/", 1)[1])
    print(f'Page Count: {page_amount}')


list_of_all_features = []
items = []

for page_number in range(1, page_amount + 1):
    amount_of_items_on_page = 0

    if 'ID-' in initial_response.url and page_number > 1:
        split_url = re.compile('(ID-[0-9]+)').split(initial_response.url)
        page_url = f'{split_url[0]}{split_url[1]}/Page-{page_number}'
    elif 'ID-' in initial_response.url and page_number == 1:
        page_url = f'{initial_response.url}'
    else:
        page_url = f'{initial_response.url}&page={page_number}'
    print(f'Scraping Page {page_number}/{page_amount}: {page_url}')

    # Get response from desired Newegg page URL
    page_response = requests.get(page_url, headers=page_headers)
    page_html = page_response.text


    # Parse HTML
    page_soup = soup(page_html, 'html.parser')

    # Check for CAPTCHA
    if 'Are you a human?' in page_soup.text:
        print('CAPTCHA REQUIRED! Launching browser.')
        page_soup = solveCaptcha(page_soup, page_response.url)

    # Get item containers
    containers = page_soup.find_all('div', class_='item-container')

    for container in containers:
        item_data = {}

        # Get brand of item from image link
        try:
            brand = container.find(class_='item-brand').img['title']
        except:
            brand = unfound_data_string
        finally:
            item_data['brand'] = brand

        # Get name and page url of item
        try:
            name = container.find(class_='item-title').text.replace('\n', ' | ').strip()
            item_url = container.find(class_='item-title')['href']
        except:
            name = unfound_data_string
            item_url = unfound_data_string
        finally:
            item_data['name'] = name
            item_data['url'] = item_url

        # Get list containing all item features
        try:
            feature_containers = container.find(class_='item-features').find_all('li')
            feature_list = {}
            for feature in feature_containers:
                feature_split = feature.text.replace('\n', ' | ').split(':', 1)
                feature_list[feature_split[0].strip()] = feature_split[1].strip()
                if feature_split[0].strip() not in list_of_all_features:
                    list_of_all_features.append(feature_split[0].strip())
        except:
            feature_list = {}
        finally:
            item_data['feature_list'] = feature_list

        # Check for item promotion
        try:
            item_promotion = container.find(class_='item-promo').text.replace('\n', ' | ').strip()
        except:
            item_promotion = unfound_data_string
        finally:
            item_data['item_promotion'] = item_promotion

        # Try to get item cost
        try:
            item_cost_tag = container.find(class_='price-current')
            item_cost_dollars = item_cost_tag.strong.text.replace('\n', ' | ').strip()
            item_cost_cents = item_cost_tag.sup.text.replace('\n', ' | ').strip()
            item_cost = f'${item_cost_dollars}{item_cost_cents}'
        except:
            item_cost = unfound_data_string
        finally:
            item_data['item_cost'] = item_cost

        # Check if item is shipped by newegg
        if container.find(class_='shipped-by-newegg') is not None:
            is_shipped_by_newegg = True
        else:
            is_shipped_by_newegg = False
        item_data['is_shipped_by_newegg'] = is_shipped_by_newegg

        # Get shipping cost of item
        try:
            shipping_cost = container.find(class_='price-ship').text.replace('\n', ' | ').strip()
        except:
            shipping_cost = unfound_data_string
        finally:
            item_data['shipping_cost'] = shipping_cost

        items.append(item_data)
        amount_of_items_on_page += 1
    print(f'Number of Items Found: {amount_of_items_on_page}')


for item in items:
    print(item)