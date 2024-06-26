from src.utils.base.libraries import webdriver, Options, os, WebDriverWait, EC, By, time, Lock, cycle, json
from src.scraping.parsing import parse_html
import concurrent.futures



class JsWebScraper:
    def __init__(self, url, proxy_list, file_path, chrome_args=None, sleep_time=5, retries=3):
        self.url = url
        self.file_path = file_path
        self.proxy_list = cycle(proxy_list)
        self.chrome_args = chrome_args if chrome_args else []
        self.sleep_time = sleep_time
        self.retries = retries
        self.lock = Lock()
        self.init_driver_and_load_page()

    def init_driver_and_load_page(self):
        attempts = 0
        empty_html = "<html><head></head><body></body></html>"
        while attempts < self.retries:
            try:
                self.driver = self.init_driver()
                self.driver.get(self.url)
                WebDriverWait(self.driver, self.sleep_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                self.page_source = self.driver.page_source
                if self.page_source == empty_html:
                    raise Exception("Page source is empty, so retry with new proxy")
                return
            except Exception as e:
                attempts += 1
                # TODO: Add to user logs
                self.driver.quit()
                if attempts >= self.retries:
                    raise Exception("Max retries reached, could not initialize driver or load the page")

    def init_driver(self):
        chrome_options = self.get_chrome_options()
        seleniumwire_options = self.get_seleniumwire_options(next(self.proxy_list))
        return webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)

    def get_chrome_options(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--log-level=OFF')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--no-sandbox')

        # Disable user data directory
        chrome_options.add_argument('--no-default-browser-check')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--disable-translate')
        for arg in self.chrome_args:
            chrome_options.add_argument(arg)
        return chrome_options

    def get_seleniumwire_options(self, proxy_details):
        ip, port, username, password = proxy_details
        return {
            'proxy': {
                'http': f'http://{username}:{password}@{ip}:{port}',
                'https': f'https://{username}:{password}@{ip}:{port}',
                'no_proxy': 'localhost,127.0.0.1'
            }
        }

    def fetch_page(self, do_parse_html=False):
        file_name = self.url.replace('https://', '').replace('http://', '').replace('/', '_')
        file_path = os.path.join(self.file_path, f'{file_name}.json')
        original_url = f"<!-- Original URL: {self.url} -->"
        data = original_url + "\n" + self.page_source
        parsed_data = "No parsed data"
        if do_parse_html:
            parsed_data = parse_html(url=self.url , html_text=data , remove_header_footer=True)
        data_to_save = {
            "raw": data,
            "parsed": parsed_data,
            "original_url": self.url,
            "status": "success"
        }
        with self.lock:
            with open(file_path, 'w') as f:
                f.write(json.dumps(data_to_save))
        return "success"

    def delay(self, delay_time):
        # max delay time is 10 seconds
        delay_time = min(delay_time, 10)
        time.sleep(delay_time)

    def scroll_to_bottom(self, do_smooth=False):
        if do_smooth:
            total_height = int(self.driver.execute_script("return document.body.scrollHeight"))
            for i in range(1, total_height, 5):  # Change 5 to a smaller number for smoother scrolling
                self.driver.execute_script(f"window.scrollTo(0, {i});")
                self.delay(0.05)
        else:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def execute_js(self, script):
        return self.driver.execute_script(script)

    def click_element(self, css_selector):
        button = self.driver.find_element_by_css_selector(css_selector)
        button.click()

    def fill_form(self, css_selector, value):
        input_field = self.driver.find_element_by_css_selector(css_selector)
        input_field.send_keys(value)

    def take_screenshot(self, path):
        with self.lock:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.driver.save_screenshot(path)

    def quit(self) -> None:
        self.driver.quit()

    def run(self, run_config) -> dict:
        results = {}
        for config in run_config:
            method = getattr(self, config['method'])
            results[config['method']] = method(**config['args'])
        
        return results


def run_single_js_scraper(config: list):
    """Using Config dict run the scraper for one URL"""
    try:
        config_init = config[0]
        scraper = JsWebScraper(
            url=config_init['args']['url'],
            proxy_list=config_init['args']['proxy_list'],
            chrome_args=config_init['args'].get('chrome_args', []),
            file_path=config_init['args']['file_path']
        )
        next_to_run = config[1:]
        return scraper.run(next_to_run)
    except Exception as e:
        return {"Error": e}



def run_parallel_scraping(all_configs: list, max_workers: int=20):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for each_config in all_configs:
            future = executor.submit(run_single_js_scraper, each_config)
            futures.append(future)

        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                results[i] = future.result()
            except Exception as e:
                results[i] = str(e)

    return results


class JsScraping:
    def __init__(self, urls: list, proxies: list, do_parse_html: bool, max_workers: int, output_dir: str):
        self.urls = urls
        self.proxies = proxies
        self.do_parse_html = do_parse_html
        self.max_workers = max_workers
        self.output_dir = output_dir
        self.proxies_list = []  # Prossible proxies to use

    def _parse_proxies(self):
        # parse the proxy list to make it suitable for the scraper
        for proxy in self.proxies:
            ip, port, username, password = proxy.split(':')
            self.proxies_list.append((ip, port, username, password))

    def _make_configs(self):
        make_config = lambda url: [
            {
                "method": "__init__",
                "args": {
                    "url": url,
                    "proxy_list": self.proxies_list,
                    "chrome_args": ['--disable-images'],
                    "file_path": self.output_dir
                }
            },
            {
                "method": "fetch_page",
                "args": {
                    "do_parse_html": self.do_parse_html
                }
            },
            {
                "method": "quit",
                "args": {}
            }
        ]

        # Use the lambda function to generate configurations for each URL
        configs = [make_config(url) for url in self.urls]

        return configs

    
    def scrape(self):
        self._parse_proxies()
        configs = self._make_configs()
        results = run_parallel_scraping(configs, max_workers=self.max_workers)
        return results

    def run(self):
        """Run the JS scraping for the given URLs and proxies"""
        self._parse_proxies()
        configs = self._make_configs()

        results = run_parallel_scraping(configs, max_workers=self.max_workers)

        # TODO: This is a fake result, need to update it
        return {
            "urls_scraped": self.urls,
            "urls_failed": [],
            "proxies_used": self.proxies_list,
            "proxies_failed": [],
            "results": results
        }

