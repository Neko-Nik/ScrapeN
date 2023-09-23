"""
This is the main app file which contains all the endpoints of the API
This file is used to run the API
"""

from src.utils.base.libraries import (
    FastAPI,
    Jinja2Templates,
    CORSMiddleware,
    Request,
    JSONResponse,
    HTMLResponse,
    uvicorn,
    os,
    logging,
    json,
    status
)
from src.utils.base.constants import NUMBER_OF_LOGS_TO_DISPLAY
from src.scraping.main import process_url
from src.sitemap.main import get_urls_from_xml
from src.parsing.main import parse_html


# Initialization
app = FastAPI(
    title="Neko Nik - Scrape API",
    description="This Scrape API is used to scrape data from the web",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    include_in_schema=True,
)

# Load templates
templates = Jinja2Templates(directory="templates")

# Add CROCS middle ware to allow cross origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Class for handling wrong input 
class All_Exceptions(Exception):
    def __init__(self , message: str , status_code: int):
        self.message = message
        self.status_code = status_code

# 
@app.exception_handler(All_Exceptions)
async def input_data_exception_handler(request: Request, exc: All_Exceptions):    
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"Oops! {exc.message} "}
    )


#    Endpoints    #

# Logs of API
@app.get("/logs", response_class=HTMLResponse,
        tags=["Logs"], summary="Logs of API")
def view_logs(request: Request) -> HTMLResponse:
    """
    This endpoint is used to view the logs of the API in a web page
    Just go to /logs to view the logs
    """
    logs = []
    log_file_path = os.path.join(os.getcwd(), 'logs', 'log.txt')
    
    with open(log_file_path, 'r') as file:
        for line in file:
            try:
                log_entry = json.loads(line)
                logs.append(log_entry)
            except json.JSONDecodeError:
                logging.error("Invalid JSON format: " + line)
    
    logs.reverse()  # To show the latest logs first
    
    # To show only the latest 100 logs
    logs = logs[:NUMBER_OF_LOGS_TO_DISPLAY]
    response = {"request": request, "logs": logs}

    return templates.TemplateResponse("logs.html", response)



# Scrape data from the given URL with the given proxy
@app.get("/scrape", response_class=HTMLResponse, tags=["Scrape"], summary="Scrape data from the given URL with the given proxy")
def home(request: Request, proxy: str, url: str, parse_text: bool=True) -> JSONResponse:
    """
    This endpoint is used to scrape data from the given URL with the given proxy
    """
    try:
        html_data = process_url(url, proxy)
        
        if parse_text:
            parsed_data = parse_html(url, html_data)
        
        data = {
            "url": url,
            "proxy": proxy,
            "html_data": html_data,
            "parsed_data": parsed_data
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=data
        )
    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions(
            "Something went wrong",
            status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get List of URL, given sitemap URL (XML)
@app.get("/sitemap", response_class=HTMLResponse, tags=["Sitemap"], summary="Get List of URL, given sitemap URL (XML)")
def home(request: Request, url: str) -> JSONResponse:
    """
    This endpoint is used to get List of URL, given sitemap URL (XML)
    """
    try:
        urls_data = get_urls_from_xml(url)
        
        resp = {
            "sitemap_url": url,
            "total_urls": len(urls_data),
            "parsed_data": data,
            "urls": urls_data
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=resp
        )
    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions(
            "Something went wrong",
            status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == '__main__':
    # reload=True - server will automatically restart after code changes
    uvicorn.run('app:app', host='0.0.0.0', port=8080, reload=True)

# 184.174.126.249:6541:olmjtxsz:yccmlx17olxs