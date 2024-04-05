"""
[[cron]]
expression = "*/5 22 * * *"
[[user]]
name = "hta"
username = "17691189313"
password = "129hta"
school_id = "19"
sign_mode = 2
longitude = "108.7511390516493"
latitude = "34.02010877821181"
province = "陕西省"
city = "西安市"
area = "鄠邑区"
township = "草堂街道"
读取配置文件
"""

import toml


class Config:
    def __init__(self, config_file='config.toml'):
        with open(config_file, 'r') as file:
            self.data = toml.load(file)
        try:
            self.cronExpression = self.data['cron'][0].get('expression')
        except KeyError:
            raise ValueError("Cron expression not found in configuration file!")

    def readConfig(self):
        return self.data

    def getUserData(self):
        return self.data['user']

    def getCronData(self):
        return self.data['cron'][0]['expression']
