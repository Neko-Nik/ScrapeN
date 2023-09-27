from src.utils.user.postgresql import UserPostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager
from src.utils.base.basic import Error
from src.utils.base.libraries import json, logging


class User:
    def __init__(self):
        self.db = UserPostgreSQLCRUD()
        self.stripe = StripeManager()

    def get_user_data(self, email, uid, verified):
        try:
            user = self.db.read(email)

            if not user:
                self.db.create(email=email, uid=uid, points=10)
                stripe_data = self.stripe.create_stripe_customer(email)
                config_data = json.dumps({"email_verified": verified, "stripe_customer_data": stripe_data})
                self.db.update(email, {"config": config_data})
                user = self.db.read(email)            
            user["config"] = json.loads(user["config"])
            return user

        except Exception as err:
            logging.error(f"Error while getting user data: {err}")
            return Error(code=500, message="Error while getting user data from DB or Creating user or Creating stripe customer")

    def handle_user_deletion(self, email):
        try:
            has_user_deleted = self.db.delete(email)
            return has_user_deleted
        except Exception as err:
            # since many tables are dependent on user table, we need to delete them first
            logging.error(f"Error while deleting user: {err} \n\n This error is expected if the user has linked data across other tables")
            return Error(code=500, message="Error while deleting user data from DB")
