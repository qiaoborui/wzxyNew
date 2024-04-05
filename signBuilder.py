import json
import logging
import config

signTypeTable = {
    1: {
        "name": "AreaSign",
        "url": "https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByArea?id={}&schoolId={}&signId={}"
    },
    2: {
        "name": "LocationSign",
        "url": "https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByLocation?id={}&schoolId={}&signId={}"
    }
}


class SignBuilder:
    @staticmethod
    def buildSignBody(signMode, data):
        if signMode == 1:
            logging.debug("Building sign body for mode 1")
            return SignBuilder.buildLocationSignBody(data)
        elif signMode == 2:
            logging.debug("Building sign body for mode 2")
            return SignBuilder.buildAreaSignBody(data)
        else:
            raise ValueError("Unknown sign mode")

    @staticmethod
    def buildLocationSignBody(data):
        checkInData = {}
        areaJsonData = SignBuilder.convertAreaJson(data['areaList'], data['userArea'])
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

    @staticmethod
    def convertAreaJson(areaList, userArea):
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
                return json.dumps(areaJson), area.get('latitude'), area.get('longitude')
        return None

    @staticmethod
    def buildAreaSignBody(data):
        cfg = config.Config()
        phone = data['phone']
        user = next((item for item in cfg.getUserData() if item['username'] == phone), None)
        if user is None:
            raise ValueError("User not found")
        longitude = user['longitude']
        latitude = user['latitude']
        province = user['province']
        city = user['city']
        township = user['township']
        area = user['area']
        signBody = {
            "longitude": longitude,
            "latitude": latitude,
            "province": province,
            "city": city,
            "district": area,
            "township": township,
        }
        return json.dumps(signBody)


def filterSignList(json_array):
    validSigns = []
    for item in json_array:
        if item.get('type') == 0 and item.get('signStatus') == 1:
            signMode = item.get('signMode')
            signBody = SignBuilder.buildSignBody(signMode, item)
            signURL = signTypeTable.get(signMode).get('url')
            validSigns.append({
                "signMode": signMode,
                "signBody": signBody,
                "signUrl": signURL,
                "signId": item.get('signId'),
                "id": item.get('id'),
            })
            logging.debug(f"Added valid sign: {signMode}")
    return validSigns
