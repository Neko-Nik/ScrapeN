"""All the main function that will be executed when the API is called"""

from src.utils.base.libraries import logging
from src.scraping.parsing import parse_html
from src.scraping.main import process_url
from src.sitemap.main import get_urls_from_xml


def render_sitemap(url: str) -> dict:

    urls_data = get_urls_from_xml(url)
    
    resp = {
        "sitemap_url": url,
        "total_urls": len(urls_data),
        "urls": urls_data
    }

    return resp



import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelURLProcessor:
    def __init__(self, output_directory, num_workers=1):
        self.output_directory = output_directory
        os.makedirs(self.output_directory, exist_ok=True)
        self.max_workers = min(os.cpu_count() or 1, num_workers)  # Limit to a reasonable number of threads

    def process_in_parallel(self, urls: list, proxies: list, parse_text: bool=True) -> None:
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for url in urls:
                for proxy in proxies:
                    futures.append(executor.submit(self.render_url, url, proxy, parse_text))

            # Keep track of the current URL and proxy indices
            url_index = 0
            proxy_index = 0

            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc_info:
                    logging.error(exc_info)
                    result = {
                        "url": urls[url_index],
                        "proxy": proxies[proxy_index],
                        "error": str(exc_info)
                    }

                # Generate a unique filename for each combination of URL and proxy
                file_name = os.path.join(self.output_directory, self.url_proxy_to_filename(urls[url_index], proxies[proxy_index]))
                file_name = self.ensure_unique_filename(file_name)
                self.save_result_to_file(file_name, result)

                # Move to the next proxy
                proxy_index = (proxy_index + 1) % len(proxies)

                # If all proxies have been used, move to the next URL
                if proxy_index == 0:
                    url_index += 1

    @staticmethod
    def url_proxy_to_filename(url: str, proxy: str) -> str:
        return f"{ParallelURLProcessor.url_to_filename(url)}_{ParallelURLProcessor.url_to_filename(proxy)}"

    @staticmethod
    def ensure_unique_filename(file_name: str) -> str:
        base, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(file_name):
            file_name = f"{base}_{counter}{ext}"
            counter += 1
        return file_name

    @staticmethod
    def save_result_to_file(file_name: str, result: dict) -> None:
        with open(file_name, 'w') as file:
            json.dump(result, file, indent=4)

    @staticmethod
    def render_url(url: str, proxy: str, parse_text: bool=True) -> dict:
        html_data = process_url(url, proxy)
        data = {"url": url, "proxy": proxy, "html_data": html_data}

        if parse_text:
            parsed_data = parse_html(url, html_data)
            data["parsed_data"] = parsed_data

        return data


# Example usage:
# if __name__ == "__main__":
#     urls = ["https://example.com", "https://example.org"]
#     proxies = ["http://proxy1.com", "http://proxy2.com"]
    
#     processor = ParallelURLProcessor()
#     processor.process_in_parallel(urls, proxies, parse_text=True)
