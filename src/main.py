"""All the main function that will be executed when the API is called"""

from src.utils.base.libraries import json, os
from src.scraping.main import WebScraper, ProcessJob
from src.scraping.javascript_scraper import JsScraping
from src.scraping.base_functions import zip_folder_and_verify
from src.utils.user.notifications import NotificationWebhook, NotificationsEmail


def render_scrape(process_job_obj: ProcessJob) -> None:
    """Scrape data from the given URL with the given proxy"""
    
    # process_job_obj use this to get all the data
    job_id = process_job_obj.job_id
    urls = process_job_obj.urls
    do_js_rendering = process_job_obj.do_js_rendering
    proxies = process_job_obj.proxies
    num_parallel_workers = process_job_obj.parallel
    do_parsing = process_job_obj.do_parsing
    output_dir_for_urls_processed = os.path.join(process_job_obj.job_folder_path, job_id)
    os.makedirs(output_dir_for_urls_processed, exist_ok=True)


    # Start the scraping process
    process_job_obj._save_logs(f"Scraping {len(urls)} urls with {len(proxies)} proxies")
    if do_js_rendering:
        scrape_results = JsScraping(urls=urls, proxies=proxies, do_parse_html=do_parsing, max_workers=num_parallel_workers, output_dir=output_dir_for_urls_processed).run()
    else:
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

    results_data = process_job_obj.update_job_completed(**{"zip_file_path": file_path, "zip_file_hash": file_hash})

    config = json.loads(process_job_obj.user_db_data.get("config", "{}"))
    send_webhook_url_notification = config.get("webhook_url", False)
    send_email_notification = config.get("email_notification", False)   # TODO: Not implemented yet

    if send_email_notification:
        process_job_obj._save_logs(f"Sending email to the user")
        NotificationsEmail().send_email(email=process_job_obj.user_db_data["email"], subject="Job Completed", body=f"Job Completed: {results_data}")
        process_job_obj._save_logs(f"Email sent to the user")

    if send_webhook_url_notification:
        process_job_obj._save_logs(f"Calling the webhook")
        NotificationWebhook(webhook_url=send_webhook_url_notification, data=results_data, email=process_job_obj.user_db_data["email"]).call_webhook()
        process_job_obj._save_logs(f"Webhook called completed")

    return None

