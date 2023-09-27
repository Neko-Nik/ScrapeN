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


def render_scrape(urls: list, proxies: list, job_obj: ProcessJob, do_parsing: bool=True, parallel: int=1, job_data: dict={}) -> None:
    """Scrape data from the given URL with the given proxy"""
    user_email = job_obj.user.get("email", "unknown")

    # Start the scraping process
    logging.debug(f"Scraping {len(urls)} urls with {len(proxies)} proxies for user: {user_email} with job_id: {job_obj.job_id}")
    scraper_obj = WebScraper(num_workers=parallel, do_parse_html=do_parsing, output_dir=job_data["folder_path"])
    scrape_results = scraper_obj.scrape_urls(urls=urls, proxies_list=proxies)
    
    # Update the job object with the scrape results and set status as zippping
    logging.debug(f"Updating job object with scrape results and setting status as zippping for user: {user_email} with job_id: {job_obj.job_id}")
    job_obj.update(scrape_results)

    # Zip the output folder and verify the hash
    logging.debug(f"Zipping the output folder and verifying the hash for user: {user_email} with job_id: {job_obj.job_id}")
    file_path, file_hash = zip_folder_and_verify(folder_path=job_data["folder_path"])
    if not file_path or not file_hash:
        job_obj.failed()

    logging.debug(f"Job completed for user: {user_email} with job_id: {job_obj.job_id}")
    job_obj.update_job_completed(**{"zip_file_path": file_path, "zip_file_hash": file_hash})

