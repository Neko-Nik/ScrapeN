from src.utils.user.postgresql import UserPostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager
from src.utils.base.basic import Error
from src.utils.base.basic import retry


class User:
    def __init__(self):
        self.db = UserPostgreSQLCRUD()
        self.stripe = StripeManager()


    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def create(self, email, name, uid, is_active, points, tier, parallel_count):
        self.db.create(email, name, uid, is_active, points, tier, parallel_count)


    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def read(self, email=None):
        return self.db.read(email)


    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def update(self, email, new_data):
        self.db.update(email, new_data)


    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def delete(self, email):
        self.db.delete(email)


    def handle_user_creation_get(self, email, name=None, uid=None, is_active=False, points=100, tier="FREE", parallel_count=1):
        try:
            user = self.read(email)
            stripe_data = None
            stripe_plan = None

            if not user:
                self.create(email, name, uid, is_active, points, tier, parallel_count)
                user = self.read(email)

                stripe_data = self.stripe.create_stripe_customer(email)
                stripe_plan = self.stripe.get_current_plan(email)
            
            if user[0][5] == "DELETED":
                self.update(email, {"points": points, "tier": tier, "parallel_count": parallel_count, "is_active": is_active})
                stripe_data = self.stripe.create_stripe_customer(email)
                stripe_plan = self.stripe.get_current_plan(email)

            return user[0], stripe_data, stripe_plan
        except Exception as err:
            print(f"Error: {err}")
            return []

    def handle_user_deletion(self, email):
        try:
            self.update(email, {"points": -1, "tier": "DELETED", "parallel_count": 0, "is_active": False})
            self.stripe.delete_stripe_customer(email)
            return True
        except Exception as err:
            print(f"Error: {err}")
            return False


    def _get_points(self, email):
        try:
            user = self.read(email)
            if not user:
                return Error(code=404, message="User not found")

            return user[0][4]
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

            self.update(email, {"points": user_points - points})
            return True
        except Exception as err:
            print(f"Error: {err}")
            return False

