from datetime import datetime
import requests
import json
import re
import traceback
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import logging
import toml
from croniter import croniter
import time
import os
from dateutil import tz
import signBuilder
from config import Config

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create handlers
fileHandler = logging.FileHandler('wozaixiaoyuan.log')
consoleHandler = logging.StreamHandler()

# Create formatters and add them to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fileHandler.setFormatter(formatter)
consoleHandler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)


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
            sign_info = signBuilder.filterSignList(data['data']) 
            logging.debug(sign_info)   
            self.sign_data =  sign_info
            logging.info("Sign-in list retrieved successfully!")
        else:
            logging.error("Failed to retrieve sign-in list!")


    def night_sign(self):
        self.get_sign_list()
        if len(self.sign_data) == 0:
            logging.info("No sign-in task found!")
            return
        for i, sign in  enumerate(self.sign_data):
            logging.debug(f"Sign-in data: {sign}")
            check_in_data = self.sign_data[i]['signBody']
            logging.debug(f"Check-in data: {check_in_data}")
            headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
            id_ = sign.get('id')
            sign_id = sign.get('signId')
            url = self.sign_data[i]['signUrl'].format(id_, self.school_id, sign_id)
            logging.debug(f"Request URL: {url}")
            res = requests.post(url, headers=headers, data=check_in_data)
            text = json.loads(res.text)
            if text['code'] == 0:
                logging.info("sign-in successful!")
            else:
                logging.error("sign-in failed!")
            logging.debug(f"Response: {text}")


def run_users():
    """
    Runs the night sign-in for multiple users.

    Returns:
        None
    """
    cfg = Config()
    data = cfg.get_user_data()

    for i, user_data in enumerate(data):
        if i != 0:
            print("-" * 50)  # Separator between different users
        logging.info(f"Running user {user_data.get('name')}...")
        try:
            u = User(user_data.get('username'), user_data.get('password'), user_data.get('school_id'))
            u.night_sign()
        except Exception as e:
            logging.error(f"An error occurred while running user {user_data.get('name')}: {str(e)}")
            logging.error(traceback.format_exc())
        if i == len(data) - 1:
            print("-" * 50)


if __name__ == "__main__":
    # judge whether is the development environment
    if os.environ.get('ENV') == 'DEV':
        # Set the logging level to DEBUG
        logger.setLevel(logging.DEBUG)
        # Run the script
        run_users()
        exit(0)

    # Read cron expression from configuration file
    try:
        cfg = Config()
    except ValueError as e:
        logging.error(str(e))
        exit(1)

    cronExpression = cfg.get_cron_data()

    now = datetime.now().replace(tzinfo=tz.gettz()) 

    # Create a cron iterator
    cron = croniter(cronExpression,now)

    # Log the welcome message
    logging.info("Welcome to Wozaixiaoyuan Night Sign-in Script!")

    # Infinite loop to check if it's time to execute the task
    while True:
        # Get the next scheduled time
        nextRunTime = cron.get_next(float)

        logging.info(f"Next scheduled run time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nextRunTime))}")

        # Calculate the delay until the next scheduled time
        delay = nextRunTime - time.time()

        # Sleep until the next scheduled time
        if delay > 0:
            time.sleep(delay)

        # Execute the task
        run_users()
