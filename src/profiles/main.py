from src.utils.base.libraries import logging, os, json
from src.utils.base.constants import OUTPUT_ROOT_DIR
from src.utils.base.basic import Error
from src.proxies.main import ProxyValidator
from src.utils.user.handler import User


class JobProfile:
    def __init__(self, user):
        self.user = user
        self.all_profiles = self.get_all_profiles()

    def get_all_profiles(self):
        try:
            all_job_profiles = {}
            profiles_dir = os.path.join(OUTPUT_ROOT_DIR, self.user["email"], "profiles")
            if os.path.exists(profiles_dir):
                for file in os.listdir(profiles_dir):
                    if file.endswith(".json"):
                        file_path = os.path.join(profiles_dir, file)
                        with open(file_path, 'r') as f:
                            profile_data = json.load(f)
                            all_job_profiles[file.split(".")[0]] = profile_data

            return all_job_profiles
        except Exception as e:
            logging.error(f"Error while getting all the profiles for user: {self.user['email']} with error: {e}")
            return Error(code=500, message="Error while getting all the profiles for user")

    def _write_json_file(self, file_path, data):
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logging.error(f"Error while writing the json file: {file_path} with error: {e}")
            return Error(code=500, message="Error while writing the json file")

    def _validate_profile_name(self, profile_name):
        """Validate the profile name"""
        if not isinstance(profile_name, str):
            return Error(code=412, message="Profile name must be a string")
        if not profile_name.isalnum():
            return Error(code=412, message="Profile name must be alphanumeric")
        if " " in profile_name:
            return Error(code=412, message="Profile name must not contain spaces")
        if len(profile_name) > 30:
            return Error(code=412, message="Profile name must be less than 30 characters")
        return True

    def _parallel_count_validator(self, given_parallel_count):
        """Validate the parallel count"""
        if not isinstance(given_parallel_count, int):
            return Error(code=412, message="Parallel count must be an integer")
        if given_parallel_count < 0:
            return Error(code=412, message="Parallel count must be greater than 0")
        
        # parallel_count validation
        user_obj = User()
        user_db_data = user_obj.get_user_data(self.user["email"], self.user["uid"], self.user["email_verified"])
        if isinstance(user_db_data, Error):
            return user_db_data

        user_parallel_count = user_db_data.get("parallel_count", 0)
        if given_parallel_count > user_parallel_count:
            return Error(code=412, message="Parallel count cannot be greater than allocated count")

        return True

    def create(self, profile_name, profile_data):
        """Create a new profile"""
        try:
            profile_file_path = os.path.join(OUTPUT_ROOT_DIR, self.user["email"], "profiles", f"{profile_name}.json")
            os.makedirs(os.path.dirname(profile_file_path), exist_ok=True)
            name_validator = self._validate_profile_name(profile_name)

            # Profile Validator
            if os.path.exists(profile_file_path):
                return Error(code=409, message="Profile already exists")
            if isinstance(name_validator, Error):
                return name_validator

            # parse_text validation
            parse_text = profile_data.get("parse_text", True)

            # proxies validation
            proxies = profile_data.get("proxies", [])
            if not isinstance(proxies, list):
                return Error(code=412, message="proxies must be a list")
            
            proxy_validator_obj = ProxyValidator(proxies)
            if isinstance(proxy_validator_obj, Error):
                return proxy_validator_obj
            
            parallel_count = profile_data.get("parallel_count", None)
            if parallel_count:
                parallel_count_validator = self._parallel_count_validator(parallel_count)
                if isinstance(parallel_count_validator, Error):
                    return parallel_count_validator
            else:
                user_obj = User()
                user_db_data = user_obj.get_user_data(self.user["email"], self.user["uid"], self.user["email_verified"])
                if isinstance(user_db_data, Error):
                    return user_db_data
                parallel_count = user_db_data.get("parallel_count", 0)
            

            profile_data = {
                "parallel_count": parallel_count,
                "parse_text": parse_text,
                "proxies": proxy_validator_obj.valid_proxies
            }

            # write the profile file
            if not self._write_json_file(profile_file_path, profile_data):
                return Error(code=500, message="Error while writing the profile file")

            # update the all profiles dict
            self.all_profiles[profile_name] = profile_data

            return True
        except Exception as e:
            logging.error(f"Error while creating the profile: {profile_name} for user: {self.user['email']} with error: {e}")
            return Error(code=500, message="Error while creating the profile")

    def update(self, profile_name, profile_data):
        """Update an existing profile"""
        try:
            profile_file_path = os.path.join(OUTPUT_ROOT_DIR, self.user["email"], "profiles", f"{profile_name}.json")
            if not os.path.exists(profile_file_path):
                return Error(code=404, message="Profile does not exists")
            
            # read the profile file
            with open(profile_file_path, 'r') as f:
                old_profile_data = json.load(f)

            parse_text = profile_data.get("parse_text", old_profile_data.get("parse_text", True))
            proxies = profile_data.get("proxies", old_profile_data.get("proxies", []))
            parallel_count = profile_data.get("parallel_count", old_profile_data.get("parallel_count", 0))

            # parse_text validation
            if not isinstance(parse_text, bool):
                return Error(code=412, message="parse_text must be a boolean")

            # proxies validation
            if not isinstance(proxies, list):
                return Error(code=412, message="proxies must be a list")
            
            proxy_validator_obj = ProxyValidator(proxies)
            if isinstance(proxy_validator_obj, Error):
                return proxy_validator_obj
            
            if parallel_count:
                parallel_count_validator = self._parallel_count_validator(parallel_count)
                if isinstance(parallel_count_validator, Error):
                    return parallel_count_validator
            
            profile_data = {
                "parallel_count": parallel_count,
                "parse_text": parse_text,
                "proxies": proxy_validator_obj.valid_proxies
            }

            # write the profile file
            if not self._write_json_file(profile_file_path, profile_data):
                return Error(code=500, message="Error while writing the profile file")
            
            # update the all profiles dict
            self.all_profiles[profile_name] = profile_data

            return True

        except Exception as e:
            logging.error(f"Error while updating the profile: {profile_name} for user: {self.user['email']} with error: {e}")
            return Error(code=500, message="Error while updating the profile")

    def delete(self, profile_name):
        """Delete an existing profile"""
        try:
            profile_file_path = os.path.join(OUTPUT_ROOT_DIR, self.user["email"], "profiles", f"{profile_name}.json")
            if not os.path.exists(profile_file_path):
                return Error(code=404, message="Profile does not exists")
            # delete the profile file
            os.remove(profile_file_path)
            # update the all profiles dict
            del self.all_profiles[profile_name]

            return True

        except Exception as e:
            logging.error(f"Error while deleting the profile: {profile_name} for user: {self.user['email']} with error: {e}")
            return Error(code=500, message="Error while deleting the profile")

