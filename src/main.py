"""All the main function that will be executed when the API is called"""

from src.utils.base.libraries import logging, os
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


def render_scrape(process_job_obj: ProcessJob) -> None:
    """Scrape data from the given URL with the given proxy"""
    
    # process_job_obj use this to get all the data
    job_id = process_job_obj.job_id
    urls = process_job_obj.urls
    proxies = process_job_obj.proxies
    num_parallel_workers = process_job_obj.parallel
    do_parsing = process_job_obj.do_parsing
    output_dir_for_urls_processed = os.path.join(process_job_obj.job_folder_path, job_id)
    os.makedirs(output_dir_for_urls_processed, exist_ok=True)


    # Start the scraping process
    process_job_obj._save_logs(f"Scraping {len(urls)} urls with {len(proxies)} proxies")
    scraper_obj = WebScraper(num_workers=num_parallel_workers, do_parse_html=do_parsing, output_dir=output_dir_for_urls_processed)
    scrape_results = scraper_obj.scrape_urls(urls=urls, proxies_list=proxies)
    process_job_obj._save_logs(f"Scraping completed!")

    # Update the job object with the scrape results and set status as zippping
    process_job_obj.update(scrape_results)

    # Zip the output folder and verify the hash
    process_job_obj._save_logs(f"Zipping the output folder and verifying the hash")
    file_path, file_hash = zip_folder_and_verify(folder_path=output_dir_for_urls_processed)
    if not file_path or not file_hash:
        process_job_obj.failed(message="Error while zipping the output folder")

    process_job_obj.update_job_completed(**{"zip_file_path": file_path, "zip_file_hash": file_hash})

    # Send email to the user or call the webhook
