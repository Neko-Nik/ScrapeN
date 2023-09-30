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
    RateLimitExceeded,
    StaticFiles
)
from src.utils.base.constants import NUMBER_OF_LOGS_TO_DISPLAY, OUTPUT_ROOT_DIR
from src.main import render_scrape
from src.sitemap.main import Sitemap
from src.utils.user.auth import get_user_token
from src.utils.user.handler import User
from src.scraping.main import ProcessJob
from src.utils.base.basic import Error
from src.utils.user.postgresql import JobPostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager
from src.proxies.main import ProxyValidator, Proxies
from src.profiles.main import JobProfile
from src.utils.user.notifications import NotificationWebhook


# Initialization
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Neko Nik - ScrapeN API",
    description="This ScrapeN API is used to scrape data from the web",
    version="1.7.7",
    docs_url="/docs",
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

# Download Static files
app.mount("/download", app=StaticFiles(directory=OUTPUT_ROOT_DIR), name="Download Job Files")

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
def view_logs(request: Request, passwd: str="") -> HTMLResponse:
    """
    This endpoint is used to view the logs of the API in a web page
    Just go to /logs to view the logs
    """
    if passwd != "Neko_Nik_777":
        return HTMLResponse( status_code=status.HTTP_404_NOT_FOUND, content="Not Found" )
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


@app.get("/job", response_class=JSONResponse, tags=["Job"], summary="Job one or all job details")
def job_status(request: Request, job_id: str=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to scrape status of the job id
    or if job id is not given, then it will return all the jobs of the user
    """
    try:
        if job_id:
            job_uid = user["email"] + "|" + job_id
            job_obj = JobPostgreSQLCRUD()
            job_data = job_obj.read(job_uid=job_uid)
            if not job_data:
                return JSONResponse( status_code=status.HTTP_404_NOT_FOUND, content={"message": "Job not found, please check the job id"} )
        else:
            job_obj = JobPostgreSQLCRUD()
            job_data = job_obj.filter_by_email(email=user["email"])

        if isinstance(job_data, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": job_data.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content=job_data )
    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.post("/job", response_class=JSONResponse, tags=["Job"], summary="Create a new job")
@limiter.limit("1/2 second")
def create_job(request: Request, background_tasks: BackgroundTasks, profile_name: str, urls: list, job_name: str=None, job_description: str=None, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to create a new job, n number of urls and proxies can be passed, even 1 url and 1 proxy can be passed
    """
    try:
        process_job_obj = ProcessJob(urls=urls, user=user, profile_name=profile_name, job_name=job_name, job_description=job_description)
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
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            proxies = json.loads(content)
            if (not isinstance(proxies, list)) or (not all(isinstance(proxy, str) for proxy in proxies)):
                return JSONResponse( status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid file format, please upload a proper json file, with list of proxies as strings"} )

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


@app.put("/notification/webhook", response_class=JSONResponse, tags=["Notification"], summary="Set webhook url for notifications")
def set_webhook_notification(request: Request, url: str, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to set webhooks for notifications of the job by the user
    When the job is completed, the user will get a notification on the given url, we will send the job id and status,
    basically we will send the same response as the job status endpoint
    """
    try:
        configured_correctly = NotificationWebhook(webhook_url=url, data={}, email=user["email"]).set_webhook_url_db()
        if isinstance(configured_correctly, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": configured_correctly.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Webhook url set successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.delete("/notification/webhook", response_class=JSONResponse, tags=["Notification"], summary="Delete webhook url for notifications")
def delete_webhook_notification(request: Request, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to delete webhooks for notifications of the job by the user
    """
    try:
        print(user)
        configured_correctly = NotificationWebhook(webhook_url="", data={}, email=user["email"]).delete_webhook_url_db()
        if isinstance(configured_correctly, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": configured_correctly.message} )

        return JSONResponse( status_code=status.HTTP_200_OK, content={"message": "Webhook url deleted successfully"} )

    except Exception as exc_info:
        logging.error(exc_info)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


@app.post("/scrape/sitemap", response_class=JSONResponse, tags=["Scrape"], summary="Scrape sitemap of the given xml sitemap urls")
async def xml_sitemap_scraper(request: Request, website_urls: list, do_nested: bool=False, user: dict=Depends(get_user_token)) -> JSONResponse:
    """
    This endpoint is used to scrape sitemap of the given xml sitemap urls
    """
    try:
        sitemap_obj = Sitemap(user=user, xml_urls=website_urls, do_nested=do_nested)
        urls = sitemap_obj.run()
        if isinstance(urls, Error):
            return JSONResponse( status_code=status.HTTP_412_PRECONDITION_FAILED, content={"message": urls.message} )
        return JSONResponse( status_code=status.HTTP_200_OK, content=urls )

    except Exception as exc_info:
        logging.error(exc_info, exc_info=True)
        raise All_Exceptions( "Something went wrong", status.HTTP_500_INTERNAL_SERVER_ERROR )


# 25-30% usage for workers of 30 parallel count
# buy more points, or pay as you go option
# firebase bkend, need to add Access Token Generator endpoint
# add stripe payment gateway, unique payment link generator for each user how ? frontend ?




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