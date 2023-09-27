import concurrent.futures
from src.utils.base.libraries import logging, cloudscraper, requests, os, threading, json, datetime, urllib
from src.utils.base.basic import Error
from src.utils.base.constants import LIST_OF_SKIP_CODES, OUTPUT_ROOT_DIR
from src.scraping.parsing import parse_html
from src.utils.user.postgresql import UserPostgreSQLCRUD, JobPostgreSQLCRUD


class WebScraper:
    def __init__(self, output_dir, num_workers=None, do_parse_html=True):
        self.max_workers = min(os.cpu_count() or 1, num_workers)
        self.proxies_lock = threading.Lock()  # Lock for accessing the proxies list
        self.urls_lock = threading.Lock()  # Lock for accessing the URLs list
        self.do_parse_html = do_parse_html
        self.output_dir = output_dir

        # Processed data
        self.urls_scraped = []
        self.urls_failed = []
        self.proxies_used = []
        self.proxies_failed = []

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
                self.proxies_used.append(proxy)
                self.urls_scraped.append(url)
                break  # If data is not an error, we have successfully retrieved the data
            else:
                self.proxies_failed.append(proxy)
                self.urls_failed.append(url)
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



    def scrape_urls(self, urls: list, proxies_list: list) -> dict:
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

        # Once all the URLs are processed, remove the duplicates
        self.urls_scraped = list(set(self.urls_scraped))
        self.urls_failed = list(set(self.urls_failed))
        self.proxies_used = list(set(self.proxies_used))
        self.proxies_failed = list(set(self.proxies_failed))

        return {
            "urls_scraped": self.urls_scraped,
            "urls_failed": self.urls_failed,
            "proxies_used": self.proxies_used,
            "proxies_failed": self.proxies_failed
        }


