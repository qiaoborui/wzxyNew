import requests
import json
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import logging
import toml
from croniter import croniter
import time

logging.basicConfig(level=logging.INFO)

class User:
    def __init__(self, username, password, school_id):
        self.username = username
        self.password = password
        self.school_id = school_id
        self.sign_data = []
        self.cookie = None

        # Try to read JWSESSION from local cache and test login status
        self.test_cached_session()

    def encrypt(self, text):
        key = (str(self.username) + "0000000000000000")[:16]
        cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        padded_text = pad(text.encode('utf-8'), AES.block_size)
        encrypted_text = cipher.encrypt(padded_text)
        return b64encode(encrypted_text).decode('utf-8')

    def login(self):
        encrypted_text = self.encrypt(self.password)
        login_url = 'https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username'
        params = {
            "schoolId": self.school_id,
            "username": self.username,
            "password": encrypted_text
        }
        login_req = requests.post(login_url, params=params)
        text = json.loads(login_req.text)
        if text['code'] == 0:
            set_cookie = login_req.headers['Set-Cookie']
            jws = re.search(r'JWSESSION=.*?;', str(set_cookie)).group(0)
            self.cookie = jws
            self.write_jws_to_cache({self.username: jws})  # Write obtained JWSESSION to local cache
            return True
        else:
            logging.error(f"{self.username} login error, please check account password!")
            return False

    def test_login_status(self):
        if self.cookie:
            headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
            url = "https://gw.wozaixiaoyuan.com/health/mobile/health/getBatch"
            res = requests.get(url, headers=headers)
            text = json.loads(res.text)
            if text['code'] == 0:
                return True
            elif text['code'] == 103:
                return False
            else:
                return 0
        else:
            logging.error("Please log in first!")
            return False
    
    def write_jws_to_cache(self, jws_dict):
        try:
            with open("users_jws.json", 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        data.update(jws_dict)

        with open("users_jws.json", 'w') as file:
            json.dump(data, file)

    def read_jws_from_cache(self):
        try:
            with open("users_jws.json", 'r') as file:
                jws_dict = json.load(file)
                return jws_dict
        except FileNotFoundError:
            return {}

    def test_cached_session(self):
        cached_jws = self.read_jws_from_cache()
        if cached_jws:
            self.cookie = cached_jws.get(self.username)
            if self.cookie:
                # Test login status
                if self.test_login_status():
                    return
                else:
                    logging.error("JWSESSION in local cache expired, re-login...")
                    # Re-login
                    if self.login():
                        logging.info("Re-login successful!")
                    else:
                        logging.error("Re-login failed, please check account password!")
            else:
                logging.error(f"JWSESSION not found in local cache for user {self.username}")
                if self.login():
                    logging.info("Login successful!")
                else:
                    logging.error("Login failed, please check account password!")
        else:
            logging.error("No JWSESSION found in local cache, starting login...")
            # Login
            if self.login():
                logging.info("Login successful!")
            else:
                logging.error("Login failed, please check account password!")

    def get_sign_list(self):
        if not self.cookie:
            logging.error("Please log in first!")
            return

        headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
        url = "https://gw.wozaixiaoyuan.com/sign/mobile/receive/getMySignLogs?page=1&size=10"
        res = requests.get(url, headers=headers)
        data = json.loads(res.text)

        if 'code' in data and data['code'] == 0 and 'data' in data:
            for item in data['data']:
                if item.get('type') ==  0 and item.get('signStatus') == 1:
                    sign_info = {'signId': item.get('signId'), 'id': item.get('id'),'userArea':item.get('userArea'),'areaList':item.get('areaList')}
                    self.sign_data.append(sign_info)
            logging.info("Sign-in list retrieved successfully!")
        else:
            logging.error("Failed to retrieve sign-in list!")

    def generate_check_in_request(self, area_list, user_area):
        check_in_data = {}
        area_json_data = self.find_area_json(area_list, user_area)
        if area_json_data:
            area_json, latitude, longitude = area_json_data
            check_in_data = {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "nationcode": "156",
                "country": "China",
                "areaJSON": area_json,
                "inArea": 1
            }
        return json.dumps(check_in_data)

    def find_area_json(self, area_list, user_area):
        for area in area_list:
            if area.get('name') == user_area:
                area_json = {
                    "type": 0,
                    "circle": {
                        "latitude": area.get('latitude'),
                        "longitude": area.get('longitude'),
                        "radius": area.get('radius')
                    },
                    "id": area.get('id'),
                    "name": area.get('name')
                }
                return (json.dumps(area_json), area.get('latitude'), area.get('longitude'))
        return None

    def night_sign(self):
        self.get_sign_list()
        if (sign_count := len(self.sign_data)) == 0:
            logging.info("No sign-in task found!")
            return
        for sign in self.sign_data:
            check_in_data = self.generate_check_in_request(sign.get('areaList'), sign.get('userArea'))
            headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
            id_ = sign.get('id')
            sign_id = sign.get('signId')
            url = f"https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByArea?id={id_}&schoolId={self.school_id}&signId={sign_id}"
            res = requests.post(url, headers=headers, data=check_in_data)
            text = json.loads(res.text)
            if text['code'] == 0:
                logging.info(f"{sign.get('userArea')} sign-in successful!")
            else:
                logging.error(f"{sign.get('userArea')} sign-in failed!")


def run_users():
    with open('users.toml', 'r') as file:
        data = toml.load(file)['user']

    for i, user_data in enumerate(data):
        if i != 0:
            print("-" * 50)  # Separator between different users
        logging.info(f"Running user {user_data.get('name')}...")
        try:
            u = User(user_data.get('username'), user_data.get('password'), user_data.get('school_id'))
            u.night_sign()
        except Exception as e:
            logging.error(f"An error occurred while running user {user_data.get('name')}: {str(e)}")
        if i == len(data) - 1:
            print("-" * 50)

if __name__ == "__main__":
    # Define your cron expression here
    cron_expression = "* * * * *"  # Runs at 1:00 AM every day

    # Create a cron iterator
    cron = croniter(cron_expression)

    # Infinite loop to check if it's time to execute the task
    while True:
        # Get the next scheduled time
        next_run_time = cron.get_next(float)

        # Calculate the delay until the next scheduled time
        delay = next_run_time - time.time()

        # Sleep until the next scheduled time
        if delay > 0:
            time.sleep(delay)

        # Execute the task
        run_users()