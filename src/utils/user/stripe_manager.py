import stripe

class StripeManager:
    def __init__(self):
        stripe.api_key = "sk_test_51NbdcnSG8jX2WdcmZA7QQaWe4GoKY9wVNEWZV2E3SkHL5Ymbds1d4DWBUVZeWbwAc5gxoQOsqgXojs7lpLI0QLG300CRSSIzRo"

    def _check_customer_exists(self, email):
        try:
            customer_list = stripe.Customer.list(email=email)
            return len(customer_list.data) > 0
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return False

    def _get_stripe_customer(self, email):
        if not self._check_customer_exists(email):
            print(f"Customer with email '{email}' doesn't exist.")
            return None

        try:
            customer_list = stripe.Customer.list(email=email)
            return customer_list.data[0]
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return None
    
    def _get_stripe_customer_subscriptions(self, email):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

        try:
            subscriptions = stripe.Subscription.list(customer=customer.id)
            return subscriptions.data
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return None

    def create_stripe_customer(self, email, metadata=None):
        if self._check_customer_exists(email):
            print(f"Customer with email '{email}' already exists.")
            customer = self._get_stripe_customer(email)
            return customer

        try:
            customer = stripe.Customer.create(
                email=email,
                metadata=metadata
            )
            return customer
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return None

    def get_current_plan(self, email):
        subscriptions = self._get_stripe_customer_subscriptions(email)
        if not subscriptions:
            return None

        try:
            user_plan = subscriptions[0].plan
            return user_plan
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return None

    def create_user_payment_link(self, email, plan_id):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

        try:
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=["card"],
                subscription_data={
                    "items": [{
                        "plan": plan_id
                    }]
                },
                success_url="https://scrape.nekonik.com/dashboard",
                cancel_url="https://scrape.nekonik.com/dashboard",
            )
            return checkout_session.url
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return None

    def delete_stripe_customer(self, email):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

        try:
            get_current_plan = self.get_current_plan(email)
            if get_current_plan:
                stripe.Subscription.delete(get_current_plan.id)
            customer.delete()
            return True
        except stripe.error.StripeError as err:
            print(f"Error: {err}")
            return False

