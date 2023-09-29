"""All notifications related functions"""


from src.utils.base.libraries import logging, requests, validators
from src.utils.base.basic import Error, retry
from src.utils.user.postgresql import UserPostgreSQLCRUD


class NotificationWebhook:
    def __init__(self, webhook_url: str, data: dict, email: str):
        self.userDB = UserPostgreSQLCRUD()
        self.webhook_url = webhook_url
        self.is_valid = False
        self.error = None
        self.validate_webhook_url()
        self.data = data
        self.email = email

    def validate_webhook_url(self):
        # Check if the webhook_url is a valid URL
        if not validators.url(self.webhook_url):
            self.error = Error(code=400, message="Webhook URL is not a valid URL")

        # Check if the URL is reachable
        try:
            response = requests.head(self.webhook_url)
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            self.is_valid = True
        except requests.exceptions.RequestException:
            self.error = Error(code=400, message="Webhook URL is not reachable")

        # Check if the URL supports the HTTP POST method
        if 'POST' not in response.headers.get('allow', ''):
            self.error = Error(code=400, message="Webhook URL does not support POST method")

    def set_webhook_url_db(self):
        if not self.is_valid:
            return self.error
        userDB = UserPostgreSQLCRUD()
        configured_correctly = userDB.update_config(self.email, {"webhook_url": self.webhook_url})
        return configured_correctly

    @retry(Exception, total_tries=3, initial_wait=1, backoff_factor=2 )
    def call_webhook(self):
        resp = requests.post(self.webhook_url, json=self.data)
        if resp.status_code != 200:
            raise Exception(f"Webhook call failed with status code {resp.status_code}")


class NotificationsEmail:
    def __init__(self):
        pass

    def send_email(self, email, subject, body):
        pass