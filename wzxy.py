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
    def __init__(self, username, password, schoolId):
        self.username = username
        self.password = password
        self.schoolId = schoolId
        self.signData = []
        self.cookie = None

        # Try to read JWSESSION from local cache and test login status
        self.testCachedSession()

    def encrypt(self, text):
        key = (str(self.username) + "0000000000000000")[:16]
        cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        paddedText = pad(text.encode('utf-8'), AES.block_size)
        encryptedText = cipher.encrypt(paddedText)
        return b64encode(encryptedText).decode('utf-8')

    def login(self):
        encryptedText = self.encrypt(self.password)
        loginUrl = 'https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username'
        params = {
            "schoolId": self.schoolId,
            "username": self.username,
            "password": encryptedText
        }
        loginReq = requests.post(loginUrl, params=params)
        text = json.loads(loginReq.text)
        if text['code'] == 0:
            setCookie = loginReq.headers['Set-Cookie']
            jws = re.search(r'JWSESSION=.*?;', str(setCookie)).group(0)
            self.cookie = jws
            self.writeJwsToCache({self.username: jws})  # Write obtained JWSESSION to local cache
            return True
        else:
            logging.error(f"{self.username} login error, please check account password!")
            return False

    def testLoginStatus(self):
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
    
    def writeJwsToCache(self, jwsDict):
        try:
            with open("users_jws.json", 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        data.update(jwsDict)

        with open("users_jws.json", 'w') as file:
            json.dump(data, file)

    def readJwsFromCache(self):
        try:
            with open("users_jws.json", 'r') as file:
                jwsDict = json.load(file)
                return jwsDict
        except FileNotFoundError:
            return {}

    def testCachedSession(self):
        cachedJws = self.readJwsFromCache()
        if cachedJws:
            self.cookie = cachedJws.get(self.username)
            if self.cookie:
                # Test login status
                if self.testLoginStatus():
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

    def getSignList(self):
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
                    signInfo = {'signId': item.get('signId'), 'id': item.get('id'),'userArea':item.get('userArea'),'areaList':item.get('areaList')}
                    self.signData.append(signInfo)
            logging.info("Sign-in list retrieved successfully!")
        else:
            logging.error("Failed to retrieve sign-in list!")

    def generateCheckInRequest(self, areaList, userArea):
        checkInData = {}
        areaJsonData = self.findAreaJson(areaList, userArea)
        if areaJsonData:
            areaJson, latitude, longitude = areaJsonData
            checkInData = {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "nationcode": "156",
                "country": "China",
                "areaJSON": areaJson,
                "inArea": 1
            }
        return json.dumps(checkInData)

    def findAreaJson(self, areaList, userArea):
        for area in areaList:
            if area.get('name') == userArea:
                areaJson = {
                    "type": 0,
                    "circle": {
                        "latitude": area.get('latitude'),
                        "longitude": area.get('longitude'),
                        "radius": area.get('radius')
                    },
                    "id": area.get('id'),
                    "name": area.get('name')
                }
                return (json.dumps(areaJson), area.get('latitude'), area.get('longitude'))
        return None

    def nightSign(self):
        self.getSignList()
        if (signCount := len(self.signData)) == 0:
            logging.info("No sign-in task found!")
            return
        for sign in self.signData:
            checkInData = self.generateCheckInRequest(sign.get('areaList'), sign.get('userArea'))
            headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
            id_ = sign.get('id')
            signId = sign.get('signId')
            url = f"https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByArea?id={id_}&schoolId={self.schoolId}&signId={signId}"
            res = requests.post(url, headers=headers, data=checkInData)
            text = json.loads(res.text)
            if text['code'] == 0:
                logging.info(f"{sign.get('userArea')} sign-in successful!")
            else:
                logging.error(f"{sign.get('userArea')} sign-in failed!")


def runUsers():
    with open('users.toml', 'r') as file:
        data = toml.load(file)['user']

    for i, userData in enumerate(data):
        if i != 0:
            print("-" * 50)  # Separator between different users
        logging.info(f"Running user {userData.get('name')}...")
        try:
            u = User(userData.get('username'), userData.get('password'), userData.get('schoolId'))
            u.nightSign()
        except Exception as e:
            logging.error(f"An error occurred while running user {userData.get('name')}: {str(e)}")
        if i == len(data) - 1:
            print("-" * 50)


if __name__ == "__main__":
    # Define your cron expression here
    cronExpression = "*/5 22 * * *"  # Runs at 1:00 AM every day

    # Create a cron iterator
    cron = croniter(cronExpression)

    # Infinite loop to check if it's time to execute the task
    while True:
        # Get the next scheduled time
        nextRunTime = cron.get_next(float)

        # Calculate the delay until the next scheduled time
        delay = nextRunTime - time.time()

        # Sleep until the next scheduled time
        if delay > 0:
            time.sleep(delay)

        # Execute the task
        runUsers()
