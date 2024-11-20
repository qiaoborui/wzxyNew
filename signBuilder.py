import json
import logging

signTypeTable = {
    1: {
        "name": "LocationSign",
        "url": "https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByLocation?id={}&schoolId={}&signId={}"
    },
    2: {
        "name": "AreaSign",
        "url": "https://gw.wozaixiaoyuan.com/sign/mobile/receive/doSignByArea?id={}&schoolId={}&signId={}"
    }
}

class SignBuilder:
    @staticmethod
    def buildSignBody(signMode, data, location_info=None):
        if signMode == 1:  # Location sign
            logging.debug("Building sign body for location mode")
            return SignBuilder.buildLocationSignBody(data)
        elif signMode == 2:  # Area sign
            logging.debug("Building sign body for area mode")
            if not location_info:
                raise ValueError("Location info is required for area sign")
            return SignBuilder.buildAreaSignBody(location_info)
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
    def buildAreaSignBody(location_info):
        signBody = {
            "longitude": location_info['longitude'],
            "latitude": location_info['latitude'],
            "province": location_info['province'],
            "city": location_info['city'],
            "district": location_info['area'],
            "township": location_info['township'],
        }
        return json.dumps(signBody)

def filterSignList(json_array, location_info=None):
    validSigns = []
    for item in json_array:
        if item.get('type') == 0 and item.get('signStatus') == 1:
            signMode = item.get('signMode')
            try:
                signBody = SignBuilder.buildSignBody(signMode, item, location_info)
                signURL = signTypeTable.get(signMode).get('url')
                validSigns.append({
                    "signMode": signMode,
                    "signBody": signBody,
                    "signUrl": signURL,
                    "signId": item.get('signId'),
                    "id": item.get('id'),
                })
                logging.debug(f"Added valid sign: {signMode}")
            except ValueError as e:
                logging.warning(f"Skipping sign due to: {str(e)}")
                continue
    return validSigns
