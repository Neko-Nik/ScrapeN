from src.utils.base.libraries import logging, requests, cloudscraper


# users should also have logs to see what is happening


# set as config in class / init def
SKIP_STATUS_CODES = [404, 500]


def generate_proxy_url(username, password, ip, port):
    proxy_url = f"http://{username}:{password}@{ip}:{port}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    return proxies


def get_data(url: str, proxies: dict):
    try:
        # response = requests.get(url, proxies=proxies, timeout=TIME_OUT)
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, proxies=proxies)
        if response.status_code == 200:
            original_url = f"<!-- Original URL: {url} -->"
            data = original_url + "\n" + response.text
            return data

        elif response.status_code in SKIP_STATUS_CODES:
            # add this to user logs
            logging.info(f"Skipping {url} with proxy {proxies}")
            return {"stop": "stop"}
        else:
            # add this to user logs
            logging.info(f"Some error occured for {url} with proxy {proxies} with status code {response.status_code}")
            return {"stop": "continue"}

    except requests.exceptions.RequestException:
        logging.error(f"Request Exception occured for {url} with proxy {proxies}")
        return {"stop": "continue"}


def process_url(url: str, proxy: dict=None):
    # make a proxy parsing class 
    ip, port, username, password = proxy.split(':')
    proxie = generate_proxy_url(username, password, ip, port)

    # make a url parsing class
    data = get_data(url, proxie)

    if "stop" in data:
        return data

    else:
        return data