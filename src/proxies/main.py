from src.utils.base.constants import OUTPUT_ROOT_DIR
from src.utils.base.libraries import json, os, logging, re, FileLock
from src.utils.base.basic import Error


class ProxyValidator:
    def __init__(self, proxies):
        self.proxies = proxies
        self.valid_proxies = []
        self.invalid_proxies = []
        self.validate()
    
    def __str__(self):
        return f"Valid proxies: {len(self.valid_proxies)}, Invalid proxies: {len(self.invalid_proxies)}"

    def validate(self):
        # TODO: Add more validation checks
        # TODO: add the error message to the user logs
        # Define the regex pattern for the expected format
        pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+:[\w\d]+:[\w\d]+$'
        try:
            self.proxies = list(set(self.proxies))
            for proxy in self.proxies:
                if re.match(pattern, proxy):
                    self.valid_proxies.append(proxy)
                else:
                    self.invalid_proxies.append(proxy)
        except Exception as e:
            logging.error(f"Error validating proxies: {str(e)}")
            raise Error(code=500, message=f"Error validating proxies: {str(e)}")


class Proxies:
    def __init__(self, user):
        self.user = user
        self.proxies_file = os.path.join(OUTPUT_ROOT_DIR, user['email'], 'proxies.json')
        self.lock = FileLock(self.proxies_file + ".lock")
        self.load_proxies()

    def __str__(self):
        return f"Total proxies: {len(self.proxies)}"
    
    def __len__(self):
        return len(self.proxies)

    def load_proxies(self):
        try:
            with self.lock:
                if not os.path.exists(self.proxies_file):
                    self.proxies = []
                    self.save_proxies()
                else:
                    with open(self.proxies_file, 'r') as file:
                        self.proxies = json.load(file)
        except Exception as e:
            logging.error(f"Error loading proxies: {str(e)}")
            raise Error(code=500, message=f"Error loading proxies: {str(e)}")

    def save_proxies(self):
        try:
            with self.lock:
                self.proxies = list(set(self.proxies))
                with open(self.proxies_file, 'w') as file:
                    json.dump(self.proxies, file)
        except Exception as e:
            logging.error(f"Error saving proxies: {str(e)}")
            raise Error(code=500, message=f"Error saving proxies: {str(e)}")

    def add(self, proxy):
        try:
            with self.lock:
                self.proxies.append(proxy)
                self.save_proxies()
        except Exception as e:
            logging.error(f"Error adding proxy: {str(e)}")
            raise Error(code=500, message=f"Error adding proxy: {str(e)}")

    def remove(self, proxy):
        try:
            with self.lock:
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
                    self.save_proxies()
        except Exception as e:
            logging.error(f"Error removing proxy: {str(e)}")
            raise Error(code=500, message=f"Error removing proxy: {str(e)}")

    def delete(self, delete_list: list=[]) -> bool:
        try:
            if delete_list:
                with self.lock:
                    for proxy in delete_list:
                        if proxy in self.proxies:
                            self.proxies.remove(proxy)
                    self.save_proxies()

            else:
                self.delete_all()
        except Exception as e:
            logging.error(f"Error deleting proxy: {str(e)}")
            raise Error(code=500, message=f"Error deleting proxy: {str(e)}")
        
        return True

    def delete_all(self):
        try:
            with self.lock:
                if os.path.exists(self.proxies_file):
                    os.remove(self.proxies_file)
                    if os.path.exists(self.proxies_file + ".lock"):
                        os.remove(self.proxies_file + ".lock")
                self.proxies = []
        except Exception as e:
            logging.error(f"Error deleting proxies: {str(e)}")
            raise Error(code=500, message=f"Error deleting proxies: {str(e)}")

    def update(self, proxies):
        try:
            with self.lock:
                self.proxies += proxies
                self.save_proxies()
            return True
        except Exception as e:
            logging.error(f"Error updating proxies: {str(e)}")
            return Error(code=412, message=f"Error while updating proxies, please contact support")

