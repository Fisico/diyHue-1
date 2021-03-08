from configManager import configInit
from datetime import datetime
import os
import json
import logManager
import yaml
from HueObjects import Light, Group, Scene, ApiUser, Rule, ResourceLink, Schedule, Sensor
from pprint import pprint
logging = logManager.logger.get_logger(__name__)

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def _open_yaml(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return yaml.load(fp)

def _write_json(path, contents):
    with open(path, 'w', encoding="utf-8") as fp:
        yaml.dump(contents, fp , Dumper=NoAliasDumper)


class Config:
    yaml_config = None
    projectDir = '/opt/hue-emulator'
    configDir = projectDir + '/config'

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def load_config(self):
        self.yaml_config = {"apiUsers": {}, "lights": {}, "groups": {}, "scenes": {}, "config": {}, "rules": {}, "resourcelinks": {}, "schedules": {}, "sensors": {}, "v2": {}, "sensors_id": {}, "temp": {"scanResult": {"lastscan": "none"}}}
        try:
            #load config
            if os.path.exists(self.configDir + "/config.yaml"):
                config = _open_yaml(self.configDir + "/config.yaml")
                os.environ['TZ'] = config["timezone"]
                config["apiUsers"] = {}
                for user, data in config["whitelist"].items():
                    self.yaml_config["apiUsers"][user] = ApiUser(user, data["name"], data["client_key"], data["create_date"], data["last_use_date"])
                del config["whitelist"]
                self.yaml_config["config"] = config
            # load lights
            if os.path.exists(self.configDir + "/lights.yaml"):
                lights = _open_yaml(self.configDir + "/lights.yaml")
                for light, data in lights.items():
                    data["id_v1"] = light
                    self.yaml_config["lights"][light] = Light(data)
                    #self.yaml_config["groups"]["0"].add_light(self.yaml_config["lights"][light])
            #groups
            if os.path.exists(self.configDir + "/groups.yaml"):
                groups = _open_yaml(self.configDir + "/groups.yaml")
                for group, data in groups.items():
                    data["id_v1"] = group
                    objctsList = []
                    #   Reference lights objects instead of id's
                    for light in data["lights"]:
                        objctsList.append(self.yaml_config["lights"][light])
                    data["lights"] = objctsList
                    self.yaml_config["groups"][group] = Group(data)
            else:
                #define group 0
                self.yaml_config["groups"]["0"] = Group({"name":"Group 0","id_v1": "0","type":"LightGroup","state":{"all_on":False,"any_on":True},"recycle":False,"action":{"on":False,"bri":165,"hue":8418,"sat":140,"effect":"none","xy":[0.6635,0.2825],"ct":366,"alert":"select","colormode":"hs"}})
            #scenes
            if os.path.exists(self.configDir + "/scenes.yaml"):
                scenes = _open_yaml(self.configDir + "/scenes.yaml")
                for scene, data in scenes.items():
                    data["id_v1"] = scene
                    if data["type"] == "GroupScene":
                        group = self.yaml_config["groups"][data["group"]]
                        data["lights"] = group.lights
                        data["group"] = group
                    else:
                        objctsList = []
                        for light in data["lights"]:
                            objctsList.append(self.yaml_config["lights"][light])
                        data["lights"] = objctsList
                    lightStates = {}
                    for light, lightstate in data["lightstates"].items():
                        lightStates[self.yaml_config["lights"][light]] = lightstate
                    data["lightstates"] = lightStates
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["scenes"][scene] = Scene(data)
            #rules
            if os.path.exists(self.configDir + "/rules.yaml"):
                rules = _open_yaml(self.configDir + "/rules.yaml")
                for rule, data in rules.items():
                    data["id_v1"] = rule
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["rules"][rule] = Rule(data)
            #schedules
            if os.path.exists(self.configDir + "/schedules.yaml"):
                schedules = _open_yaml(self.configDir + "/schedules.yaml")
                for schedule, data in schedules.items():
                    data["id_v1"] = schedule
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["schedules"][schedule] = Schedule(data)
            #sensors
            if os.path.exists(self.configDir + "/sensors.yaml"):
                sensors = _open_yaml(self.configDir + "/sensors.yaml")
                for sensor, data in sensors.items():
                    data["id_v1"] = sensor
                    self.yaml_config["sensors"][sensor] = Sensor(data)
                    self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"][sensor])
            else:
                data = {"config": {"configured": False, "on": True}, "modelid": "PHDL00", "state":{"daylight":None, "lastupdated":"none"}, "name": "Daylight", "type": "Daylight", "id_v1": "1"}
                self.yaml_config["sensors"]["1"] = Sensor(data)
                self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"]["1"])
            if os.path.exists(self.configDir + "/sensors.yaml"):
                #resourcelinks
                resourcelinks = _open_yaml(self.configDir + "/resourcelinks.yaml")
                for resourcelink, data in resourcelinks.items():
                    data["id_v1"] = resourcelink
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    links = []
                    for link in data["links"]:
                        elements = link.split("/")
                        links.append(self.yaml_config[elements[1]][elements[2]])
                    data["links"] = links
                    self.yaml_config["resourcelinks"][resourcelink] = ResourceLink(data)
                logging.info("Config loaded")
                #pprint(self.yaml_config)
        except Exception:
            logging.exception("CRITICAL! Config file was not loaded")
            raise SystemExit("CRITICAL! Config file was not loaded")
        bridgeConfig = self.yaml_config


    def save_config(self, backup=False):
        path = self.configDir + '/'
        if backup:
            path = self.configDir + '/backup/'
            if not os.path.exists(path):
                os.makedirs(path)
        config = self.yaml_config["config"]
        config["whitelist"] = {}
        for user, obj in self.yaml_config["apiUsers"].items():
            config["whitelist"][user] = obj.save()

        _write_json(path + "config.yaml", config)
        for object in ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors"]:
            filePath = path + object + ".yaml"
            dumpDict = {}
            for element in self.yaml_config[object]:
                dumpDict[self.yaml_config[object][element].id_v1] = self.yaml_config[object][element].save()
            _write_json(filePath, dumpDict)


    def reset_config(self):
        backup = self.save_config(True)
        try:
            os.remove(self.configDir + "/*.yaml")
        except:
            logging.exception("Something went wrong when deleting the config")
        self.load_config()
        return backup

    def write_args(self, args):
        self.yaml_config = configInit.write_args(args, self.yaml_config)

    def generate_security_key(self):
        self.yaml_config = configInit.generate_security_key(self.yaml_config)
