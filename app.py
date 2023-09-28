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
    FileResponse,
    HTMLResponse,
    UploadFile,
    File,
    uvicorn,
    Optional,
    Form,
    os,
    logging,
    json,
    status,
    Limiter,
    get_remote_address,
    _rate_limit_exceeded_handler,
    RateLimitExceeded
)
from src.utils.base.constants import NUMBER_OF_LOGS_TO_DISPLAY, OUTPUT_ROOT_DIR
from src.main import render_sitemap, render_scrape
from src.utils.user.auth import get_user_token
from src.utils.user.handler import User
from src.scraping.main import ProcessJob
from src.utils.base.basic import Error
from src.utils.user.postgresql import JobPostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager
from src.proxies.main import ProxyValidator, Proxies
from src.profiles.main import JobProfile


# Initialization
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Neko Nik - ScrapeN API",
    description="This ScrapeN API is used to scrape data from the web",
    version="1.6.7",
    docs_url="/",
    redoc_url="/redoc",
    include_in_schema=True,
)

# Load templates
templates = Jinja2Templates(directory="templates")

# Add slowapi rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# Exception handler for wrong input
@app.exception_handler(All_Exceptions)
async def input_data_exception_handler(request: Request, exc: All_Exceptions):    
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"Oops! {exc.message} "}
    )


#    Endpoints    #


@app.get("/logs", response_class=HTMLResponse, tags=["Logs"], summary="Logs of API")
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


