import concurrent.futures
from src.utils.base.libraries import logging, cloudscraper, requests, os, threading, json
from src.utils.base.basic import Error
from src.utils.base.constants import LIST_OF_SKIP_CODES
from src.scraping.parsing import parse_html


class WebScraper:
    def __init__(self, output_dir, num_workers=None, do_parse_html=True):
        self.max_workers = min(os.cpu_count() or 1, num_workers)
        self.proxies_lock = threading.Lock()  # Lock for accessing the proxies list
        self.urls_lock = threading.Lock()  # Lock for accessing the URLs list
        self.do_parse_html = do_parse_html
        self.output_dir = output_dir

    @staticmethod
    def save_as_json(data, filename):
        try:
            with open(filename, 'w') as json_file:
                json.dump(data, json_file, indent=4)
        except Exception as e:
            logging.error(f"Error occurred while saving data to {filename} with error {e}")


    @staticmethod
    def generate_proxy_url(username, password, ip, port):
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        return proxies

    @staticmethod
    def get_data(url: str, proxies: dict):
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, proxies=proxies)
            if response.status_code == 200:
                original_url = f"<!-- Original URL: {url} -->"
                data = original_url + "\n" + response.text
                return data

            elif response.status_code in LIST_OF_SKIP_CODES:
                # TODO: add this to user logs
                logging.info(f"Skipping {url} with proxy {proxies}")
                return f"Encountered Skip Status Code of {response.status_code} So, Skipping This URL {url}"
            else:
                # TODO: add this to user logs
                logging.info(
                    f"Some error occurred for {url} with proxy {proxies} with status code {response.status_code}")
                return Error(code=response.status_code,
                             message=f"Some error occurred for {url} with proxy {proxies} with status code {response.status_code}")

        except requests.exceptions.RequestException:
            # TODO: add this to user logs
            logging.error(f"Request Exception occurred for {url} with proxy {proxies}")
            return Error(code=500, message=f"Request Exception occurred for {url} with proxy {proxies}")

    def process_url(self, url: str, proxies: list):
        data = None
        for proxy in proxies:
            ip, port, username, password = proxy.split(':')
            proxy_data = self.generate_proxy_url(username, password, ip, port)
            data = self.get_data(url, proxy_data)
            if not isinstance(data, Error):
                break  # If data is not an error, we have successfully retrieved the data
        return data
    

    def _post_process_data(self, data, url):
        result = {"url": url, "data": data}
        if self.do_parse_html:
            result["parsed_data"] = parse_html(url=url, html_text=data)
        
        # with the data save it to a file
        file_name = url.replace("/", "_") + ".json"
        file_name = os.path.join(self.output_dir, file_name)
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        self.save_as_json(result, file_name)



    def scrape_urls(self, urls: list, proxies_list: list):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for url in urls:
                future = executor.submit(self.process_url, url, proxies_list)
                futures.append(future)

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                url = urls[i]
                data = future.result()
                # If the data is not an error, we have successfully retrieved the data
                if not isinstance(data, Error):
                    self._post_process_data(data, url)