class ProcessJob:
    def __init__(self, urls: list, proxies: list, do_parsing: bool = True, parallel: int = 1, user: dict = {}):
        self.jobDB = JobPostgreSQLCRUD()
        self.userDB = UserPostgreSQLCRUD()
        self.urls = urls
        self.proxies = proxies
        self.do_parsing = do_parsing
        self.parallel = parallel
        self.job_id = None
        self.folder_path = None
        self.user = user
        self.allocated_parallel = 0
        self.user_db_data = {}

    def _string_connvert(self, date: str):
        date = str(date)
        # Each digit change to A, B, C, etc
        date = date.replace("0", "A")
        date = date.replace("1", "B")
        date = date.replace("2", "C")
        date = date.replace("3", "D")
        date = date.replace("4", "E")
        date = date.replace("5", "F")
        date = date.replace("6", "G")
        date = date.replace("7", "H")
        date = date.replace("8", "I")
        date = date.replace("9", "J")
        return date
    
    def _job_id_decoder(self, date: str):
        date = str(date)
        # Each digit change to A, B, C, etc
        date = date.replace("A", "0")
        date = date.replace("B", "1")
        date = date.replace("C", "2")
        date = date.replace("D", "3")
        date = date.replace("E", "4")
        date = date.replace("F", "5")
        date = date.replace("G", "6")
        date = date.replace("H", "7")
        date = date.replace("I", "8")
        date = date.replace("J", "9")
        # give back the clear format of date
        date = datetime.strptime(date, "%Y%m%d%H%M%S")
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        return date

    def make_job_id(self):
        """This job id is unique for each user"""
        current_time = datetime.now()
        # Format the current time as a string
        formatted_time = current_time.strftime("%Y%m%d%H%M%S")
        # Convert the string to a unique string
        self.job_id = self._string_connvert(formatted_time)
        self.folder_path = os.path.join(OUTPUT_ROOT_DIR, self.user["email"], self.job_id)

    def _has_file_extension(self, url: str):
        """Check if the given URL has a file extension"""
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        # Split the path by "." and check if the last part has a file extension
        parts = path.split(".")
        if len(parts) > 1:
            if not parts[-1] in ["html", "htm"]:
                return True
        return False

    def handle_file_based_urls(self):
        """Handle the file based URLs"""
        self.urls = [url for url in self.urls if not self._has_file_extension(url)]

    def reduce_points(self):
        """Reduce the points from the user"""
        initial_points = len(self.urls)
        current_points = self.user_db_data.get("points", 0)

        if self.user_db_data:
            if current_points >= initial_points:
                logging.debug(f"Reducing {initial_points} points from user {self.user['email']} with current points {current_points}")
                self.userDB.update(self.user["email"], {"points": current_points - initial_points})
                return True
        return False

    def create_job_in_db(self):
        """Create a job in the database"""
        job_data = {
            "job_id": self.user["email"] + '|' + self.job_id,
            "email": self.user["email"],
            "status": "processing",
            "urls": json.dumps(self.urls),
            "proxies": json.dumps(self.proxies),
            "do_parsing": self.do_parsing,
            "parallel_count": self.parallel,
            "created_at": datetime.now()
        }
        self.jobDB.create(**job_data)

    def pre_conditions(self):
        user_email = self.user["email"]
        user_data = self.userDB.read(email=user_email)
        self.user_db_data = user_data
        self.allocated_parallel = self.user_db_data.get("parallel_count", 0)

        if not user_data:
            return Error(code=404, message=f"User with email {user_email} not found")

        if not self.urls:
            return Error(code=412, message="No URLs left after removing the file based URLs")

        if self.parallel > self.allocated_parallel:
            return Error(code=412, message=f"Parallel count {self.parallel} is greater than allocated parallel count {self.allocated_parallel}")

        has_enough_points = self.reduce_points()
        if not has_enough_points:
            return Error(code=412, message="Not enough points to scrape the given URLs")

        return {"has_enough_points": has_enough_points}

    def run(self):
        """Run the process"""
        self.make_job_id()
        self.handle_file_based_urls()
        pre_process = self.pre_conditions()
        if isinstance(pre_process, Error):
            return pre_process

        self.create_job_in_db()

        return {
            "job_id": self.job_id,
            "folder_path": self.folder_path,
            "urls": self.urls,
            "proxies": self.proxies,
            "do_parsing": self.do_parsing,
            "parallel_count": self.parallel,
            "has_enough_points": pre_process["has_enough_points"],
        }

    def update(self,scrape_results):
        """Update the process"""
        # increase the points by the number of urls not scraped
        urls_scraped = scrape_results["urls_scraped"]
        urls_failed = scrape_results["urls_failed"]
        # remove success from the failed list
        urls_done = [url for url in urls_failed if url not in urls_scraped]

        # update the status in db as zipping
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {
            "status": "zipping",
            "urls_scraped": json.dumps(scrape_results["urls_scraped"]),
            "urls_failed": json.dumps(scrape_results["urls_failed"]),
            "proxies_used": json.dumps(scrape_results["proxies_used"]),
            "proxies_failed": json.dumps(scrape_results["proxies_failed"]),
            "points_used": len(urls_scraped),
            # "parallel_count": 
            # TODO: add the parallel count used back to the user
        })

        # increase the points by the number of urls not scraped
        points = len(urls_done)
        user_email = self.user["email"]
        user = self.userDB.read(user_email)
        if user:
            current_points = user.get("points", 0)
            new_points = current_points + points
            self.userDB.update(user_email, {"points": new_points})
        else:
            self.jobDB.update(user_email + '|' + self.job_id, {"status": "failed due to user not found"})
            return False

    def failed(self, message=""):
        """Update the process as failed"""
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {"status": "Failed: " + message})
        return True
    
    def update_job_completed(self, zip_file_path, zip_file_hash):
        """Update the process as completed"""
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {"status": "completed", "zip_file_path": zip_file_path, "zip_file_hash": zip_file_hash})
        return True

