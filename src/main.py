"""All the main function that will be executed when the API is called"""

from src.utils.base.libraries import logging
from src.sitemap.main import get_urls_from_xml
from src.scraping.main import WebScraper, ProcessJob
from src.scraping.base_functions import zip_folder_and_verify


def render_sitemap(url: str) -> dict:

    urls_data = get_urls_from_xml(url)
    
    resp = {
        "sitemap_url": url,
        "total_urls": len(urls_data),
        "urls": urls_data
    }

    return resp




def render_scrape(urls: list, proxies: list, job_obj: ProcessJob, parse_text: bool=True, parallel: int=1, job_data: dict={}) -> dict:
    """Scrape data from the given URL with the given proxy"""

    # Start the scraping process
    scraper_obj = WebScraper(num_workers=parallel, do_parse_html=parse_text, output_dir=job_data["folder_path"])
    scrape_results = scraper_obj.scrape_urls(urls=urls, proxies_list=proxies)
    
    # Update the job object with the scrape results and set status as zippping
    job_obj.update(scrape_results)

    # Zip the output folder and verify the hash
    file_path, file_hash = zip_folder_and_verify(folder_path=job_data["folder_path"])

    # TODO: Given the file path and file hash, update the job with the file path and hash and set status as done and download link
