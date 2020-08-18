import os
import requests
import time
from bs4 import BeautifulSoup as soup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()
captcha_attempts = 0


def solve_captcha(soup_, url, max_retries=15):
    # Check for 2Captcha API key
    captcha_api_key = os.getenv('2CAPTCHA_API_KEY')
    if (captcha_api_key is None) or (captcha_api_key == ""):
        captcha_api_key = input('2Captcha API key not found. Please input your API key now: ').strip()
        # exit('Please enter your 2CAPTCHA_API_KEY in a .env file')

    # Check for how many calls made for this specific captcha and terminate if failed too many times
    global captcha_attempts
    if captcha_attempts > 5:
        exit('Captcha failed too many times. Please check your 2Captcha API Key or the 2Captcha service.')

    # Run Chrome selenium in headless mode
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(executable_path='./chromedriver.exe', options=options)
    driver.get(url)

    # Check for Google ReCaptcha (if valid, continue; if not Google ReCaptcha, close browser and restart)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'g-recaptcha')))
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="";')
        print('\tFound Google ReCaptcha.')
    except:
        print('\tNot a valid Google ReCaptcha. Restarting browser.')
        driver.close()
        solve_captcha(soup_=soup_, url=url)

    # Required form data to utilize 2Captcha API
    captcha_form_data = {
        'method': 'userrecaptcha',
        'googlekey': '6Ld0av8SAAAAAA_bWcLCPqT109QEfdRp0w50GCsq',
        'key': captcha_api_key,
        'pageurl': url,
        'json': 1
    }

    # Submit captcha solve request
    captcha_post_response = requests.post('https://2captcha.com/in.php', data=captcha_form_data).json()

    # Check for any 2Captcha errors in request
    error_key_words = ['ERROR', 'IP_BANNED', 'MAX_USER_TURN']
    for error in error_key_words:
        if error in captcha_post_response['request']:
            exit(f'CAPTCHA NOT SUBMITTED ERROR: {captcha_post_response["request"]}')

    print(f'\tSent captcha to be solved using sitekey ({captcha_form_data["googlekey"]}) '
          f'for {captcha_form_data["pageurl"]}.')

    # Required parameters for get request on submitted captcha through 2Captcha API
    captcha_get_parameters = {
        'key': captcha_api_key,
        'action': 'get',
        'id': captcha_post_response['request'],
        'json': 1
    }

    # Wait 15 seconds before checking for completed captcha
    time.sleep(15)
    print(f'\tGetting Captcha Response for Request ID: {captcha_get_parameters["id"]}.')
    captcha_get_response = requests.get('https://2captcha.com/res.php', params=captcha_get_parameters).json()
    captcha_token = captcha_get_response['request']

    # Check for any 2Captcha errors in request
    for error in error_key_words:
        if error in captcha_token:
            exit(f'CAPTCHA NOT SUBMITTED ERROR: {captcha_token}')

    print(f'\t\tCaptcha Token Status: {captcha_get_response["status"]}, Response: {captcha_token}')

    # Time out captcha and restart if not ready after max_retries amount
    retries = 0
    while captcha_token == 'CAPCHA_NOT_READY':
        if retries >= max_retries:
            print('\tCaptcha timed out, retrying.')
            driver.close()
            captcha_attempts += 1
            solve_captcha(soup_=soup_, url=url)
        time.sleep(5)
        retries += 1
        print(f'\tRetry #{retries}/{max_retries}. Getting Captcha Response for Request ID: {captcha_get_parameters["id"]}.')
        captcha_get_response = requests.get('https://2captcha.com/res.php', params=captcha_get_parameters).json()
        captcha_token = captcha_get_response['request']
        print(f'\t\tCaptcha Token Status: {captcha_get_response["status"]}, Response: {captcha_token}')

    # Submit captcha
    print('\tSubmitting Captcha')
    captcha_attempts = 0
    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_token}";')
    driver.execute_script(f'reCAPTCHACallBack();')

    # Wait for new page to load and return source of page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'item-container')))
    page_source = driver.page_source
    driver.close()
    return soup(page_source, 'html.parser')
