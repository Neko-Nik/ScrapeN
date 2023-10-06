from src.scraping.javascript_scraper import run_parallel_scraping
import json



run_config = [
    {
        "method": "__init__",
        "args": {
            "url": "https://www.nekonik.com/",
            "proxy_list": [('154.92.112.3', '5024', 'olmjtxsz', 'yccmlx17olxs'), ("45.43.83.171",'6454','olmjtxsz', 'yccmlx17olxs')],
            "chrome_args": ['--disable-images'],
            "file_path": "results"
        }
    },
    {
        "method": "fetch_page",
        "args": {}
    },
    {
        "method": "take_screenshot",
        "args": {
            "path": "screenshots/example.png",
        }
    },
    {
        "method": "quit",
        "args": {}
    }
]



if __name__ == "__main__":
    data = run_parallel_scraping([run_config]*20 , max_workers=30)
    print(json.dumps(data, indent=4))
