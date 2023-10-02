import concurrent.futures
from src.utils.base.libraries import logging, cloudscraper, requests, os, threading, json, datetime, urllib
from src.utils.base.basic import Error
from src.utils.base.constants import LIST_OF_SKIP_CODES, OUTPUT_ROOT_DIR, SELF_SERVER_ROOT_URL, SAFETY_EXTENSIONS
from src.scraping.parsing import parse_html
from src.utils.user.postgresql import UserPostgreSQLCRUD, JobPostgreSQLCRUD
from src.profiles.main import JobProfile
from src.proxies.main import Proxies


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
    def __init__(self, urls: list, user: dict, profile_name: str, job_name: str, job_description: str=""):
        self.jobDB = JobPostgreSQLCRUD()
        self.userDB = UserPostgreSQLCRUD()
        self.jobProfile = JobProfile(user=user)
        self.proxiesObj = Proxies(user=user)
        self.logs = []
        self.user = user
        self.urls = urls
        self.profile_name = profile_name
        self.job_name = job_name
        self.job_description = job_description
        self.preprocessing_status = self._pre_processing()  # will add: do_parsing, parallel, proxies
        self.job_id = None
        self.job_folder_path = None
        self.allocated_parallel = 0
        self.user_db_data = {}

    def _save_logs(self, message):
        """Save the logs to the logs file"""
        message = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }
        self.logs.append(message)
        with open(os.path.join(self.job_folder_path, "logs.json"), "w") as f:
            json.dump(self.logs, f, indent=4)

    def _pre_processing(self):
        """Pre processing for the job"""
        current_profile = self.jobProfile.all_profiles.get(self.profile_name, None)
        if not current_profile:
            return Error(code=404, message=f"Profile {self.profile_name} not found")

        self.do_parsing = current_profile.get("parse_text", True)
        self.parallel = current_profile.get("parallel_count", 0)

        self.proxies = current_profile.get("proxies", [])
        if not self.proxies:
            self.proxies = self.proxiesObj.proxies
        if not self.proxies:
            return Error(code=412, message="There are no proxies available, please add proxies to either the profile or at the user level")

        self.handle_file_based_urls()
        if not self.urls:
            return Error(code=412, message="No URLs left after removing the file based URLs and invalid URLs")

        return True

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
        os.makedirs(os.path.join(OUTPUT_ROOT_DIR, self.user["user_id"], "jobs", self.job_id), exist_ok=True)
        self.job_folder_path = os.path.join(OUTPUT_ROOT_DIR, self.user["user_id"], "jobs", self.job_id)

    def _has_file_extension(self, url: str):
        """Check if the given URL has a file extension"""
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        split_url = path.split('/')
        split_url = list(filter(None, split_url))[-1] # clean the list
        if "." not in split_url:
            return False
        if split_url.endswith(SAFETY_EXTENSIONS):
            return False
        return True

    def handle_file_based_urls(self):
        """Handle the file based URLs"""
        self.urls = [url for url in self.urls if not self._has_file_extension(url)]
        # validate if its a valid url or not
        self.urls = [url for url in self.urls if urllib.parse.urlparse(url).scheme in ["http", "https"]]

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
    
    def reduce_parallel_units(self):
        """Reduce the parallel units from the user"""
        current_parallel = self.user_db_data.get("parallel_count", 0)
        if self.user_db_data:
            if current_parallel >= self.parallel:
                logging.debug(f"Reducing {self.parallel} parallel units from user {self.user['email']} with current parallel units {current_parallel}")
                self.userDB.update(self.user["email"], {"parallel_count": current_parallel - self.parallel})
                return True
        return False

    def _create_job_in_db(self):
        """Create a job in the database"""
        job_data = {
            "job_uid": self.user["email"] + '|' + self.job_id,
            "email": self.user["email"],
            "status": "processing",
            "profile_name": self.profile_name,
            "created_at": datetime.now(),
            "job_name": self.job_name,
            "job_description": self.job_description
        }
        self.jobDB.create(**job_data)
        self._save_logs("Updated the job details in the database")

    def pre_conditions(self):
        user_email = self.user["email"]
        user_data = self.userDB.read(email=user_email)
        self.user_db_data = user_data
        self.allocated_parallel = self.user_db_data.get("parallel_count", 0)
        self._save_logs("Starting to check the pre conditions for the job")

        if not user_data:
            return Error(code=404, message=f"User with email {user_email} not found")

        if not self.urls:
            return Error(code=412, message="No URLs left after removing the file based URLs")

        has_enough_parallel_units = self.reduce_parallel_units()
        if not has_enough_parallel_units:
            return Error(code=412, message=f"Parallel count {self.parallel} is greater than \
                         allocated parallel count {self.allocated_parallel} or You don't have enough \
                            parallel units to scrape the given URLs with the given profile")

        has_enough_points = self.reduce_points()
        if not has_enough_points:
            return Error(code=412, message="Not enough points to scrape the given URLs")

        self._save_logs("All the pre conditions are met, so proceeding with the job")

        return {"has_enough_points": has_enough_points}
    
    def _save_job_data_files(self):
        self._save_logs("Saving the job data files")
        config_data = {
            "profile_name": self.profile_name,
            "job_name": self.job_name,
            "do_parsing": self.do_parsing,
            "parallel": self.parallel,
            "urls": self.urls,
            "proxies": self.proxies
        }
        
        with open(os.path.join(self.job_folder_path, "config.json"), "w") as f:
            json.dump(config_data, f, indent=4)
        self._save_logs("Saved the job config file")

    def run(self):
        """Run the process"""
        if isinstance(self.preprocessing_status, Error):
            return self.preprocessing_status
        self.make_job_id()
        self._save_logs("Job creation preprocessing step is completed")

        pre_process = self.pre_conditions()
        if isinstance(pre_process, Error):
            return pre_process

        self._create_job_in_db()
        self._save_job_data_files()
        return {
            "job_id": self.job_id,
            "urls": self.urls,
            "profile_name": self.profile_name
        }
    
    def _post_processing(self, scrape_results):
        """Post processing for the job"""
        self._save_logs("Starting the post processing for the job")
        config_data = {}
        with open(os.path.join(self.job_folder_path, "config.json"), "r") as f:
            config_data = json.load(f)
        
        # remove success from the failed list
        urls_failed = [url for url in scrape_results["urls_failed"] if url not in scrape_results["urls_scraped"]]

        # increase the points by the number of urls not scraped
        user_db_data = self.userDB.read(self.user["email"])
        current_points = user_db_data.get("points", 0)
        add_points = len(urls_failed)
        points_used = len(scrape_results["urls_scraped"])
        new_points = current_points + add_points
        new_parallel_units = user_db_data.get("parallel_count", 0) + self.parallel
        self.userDB.update(self.user["email"], {"points": new_points, "parallel_count": new_parallel_units})

        self._save_logs(f"Updated with the new points with {new_points} points")

        config_data["urls_scraped"] = scrape_results["urls_scraped"]
        config_data["urls_failed"] = scrape_results["urls_failed"]
        config_data["proxies_used"] = scrape_results["proxies_used"]
        config_data["proxies_failed"] = scrape_results["proxies_failed"]
        config_data["points_used"] = points_used
        config_data["points_added"] = add_points
        config_data["points_remaining"] = new_points

        with open(os.path.join(self.job_folder_path, "config.json"), "w") as f:
            json.dump(config_data, f, indent=4)
        
        self._save_logs("Post processing for the job is completed, saved the results to the config file")

        return config_data

    def update(self,scrape_results):
        """Update the process"""
        self._save_logs("Processing the scrape results")

        config_data = self._post_processing(scrape_results)

        # update the status in db as zipping
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {
            "status": "zipping",
            "points_used": config_data["points_used"],
            "urls_failed": len(config_data["urls_failed"]),
            "proxies_failed": len(config_data["proxies_failed"])
        })
        self._save_logs("Updated the job status in the database")
        return True

    def failed(self, message=""):
        """Update the process as failed"""
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {"status": "Failed: " + message})
        self._save_logs("Failed the job with message: " + message)
        return True
    
    def _generate_url(self):
        """Generate the URL for the file"""
        create_path = os.path.join(self.user['user_id'], "jobs", self.job_id, self.job_id + ".zip")
        url = f"{SELF_SERVER_ROOT_URL}/download/{create_path}"
        return url

    def update_job_completed(self, zip_file_path, zip_file_hash):
        """Update the process as completed"""
        self._save_logs("Updating the job as completed in the database and config file")
        file_url_link = self._generate_url()
        self.jobDB.update(self.user["email"] + '|' + self.job_id, {"status": "completed", "zip_file_url": file_url_link})

        config_data = {}
        with open(os.path.join(self.job_folder_path, "config.json"), "r") as f:
            config_data = json.load(f)

        config_data["zip_file_path"] = zip_file_path
        config_data["zip_file_hash"] = zip_file_hash

        with open(os.path.join(self.job_folder_path, "config.json"), "w") as f:
            json.dump(config_data, f, indent=4)

        self._save_logs("Job completed successfully!")

        return {"job_id": self.job_id, "status": "completed", "zip_file_url": file_url_link, "md5_hash": zip_file_hash}

