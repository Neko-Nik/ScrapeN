"""
This is the main app file which contains all the endpoints of the API
This file is used to run the API
"""

from src.utils.base.libraries import (
    FastAPI,
    Depends,
    Jinja2Templates,
    CORSMiddleware,
    BackgroundTasks,
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
from src.main import render_sitemap, render_scrape
from src.utils.user.auth import get_user_token
from src.utils.user.handler import User
from src.scraping.main import ProcessJob


# Initialization
app = FastAPI(
    title="Neko Nik - Scrape API",
    description="This Scrape API is used to scrape data from the web",
    version="1.5.2",
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



@app.get("/test_auth", response_class=JSONResponse, tags=["Test"], summary="Test authentication")
def test_auth(request: Request, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to test authentication
    """
    user_obj = User()
    user, stripe_data, stripe_plan = user_obj.handle_user_creation_get(user["email"], user["name"], user["uid"], user["email_verified"])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"user": user, "stripe_data": stripe_data, "stripe_plan": stripe_plan}
    )

# Get user data - nothing but the handle_user_creation_get
# update user data
    # - if user changes the email, then update the email in the user table
    # - if user changes the name, then update the name in the user table
    # - if user changes the plan, then update the plan in the user table
    # - if user updates the points, then update the points in the user table
# Delete account




# Scrape data from the given URL with the given proxy
@app.post("/scrape", response_class=JSONResponse, tags=["Scrape"], summary="Scrape data from the given URL with the given proxy")
def scrape_websites(request: Request, background_tasks: BackgroundTasks, urls: list, proxies: list, 
                    user: dict=Depends(get_user_token), parse_text: bool=True) -> JSONResponse:
    """
    This endpoint is used to scrape data from the given URL with the given proxy
    """
    try:
        # TODO: handle parallel requests based on user data
        # if user is good to go then only do the scraping
        user_obj = User()
        user_db_data = user_obj.read(user["email"])
        points = user_db_data[0][4]
        parallel = user_db_data[0][5]
        if parallel == "FREE":
            parallel = 1
        else:
            parallel = 3
        if user_db_data and user_db_data[0][3] == 1 and points > len(urls):
            # Setup required things for scraping and set status as processing
            job_obj = ProcessJob(urls=urls, proxies=proxies, parse_text=parse_text, parallel=parallel, user=user)
            job_result = job_obj.run()

            background_tasks.add_task(render_scrape, urls=urls, proxies=proxies, parse_text=parse_text, parallel=parallel, job_data=job_result, job_obj=job_obj)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Scraping started", "job_id": job_result["process_id"]}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                content={"message": "User is not active or not enough points"}
            )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions(
            "Something went wrong",
            status.HTTP_500_INTERNAL_SERVER_ERROR)



# Get List of URL, given sitemap URL (XML)
@app.get("/sitemap", response_class=JSONResponse, tags=["Sitemap"], summary="Get List of URL, given sitemap URL (XML)")
def home(request: Request, url: str) -> JSONResponse:
    """
    This endpoint is used to get List of URL, given sitemap URL (XML)
    """
    try:
        urls_data = render_sitemap(url=url)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=urls_data
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