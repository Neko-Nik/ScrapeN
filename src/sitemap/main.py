from src.utils.base.libraries import logging, requests, ET, cloudscraper, urllib
from src.utils.user.postgresql import UserPostgreSQLCRUD
from src.utils.base.basic import Error



class ScrapeXML:
    def __init__(self, xml_urls: list, do_nested: bool = False):
        self.xml_urls = xml_urls
        self.do_nested = do_nested
        self.max_nested_count = 2
        self.nested_count = 0

    def _get_xml_url_site(self, xml_url: str) -> dict:
        """Render the xml url"""
        try:
            response = requests.get(xml_url)
            if response.status_code != 200:
                return Error(code=400, message=f"Error in getting xml from {xml_url} with status code {response.status_code}")
            elif response.status_code == 403:
                scraper = cloudscraper.create_scraper()
                response = scraper.get(xml_url)
                if response.status_code != 200:
                    return Error(code=400, message=f"Error in getting xml from {xml_url} with status code {response.status_code}, with bypassing cloudflare")
            content_type = response.headers.get('Content-Type', '')
            if 'xml' not in content_type:
                return Error(code=400, message=f"Unexpected Content-Type: {content_type}")
            xml_data = response.content.decode('utf-8-sig')
            return xml_data
        except Exception as e:
            return Error(code=400, message=f"Error in getting xml from {xml_url} with error {e}")

    def _get_urls_from_xml(self, xml_data: str) -> list:
        """Get the urls from the xml"""
        try:
            urls = []
            root = ET.fromstring(xml_data)
            # Define namespace
            namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for url in root.findall(".//sitemap:loc", namespaces):
                urls.append(url.text.strip())
            return urls
        except Exception as e:
            return Error(code=400, message=f"Error in getting urls from xml with error {e}")
        
    def _process_xml_url(self, xml_url: str) -> list:
        """Process the xml url"""
        xml_data = self._get_xml_url_site(xml_url)
        if isinstance(xml_data, Error):
            return xml_data
        urls = self._get_urls_from_xml(xml_data)
        return urls

    def _is_xml_url(self, url: str) -> bool:
        """Check if the url is xml url"""
        # check if its a url or not
        if not urllib.parse.urlparse(url).scheme in ["http", "https"]:
            return False
        return url.endswith(".xml")
    
    def _process_nested_urls(self, xml_urls: list, urls: list=[]) -> list:
        """Process the nested urls recursively until the max_nested_count is reached"""
        if self.nested_count >= self.max_nested_count:
            return urls
        for xml_url in xml_urls:
            if not self._is_xml_url(xml_url):
                continue
            self.nested_count += 1
            urls.extend(self._process_xml_url(xml_url))
            urls.extend(self._process_nested_urls(xml_urls=urls, urls=urls))
        return urls

    def process_urls(self):
        """Process the urls"""
        urls = []
        for xml_url in self.xml_urls:
            if self.do_nested:
                nested_urls = self._process_xml_url(xml_url)
                if isinstance(nested_urls, Error):
                    return nested_urls
                urls.extend(self._process_nested_urls(xml_urls=nested_urls, urls=urls))
            else:
                urls.extend(self._process_xml_url(xml_url))
        urls = list(set(urls))
        urls.sort()
        return urls


class Sitemap:
    def __init__(self, user: dict, xml_urls: list, do_nested: bool = False):
        self.userDB = UserPostgreSQLCRUD()
        self.user = user
        self.xml_urls = xml_urls
        self.do_nested = do_nested
        self.error = None
        self._validate_xml_url()

    def _validate_xml_url(self):
        self.xml_urls = [url for url in self.xml_urls if urllib.parse.urlparse(url).scheme in ["http", "https"]]
        self.xml_urls = list(set(self.xml_urls))
        self.xml_urls.sort()
        self.xml_urls = [url for url in self.xml_urls if url.endswith(".xml")]
        if not self.xml_urls:
            self.error = Error(code=400, message="After validation, no valid xml urls found")

    def _reduce_points(self):
        """Reduce the points from the user"""
        to_process_points = len(self.xml_urls)
        user_email = self.user.get("email","Unknown")
        user_points = self.userDB.read(email=user_email).get("points", 0)

        if user_points >= to_process_points:
            self.userDB.update(user_email, {"points": user_points - to_process_points})
            return True
        return False

    def _set_preconditions(self):
        if self.error:
            return self.error

        user_email = self.user.get("email","Unknown")
        user_points = self.userDB.read(email=user_email).get("points", 0)
        # Check if the user has enough credits to process the job
        if not self._reduce_points():
            return Error(code=400, message=f"Not enough points to process the xml urls. User points: {user_points}, Points required: {len(self.xml_urls)}")

    def _pre_process(self):
        preconditions_status = self._set_preconditions()
        if isinstance(preconditions_status, Error):
            return preconditions_status

    def run(self):
        pre_process_status = self._pre_process()
        if isinstance(pre_process_status, Error):
            return pre_process_status
        
        scrape_xml_obj = ScrapeXML(xml_urls=self.xml_urls, do_nested=self.do_nested)
        urls = scrape_xml_obj.process_urls()
        return urls

