from src.utils.base.libraries import BaseModel, wraps, time, logging



class Error(BaseModel):
    code: int
    message: str

    def __str__(self) -> str:
        return f"Error: {self.code} - {self.message}"


def retry(exceptions, total_tries=4, initial_wait=0.5, backoff_factor=2, logger=None):
    """
    calling the decorated function applying an exponential backoff.
    Args:
        exceptions: Exception(s) that trigger a retry, can be a tuple
        total_tries: Total tries
        initial_wait: Time to first retry
        backoff_factor: Backoff multiplier (e.g. value of 2 will double the delay each retry).
        logger: logger to be used, if none specified print
    """

    def retry_decorator(f):
        @wraps(f)
        def func_with_retries(*args, **kwargs):
            _tries, _delay = total_tries + 1, initial_wait
            while _tries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    _tries -= 1
                    print_args = ', '.join(map(str, args)) if args else 'no args'
                    function_name = f.__name__
                    exception_message = repr(e)
                    if _tries == 1:
                        # Constructing the message separately
                        msg = "Function: " + function_name + "\n" + \
                              "Failed despite best efforts after " + str(total_tries) + " tries.\n" + \
                              "args: " + print_args + ", kwargs: " + str(kwargs) + "\n" + \
                              "Exception: " + exception_message + "\n"
                        logging.error(f"msg: {msg}, logger: {logger}")
                        raise
                    # Same for the retry message
                    msg = "Function: " + function_name + "\n" + \
                          "Exception: " + exception_message + "\n" + \
                          "Retrying in " + str(_delay) + " seconds!, args: " + print_args + ", kwargs: " + str(kwargs) + "\n"
                    logging.warning(f"msg: {msg}, logger: {logger}")
                    time.sleep(_delay)
                    _delay *= backoff_factor

        return func_with_retries

    return retry_decorator