# Usage Example:
if __name__ == "__main__":
    # Initialize the WebScraper class with the desired number of workers
    scraper = WebScraper(num_workers=1, output_dir="output/new/", do_parse_html=True)

    data_1 = {
  "urls": [
    "https://quickbooks.intuit.com/accountants/resources/marketing-hub/video/create-social-media-content/",
    "https://quickbooks.intuit.com/time-tracking/resources/affordable-care-act-benefits/",
    "https://quickbooks.intuit.com/desktop/enterprise/payroll-and-payments/",
    "https://quickbooks.intuit.com/time-tracking/resources/rotating-shifts/",
    "https://quickbooks.intuit.com/time-tracking/remote-employees/",
    "https://quickbooks.intuit.com/time-tracking/gps-survey/2019-survey/",
    "https://quickbooks.intuit.com/payroll/healthcare/",
    "https://quickbooks.intuit.com/time-tracking/resources/guide-to-employee-time-tracking/",
    "https://quickbooks.intuit.com/accountants/news-community/",
    "https://quickbooks.intuit.com/accounting/inventory/",
    "https://quickbooks.intuit.com/cas/dam/DOCUMENT/A6ZsJ3mwX/Social-Media-Guide_Facebook-LinkedIn-and-Twitter.pdf/",
    "https://quickbooks.intuit.com/cas/dam/DOCUMENT/A89VmPpDg/QuickBooks-Desktop-to-Online-Conversion-Checklist.pdf/",
    "https://quickbooks.intuit.com/desktop/enterprise/resources/switch-to-enterprise/diamond/",
    "https://quickbooks.intuit.com/time-tracking/app-marketplace/knowify/",
    "https://quickbooks.intuit.com/time-tracking/flsa/working-off-the-clock/",
    "https://quickbooks.intuit.com/desktop/enterprise/industry-solutions/",
    "https://quickbooks.intuit.com/time-tracking/flsa/overtime-pay-rules/",
    "https://quickbooks.intuit.com/online/advanced/resources/forrester-tei-report-2022/",
    "https://quickbooks.intuit.com/cas/dam/DOCUMENT/A6IblY07m/Changes-to-Workers-Compensation-Tracking-during-COVID.pdf/",
    "https://quickbooks.intuit.com/desktop/enterprise/resources/faq/",
    "https://quickbooks.intuit.com/time-tracking/time-card-payroll-reports/",
    "https://quickbooks.intuit.com/accountants/resources/marketing-hub/article/how-to-identify-connect-and-get-referrals/",
    "https://quickbooks.intuit.com/time-tracking/non-profit/",
    "https://quickbooks.intuit.com/payroll/manufacturing/"
],
  "proxies": ["216.19.217.132:6372:olmjtxsz:yccmlx17olxs",
"134.73.64.103:6388:olmjtxsz:yccmlx17olxs",
"107.181.143.40:6171:olmjtxsz:yccmlx17olxs",
"184.174.24.212:6788:olmjtxsz:yccmlx17olxs",
"216.173.120.131:6423:olmjtxsz:yccmlx17olxs",
"154.92.112.84:5105:olmjtxsz:yccmlx17olxs",
"64.137.57.144:6153:olmjtxsz:yccmlx17olxs",
"184.174.46.130:5759:olmjtxsz:yccmlx17olxs",
"184.174.126.249:6541:olmjtxsz:yccmlx17olxs",
"188.74.168.200:5241:olmjtxsz:yccmlx17olxs",
"216.173.75.53:6354:olmjtxsz:yccmlx17olxs",
"198.105.101.140:5769:olmjtxsz:yccmlx17olxs",
"38.153.152.181:9531:olmjtxsz:yccmlx17olxs",
"104.239.81.95:6630:olmjtxsz:yccmlx17olxs",
"38.154.224.19:6560:olmjtxsz:yccmlx17olxs",
"103.53.219.17:6110:olmjtxsz:yccmlx17olxs",
"38.154.191.20:8597:olmjtxsz:yccmlx17olxs",
"104.223.157.49:6288:olmjtxsz:yccmlx17olxs",
"104.143.252.223:5837:olmjtxsz:yccmlx17olxs",
"104.239.13.14:6643:olmjtxsz:yccmlx17olxs",
"104.239.91.144:5868:olmjtxsz:yccmlx17olxs",
"45.192.136.127:5421:olmjtxsz:yccmlx17olxs",
"104.239.84.51:6086:olmjtxsz:yccmlx17olxs",
"64.137.60.156:5220:olmjtxsz:yccmlx17olxs",
"136.0.109.9:5603:olmjtxsz:yccmlx17olxs",
"104.239.3.92:6052:olmjtxsz:yccmlx17olxs",
"45.56.175.227:5901:olmjtxsz:yccmlx17olxs",
"161.123.152.124:6369:olmjtxsz:yccmlx17olxs",
"192.210.132.204:6174:olmjtxsz:yccmlx17olxs",
"216.173.75.153:6454:olmjtxsz:yccmlx17olxs",
"107.179.60.64:5096:olmjtxsz:yccmlx17olxs",
"45.41.177.24:5674:olmjtxsz:yccmlx17olxs",
"45.192.145.10:5352:olmjtxsz:yccmlx17olxs",
"198.144.190.110:5957:olmjtxsz:yccmlx17olxs",
"104.239.73.146:6689:olmjtxsz:yccmlx17olxs",
"107.179.26.234:6304:olmjtxsz:yccmlx17olxs",
"154.95.36.164:6858:olmjtxsz:yccmlx17olxs",
"38.154.217.181:7372:olmjtxsz:yccmlx17olxs"]
}

    # List of URLs to scrape
    urls_to_scrape = data_1['urls']

    # List of proxy information in the format: "ip:port:username:password"
    proxies = data_1['proxies']

    # Start scraping
    scraper.scrape_urls(urls_to_scrape, proxies)
