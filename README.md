# Newegg Web Scraper
This is a custom web scraper for scraping Newegg via a link or query term

# Features
- Search the Newegg site via a query (search term)
- Search the Newegg site via a link
- Allows you to cycle through any number of pages found through query/link
- Allows saving data to a .xlsx file
- Auto solve Google captcha if detected when you follow below instructions:
    - Create a 2CAPTCHA account
    - Load the account with some money
    - Save the API key
    - Create a .env file in the root directory of this project and paste the following with your API key:
        - ```2CAPTCHA_API_KEY=<INSERT 2CAPTCHA API KEY HERE>```
