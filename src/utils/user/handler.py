from src.utils.user.postgresql import PostgreSQLCRUD
from src.utils.user.stripe_manager import StripeManager


class User:
    def __init__(self):
        self.db = PostgreSQLCRUD()
        self.stripe = StripeManager()

    def create(self, email, name, uid, is_active, points, tier):
        try:
            self.db.create(email, name, uid, is_active, points, tier)
        except Exception as err:
            print(f"Error: {err}")

    def read(self, email=None):
        try:
            return self.db.read(email)
        except Exception as err:
            print(f"Error: {err}")
            return []
        
    def update(self, email, new_data):
        try:
            self.db.update(email, new_data)
        except Exception as err:
            print(f"Error: {err}")

    def delete(self, email):
        try:
            self.db.delete(email)
        except Exception as err:
            print(f"Error: {err}")

    def handle_user_creation_get(self, email, name=None, uid=None, is_active=None, points=None, tier=None):
        try:
            user = self.read(email)

            if not user:
                is_active = 1 if is_active else 0
                self.create(email, name, uid, is_active, points, tier)
                user = self.read(email)
            # handle stripe customer creation
            stripe_data = self.stripe.create_stripe_customer(email)
            stripe_plan = self.stripe.get_current_plan(email)

            return user[0], stripe_data, stripe_plan
        except Exception as err:
            print(f"Error: {err}")
            return []

    def handle_user_deletion(self, email):
        try:
            self.delete(email)
            self.stripe.delete_stripe_customer(email)
            return True
        except Exception as err:
            print(f"Error: {err}")
            return False

    def deduct_points(self, email, points=1):
        try:
            user = self.read(email)
            if not user:
                return False

            new_points = user[0][4] - points
            if new_points <= -1:
                return False
            else:
                self.update(email, {"points": new_points})
                return True
        except Exception as err:
            print(f"Error: {err}")
            return False

