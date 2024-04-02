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
    def build_sign_body(sign_mode, data):
        if sign_mode == 1:
            logging.debug("Building sign body for mode 1")
            return SignBuilder._build_mode1_sign_body(data)
        elif sign_mode == 2:
            logging.debug("Building sign body for mode 2")
            return SignBuilder._build_mode2_sign_body(data)
        else:
            raise ValueError("Unknown sign mode")

    @staticmethod
    def _build_mode1_sign_body(data):
        check_in_data = {}
        area_json_data = SignBuilder._find_area_json(data['areaList'], data['userArea'])
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

    @staticmethod
    def _find_area_json(area_list, user_area):
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

    @staticmethod
    def _build_mode2_sign_body(data):
        cfg = config.Config()
        phone = data['phone']
        user = next((item for item in cfg.get_user_data() if item['username'] == phone), None)
        if user is None:
            raise ValueError("User not found")
        longitude = user['longitude']
        latitude = user['latitude']
        province = user['province']
        city = user['city']
        township = user['township']
        area = user['area']
        sign_body = {
            "longitude": longitude,
            "latitude": latitude,
            "province": province,
            "city": city,
            "district": area,
            "township": township,
        }
        return json.dumps(sign_body)

def filterSignList(json_array):
    valid_signs = []
    for item in json_array:
        if item.get('type') == 0 and item.get('signStatus') == 1:
            sign_mode = item.get('signMode')
            sign_body = SignBuilder.build_sign_body(sign_mode, item)
            sign_url = signTypeTable.get(sign_mode).get('url')
            valid_signs.append({
                "signMode": sign_mode,
                "signBody": sign_body,
                "signUrl": sign_url,
                "signId": item.get('signId'),
                "id": item.get('id'),
            })
            logging.debug(f"Added valid sign: {sign_mode}")
    return valid_signs
