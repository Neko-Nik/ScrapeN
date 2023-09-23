from src.utils.base.libraries import logging, requests, ET, cloudscraper



def blocked_xml_page(xml_url):

    scraper = cloudscraper.create_scraper()
    response = scraper.get(xml_url)

    return response



def get_xml(xml_url):
    response = requests.get(xml_url)
    if response.status_code == 403:
        response = blocked_xml_page(xml_url)
        if response.status_code != 200:
            logging.error(f"Error in getting xml from {xml_url} with status code {response.status_code}")
            return None

    elif response.status_code != 200:
        logging.error(f"Error in getting xml from {xml_url} with status code {response.status_code}")
        return None

    content_type = response.headers.get('Content-Type', '')
    if 'xml' not in content_type:
        logging.error(f"Unexpected Content-Type: {content_type}")
        return None

    xml_data = response.content.decode('utf-8-sig')

    return xml_data



def get_urls(xml):
    urls = []

    root = ET.fromstring(xml)
    
    # Define namespace
    namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    for url in root.findall(".//sitemap:loc", namespaces):
        urls.append(url.text.strip())
    return urls


def get_urls_from_xml(XML_URL):

    # Check if the URL ends with .xml
    # do a lot more validations

    # what if the url is not a xml file
    # what if my IP is blocked to access the url

    xml = get_xml(XML_URL)

    if xml:
        urls = get_urls(xml)
        return urls
    
    return []