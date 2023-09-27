import stripe
from src.utils.base.basic import retry


import json
def save_to_json_file(file_path, data):
    with open(file_path, 'w') as outfile:
        json.dump(data, outfile, indent=4)


class StripePlanManager:
    def __init__(self, event_data):
        stripe.api_key = "sk_test_51NbdcnSG8jX2WdcmZA7QQaWe4GoKY9wVNEWZV2E3SkHL5Ymbds1d4DWBUVZeWbwAc5gxoQOsqgXojs7lpLI0QLG300CRSSIzRo"
        self.event_data = event_data

    # If any issue do only one thing: raise error don't return false or something else

    def handle_sub_creation(self, subscription):
        print("Subscription created")
        save_to_json_file("subscription_created.json", subscription)

    def handle_sub_deletion(self, subscription):
        print("Subscription deleted")
        save_to_json_file("subscription_deleted.json", subscription)

    def handle_sub_update(self, subscription):
        print("Subscription updated")
        save_to_json_file("subscription_updated.json", subscription)


class StripeManager:
    def __init__(self):
        stripe.api_key = "sk_test_51NbdcnSG8jX2WdcmZA7QQaWe4GoKY9wVNEWZV2E3SkHL5Ymbds1d4DWBUVZeWbwAc5gxoQOsqgXojs7lpLI0QLG300CRSSIzRo"
        self.webhook_signing_secret = "whsec_82gOhSl2mKaqMKMeKUGz00aHgyA2YmPC"

    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def _check_customer_exists(self, email):
        customer_list = stripe.Customer.list(email=email)
        return len(customer_list.data) > 0


    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def _get_stripe_customer(self, email):
        if not self._check_customer_exists(email):
            print(f"Customer with email '{email}' doesn't exist.")
            return None

        customer_list = stripe.Customer.list(email=email)
        return customer_list.data[0]
    

    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def _get_stripe_customer_subscriptions(self, email):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

        subscriptions = stripe.Subscription.list(customer=customer.id)
        return subscriptions.data

    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def create_stripe_customer(self, email, metadata=None):
        if self._check_customer_exists(email):
            print(f"Customer with email '{email}' already exists.")
            customer = self._get_stripe_customer(email)
            return customer

        customer = stripe.Customer.create(
            email=email,
            metadata=metadata
        )
        return customer

    def get_current_plan(self, email):
        subscriptions = self._get_stripe_customer_subscriptions(email)
        if not subscriptions:
            return None

        user_plan = subscriptions[0].plan
        return user_plan

    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def create_user_payment_link(self, email, plan_id):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

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
        
    @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def delete_stripe_customer(self, email):
        customer = self._get_stripe_customer(email)
        if not customer:
            return None

        get_current_plan = self.get_current_plan(email)
        if get_current_plan:
            stripe.Subscription.delete(get_current_plan.id)
        customer.delete()
        return True

    # @retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
    def webhook_handler(self, payload, sig_header):
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_signing_secret)
        except ValueError as e:
            # Invalid payload
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise e
        
        if not event:
            raise ValueError("Event is empty") # or return false

        plan_manager = StripePlanManager(event)

        match event['type']:
            case 'customer.subscription.created':
                plan_manager.handle_sub_creation(event['data']['object'])
            case 'customer.subscription.deleted':
                plan_manager.handle_sub_deletion(event['data']['object'])
            case 'customer.subscription.updated':
                plan_manager.handle_sub_update(event['data']['object'])
            case _:
                print(f"Unhandled event type {event['type']}")

