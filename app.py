import requests
import json
import re
import traceback
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import signBuilder
import os

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create handlers
consoleHandler = logging.StreamHandler()

# Create formatters and add them to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
consoleHandler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(consoleHandler)

app = Flask(__name__)
CORS(app)

class User:
    def __init__(self, username, password, school_id):
        self.username = username
        self.password = password
        self.school_id = school_id
        self.cookie = None
        
        if not self.login():
            raise Exception("Login failed")

    def encrypt(self, text):
        key = (str(self.username) + "0000000000000000")[:16]
        cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        padded_text = pad(text.encode('utf-8'), AES.block_size)
        encryptedText = cipher.encrypt(padded_text)
        return b64encode(encryptedText).decode('utf-8')

    def login(self):
        encryptedText = self.encrypt(self.password)
        loginUrl = 'https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username'
        params = {
            "schoolId": self.school_id,
            "username": self.username,
            "password": encryptedText
        }
        loginReq = requests.post(loginUrl, params=params)
        text = json.loads(loginReq.text)
        if text['code'] == 0:
            set_cookie = loginReq.headers['Set-Cookie']
            match = re.search(r'JWSESSION=.*?;', str(set_cookie))
            if match is None:
                logging.error("Login failed, JWSESSION not found in response!")
                return False
            self.cookie = match.group(0)
            return True
        else:
            logging.error(f"{self.username} login error, please check account password!")
            return False

    def getSignList(self):
        if not self.cookie:
            logging.error("Please log in first!")
            return []

        headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
        url = "https://gw.wozaixiaoyuan.com/sign/mobile/receive/getMySignLogs?page=1&size=10"
        res = requests.get(url, headers=headers)
        data = json.loads(res.text)

        if 'code' in data and data['code'] == 0 and 'data' in data:
            # Get location info from request data for area sign
            location_info = {
                'longitude': request.json.get('longitude'),
                'latitude': request.json.get('latitude'),
                'province': request.json.get('province'),
                'city': request.json.get('city'),
                'area': request.json.get('area'),
                'township': request.json.get('township')
            } if request.json else None
            
            signInfo = signBuilder.filterSignList(data['data'], location_info)
            logging.debug(signInfo)
            return signInfo
        else:
            logging.error("Failed to retrieve sign-in list!")
            return []

    def sign(self, sign_data):
        headers = {'Host': "gw.wozaixiaoyuan.com", 'Cookie': self.cookie}
        id_ = sign_data.get('id')
        sign_id = sign_data.get('signId')
        url = sign_data['signUrl'].format(id_, self.school_id, sign_id)
        res = requests.post(url, headers=headers, data=sign_data['signBody'])
        text = json.loads(res.text)
        return text['code'] == 0

@app.route('/api/areaSignin', methods=['POST'])
def area_signin():
    try:
        data = request.get_json()
        required_fields = ['username', 'password', 'school_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        user = User(data['username'], data['password'], data['school_id'])
        sign_list = user.getSignList()
        
        if not sign_list:
            return jsonify({'message': 'No sign-in task found'}), 404
            
        for sign_data in sign_list:
            if sign_data['signMode'] == 2:  # Area sign mode
                if user.sign(sign_data):
                    return jsonify({'message': 'Sign-in successful'}), 200
                else:
                    return jsonify({'error': 'Sign-in failed'}), 500
                    
        return jsonify({'message': 'No area sign-in task found'}), 404

    except Exception as e:
        logging.error(f"Error during area sign-in: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/locationSignin', methods=['POST'])
def location_signin():
    try:
        data = request.get_json()
        required_fields = ['username', 'password', 'school_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        user = User(data['username'], data['password'], data['school_id'])
        sign_list = user.getSignList()
        
        if not sign_list:
            return jsonify({'message': 'No sign-in task found'}), 404
            
        for sign_data in sign_list:
            if sign_data['signMode'] == 1:  # Location sign mode
                if user.sign(sign_data):
                    return jsonify({'message': 'Sign-in successful'}), 200
                else:
                    return jsonify({'error': 'Sign-in failed'}), 500
                    
        return jsonify({'message': 'No location sign-in task found'}), 404

    except Exception as e:
        logging.error(f"Error during location sign-in: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000), host='0.0.0.0')
