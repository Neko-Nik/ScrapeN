from src.utils.user.postgresql import UserPostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager
from src.utils.base.basic import Error, retry
from src.utils.base.libraries import json


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
            print(f"Error: {err}")
            return {"error": "Internal Server Error"}

    def handle_user_deletion(self, email):
        try:
            self.db.delete(email)
            return True
        except Exception as err:
            # since many tables are dependent on user table, we need to delete them first
            print(f"Error: {err}")
            return False

    def _get_points(self, email):
        try:
            user = self.db.read(email)
            if not user:
                return Error(code=404, message="User not found")
            return user["points"]

        except Exception as err:
            print(f"Error: {err}")
            return Error(code=500, message="Internal Server Error")


    def deduct_points(self, email, points):
        # Deduct only once at the start or at the end of the process
        try:
            user_points = self._get_points(email)
            if isinstance(user_points, Error):
                return user_points
            
            if user_points == -1:
                return False

            if user_points - points < 0:
                return False
            self.db.update(email, {"points": user_points - points})
            return True

        except Exception as err:
            print(f"Error: {err}")
            return False