@app.get("/user", response_class=JSONResponse, tags=["User"], summary="Get user data, also creates user if not exists")
def get_user_data(request: Request, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to get user data, also creates user if not exists
    """
    try:
        user_obj = User()
        user_db_data = user_obj.get_user_data(user["email"], user["uid"], user["email_verified"])
        if isinstance(user_db_data, Error):
            raise All_Exceptions( user_db_data.message, user_db_data.code )

        return JSONResponse( status_code=status.HTTP_200_OK, content=user_db_data )
    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.post("/webhook/stripe", response_class=JSONResponse, tags=["Webhook"], summary="Stripe Webhook")
async def stripe_webhook(request: Request) -> JSONResponse:
    """
    This endpoint is used to handle stripe webhook
    """
    try:
        payload = await request.body()
        headers = request.headers
        stripe_signature = headers.get('stripe-signature','')
        if not stripe_signature:
            raise All_Exceptions( "Invalid stripe signature", status.HTTP_400_BAD_REQUEST )

        stripe_obj = StripeManager()
        stripe_obj.webhook_handler(payload, stripe_signature)
        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Webhook handled successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.delete("/user", response_class=JSONResponse, tags=["User"], summary="Delete user account")
def delete_user(request: Request, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to delete user account
    """
    try:
        user_obj = User()
        data = user_obj.handle_user_deletion(user["email"])
        if isinstance(data, Error) or not data:
            return JSONResponse( status_code=status.HTTP_423_LOCKED, content={"message": "User not deleted, please delete linked data first"} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "User deleted successfully"})

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.get("/job", response_class=JSONResponse, tags=["Job"], summary="Job one or all job details")
def job_status(request: Request, job_id: str=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to scrape status of the job id
    or if job id is not given, then it will return all the jobs of the user
    """
    try:
        job_id = user["email"] + "|" + job_id
        job_obj = JobPostgreSQLCRUD()
        job_data = job_obj.read(job_id)
        if not job_data:
            return JSONResponse( status_code=status.HTTP_404_NOT_FOUND, content={"message": "Job not found, please check the job id"} )

        # TODO: if job id is not given, then it will return all the jobs of the user only from the db not all the data
        # if job id is given, then read the logs and config from the file and return the data along with the db data

        return JSONResponse( status_code=status.HTTP_200_OK, content=job_data )
    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.get("/job/{job_id}/download", response_class=FileResponse, tags=["Job"], summary="Download processed job zip file")
def download_job_file(request: Request, job_id: str, user: dict=Depends(get_user_token)) -> FileResponse:
    """
    This endpoint is used to download processed job zip file from the given job id
    """
    try:
        job_obj = JobPostgreSQLCRUD()
        job_data = job_obj.read(job_id=user["email"] + "|" + job_id)
        zip_file_path = job_data.get("zip_file_path", None)
        if zip_file_path:
            zip_file_path = os.path.join(os.getcwd(), zip_file_path)
            return FileResponse(zip_file_path, media_type='application/zip', filename=zip_file_path.split("/")[-1])
        else:
            return JSONResponse( status_code=status.HTTP_404_NOT_FOUND, content={"message": "Job not found"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


# TODO: update the parallel count of the job (parallel units)
@app.post("/job", response_class=JSONResponse, tags=["Job"], summary="Create a new job")
@limiter.limit("1/2 second")
def create_job(request: Request, background_tasks: BackgroundTasks, profile_name: str, urls: list, job_name: str=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to create a new job, n number of urls and proxies can be passed, even 1 url and 1 proxy can be passed
    """
    try:
        process_job_obj = ProcessJob(urls=urls, user=user, profile_name=profile_name, job_name=job_name)
        job_data = process_job_obj.run()

        if isinstance(job_data, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": job_data.message} )

        else:
            background_tasks.add_task(render_scrape, process_job_obj=process_job_obj)
            return JSONResponse( status_code=status.HTTP_200_OK, content=job_data )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.get("/proxies", response_class=JSONResponse, tags=["Proxies"], summary="Get user proxies list")
def get_proxies(request: Request, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to get user proxies list
    """
    try:
        proxies_obj = Proxies(user)
        return JSONResponse( status_code=status.HTTP_200_OK, content=proxies_obj.proxies )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.put("/proxies", response_class=JSONResponse, tags=["Proxies"], summary="Update user proxies list")
def update_proxies(request: Request, user: dict=Depends(get_user_token),
                   file: Optional[UploadFile] = File(None), proxies: Optional[list] = Form(None)) -> JSONResponse:
    """
    This endpoint is used to update user proxies list, via list or json file
    """
    try:
        proxies_obj = Proxies(user)
        if file:
            # read file
            content = file.file.read()
            proxies = json.loads(content)
            if not isinstance(proxies, list):
                return JSONResponse( status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid file format, please upload a json file"} )

        elif proxies:
            proxies = proxies[0].split(",")

        validator_obj = ProxyValidator(proxies=proxies)
        is_success = proxies_obj.update(validator_obj.valid_proxies)
        if isinstance(is_success, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": is_success.message} )

        resp = { "valid_proxies": validator_obj.valid_proxies, "invalid_proxies": validator_obj.invalid_proxies }

        return JSONResponse( status_code=status.HTTP_200_OK, content=resp )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.delete("/proxies", response_class=JSONResponse, tags=["Proxies"], summary="Delete user proxies list")
def delete_proxies(request: Request, user: dict=Depends(get_user_token), proxies: Optional[list] = Form(None)) -> JSONResponse:
    """
    This endpoint is used to delete user proxies list
    """
    try:
        proxies_obj = Proxies(user)
        if proxies:
            proxies = proxies[0].split(",")
            proxies_obj.delete(delete_list=proxies)
            message = "Proxies that are given are deleted successfully, if they exist"
        else:
            proxies_obj.delete()
            message = "All proxies deleted successfully"

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": message} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.get("/job/profile", response_class=JSONResponse, tags=["Profile"], summary="Get Job Profile")
def get_job_profile(request: Request, user: dict=Depends(get_user_token), profile_name: str=None) -> JSONResponse:
    """
    This endpoint is used to get all the job profiles and also a specific job profile if profile name is given
    """
    try:
        profile_obj = JobProfile(user)
        profile_data = profile_obj.all_profiles

        if isinstance(profile_data, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": profile_data.message} )
        
        if profile_name:
            profile_data = profile_data.get(profile_name, None)
            if not profile_data:
                return JSONResponse( status_code=status.HTTP_404_NOT_FOUND, content={"message": "Profile not found"} )

        return JSONResponse( status_code=status.HTTP_200_OK, content=profile_data )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.post("/job/profile", response_class=JSONResponse, tags=["Profile"], summary="Create Job Profile")
def create_job_profile(request: Request, profile_name: str, parallel_count: int=None, parse_text: bool=True,
                        proxies: list=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to create job profile
    """
    try:
        profile_data = {
            "parallel_count": parallel_count,
            "parse_text": parse_text,
            "proxies": proxies
        }
        profile_obj = JobProfile(user)
        is_success = profile_obj.create(profile_name, profile_data)
        if isinstance(is_success, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": is_success.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Profile created successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.put("/job/profile", response_class=JSONResponse, tags=["Profile"], summary="Update Job Profile")
def update_job_profile(request: Request, profile_name: str, parallel_count: int=None, parse_text: bool=None,
                        proxies: list=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to update job profile
    """
    try:
        profile_data = {}
        if parallel_count:
            profile_data["parallel_count"] = parallel_count
        if parse_text is not None:
            profile_data["parse_text"] = parse_text
        if proxies:
            profile_data["proxies"] = proxies

        profile_obj = JobProfile(user)
        is_success = profile_obj.update(profile_name, profile_data)
        if isinstance(is_success, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": is_success.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Profile updated successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.delete("/job/profile", response_class=JSONResponse, tags=["Profile"], summary="Delete Job Profile")
def delete_job_profile(request: Request, profile_name: str, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to delete job profile
    """
    try:
        profile_obj = JobProfile(user)
        is_success = profile_obj.delete(profile_name)
        if isinstance(is_success, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": is_success.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Profile deleted successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )





@app.get("/sitemap", response_class=JSONResponse, tags=["Sitemap"], summary="Sitemap")
def sitemap(request: Request, site_url: str) -> JSONResponse:
    """
    This endpoint is used to render_sitemap
    """
    try:
        resp = render_sitemap(site_url)
        return JSONResponse( status_code=status.HTTP_200_OK, content=resp )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


# 25-30% usage for workers of 30 parallel count
# notification system, after job is completed, send email to the user or a webhook
# buy more points, or pay as you go option
# charts for the user - points, jobs, proxies, etc
# firebase bkend, need to add Access Token Generator endpoint
# add stripe payment gateway, unique payment link generator for each user how ? frontend ?



# DB tables
## users
    # email - user email (primary key) - string
    # uid - user id - string
    # points - user points - integer
    # plan - user plan - string
    # parallel_count - scraper parallel count - integer
    # config - user config - TEXT   # a json string

## jobs
    # job_id - job id (primary key) - string
    # user_email - user email (foreign key) - string
    # status - job status - string
    # urls - job urls - TEXT
    # proxies - job proxies - TEXT
    # created_at - job created at - datetime
    # parse_text - job parse text - boolean
    # parallel_count - job parallel count - integer
    # urls_scraped - job urls scraped - TEXT    # remove
    # urls_failed - job urls failed - TEXT
    # proxies_used - job proxies used - TEXT    # remove
    # proxies_failed - job proxies failed - TEXT
    # points_used - job points used - integer
    # zip_file_path - job zip file path - string
    # file_hash - job file hash - string md5

## logs
    # log_id - log id (primary key) - string
    # user_email - user email (foreign key) - string
    # log - log - TEXT
    # created_at - log created at - datetime




if __name__ == '__main__':
    # reload=True - server will automatically restart after code changes
    uvicorn.run('app:app', host='0.0.0.0', port=8083, reload=True)

# 184.174.126.249:6541:olmjtxsz:yccmlx17olxs
#
# {
#   "urls": [
#     "https://quickbooks.intuit.com/accountants/resources/marketing-hub/video/create-social-media-content/",
#     "https://quickbooks.intuit.com/time-tracking/resources/affordable-care-act-benefits/",
#     "https://quickbooks.intuit.com/desktop/enterprise/payroll-and-payments/"
#   ],
#   "proxies": [
#   "216.19.217.132:6372:olmjtxsz:yccmlx17olxs",
#   "134.73.64.103:6388:olmjtxsz:yccmlx17olxs",
#   "107.181.143.40:6171:olmjtxsz:yccmlx17olxs"
#   ]
# }