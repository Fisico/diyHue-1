import uuid
import logManager
from lights.light_types import lightTypes, sensorTypes
from lights.protocols import protocols
from datetime import datetime
from pprint import pprint

logging = logManager.logger.get_logger(__name__)

def genV2Uuid():
    return str(uuid.uuid4())


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def incProcess(state, data):
    if "bri_inc" in data:
        state["bri"] += data["bri_inc"]
        if state["bri"] > 254:
            state["bri"] = 254
        elif state["bri"] < 1:
            state["bri"] = 1
        del data["bri_inc"]
        data["bri"] = state["bri"]
    elif "ct_inc" in data:
        state["ct"] += data["ct_inc"]
        if state["ct"] > 500:
            state["ct"] = 500
        elif state["ct"] < 153:
            state["ct"] = 153
        del data["ct_inc"]
        data["ct"] = state["ct"]
    elif "hue_inc" in data:
        state["hue"] += data["hue_inc"]
        if state["hue"] > 65535:
            state["hue"] -= 65535
        elif state["hue"] < 0:
            state["hue"] += 65535
        del data["hue_inc"]
        data["hue"] = state["hue"]
    elif "sat_inc" in data:
        state["sat"] += data["sat_inc"]
        if state["sat"] > 254:
            state["sat"] = 254
        elif state["sat"] < 1:
            state["sat"] = 1
        del data["sat_inc"]
        data["sat"] = state["sat"]

    return data

class ApiUser():
    def __init__(self, username, name, client_key, create_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), last_use_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")):
        self.username = username
        self.name = name
        self.client_key = client_key
        self.create_date = create_date
        self.last_use_date = last_use_date

    def getV1Api(self):
        return {"name": self.name, "create date": self.create_date, "last use date": self.last_use_date}

    def save(self):
        return {"name": self.name, "client_key": self.client_key, "create_date": self.create_date, "last_use_date": self.last_use_date}

class Device():
    def __init__(self, id_v2=genV2Uuid()):
        self.id_v2 = id_v2
        self.services = []

    def add_service(self, service):
        self.services.append(service)

    def getV2Api(self):
        result = {}


class Light():
    def __init__(self, data):
        self.name = data["name"]
        self.modelid = data["modelid"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.swversion = data["swversion"] if "swversion" in data else generate_unique_id()
        self.state = data["state"] if "state" in data else lightTypes[self.modelid]["state"]
        self.protocol = data["protocol"] if "protocol" in data else "dummy"
        self.config = data["config"] if "config" in data else lightTypes[self.modelid]["config"]
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {}
        self.streaming = False

    def update_attr(self,newdata):
        for key,value in newdata.items():
            updateAttribute = getattr(self,key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self,key,updateAttribute)
            else:
                setattr(self,key,value)

    def getV1Api(self):
        result = lightTypes[self.modelid]["v1_static"].copy()
        result["config"] = self.config
        result["capabilities"]["streaming"]["renderer"] = self.streaming
        result["state"] = self.state
        result["name"] = self.name
        result["swversion"] = self.swversion
        return result

    def updateLightState(self, state):

        if "xy" in state:
            self.state["colormode"] = "xy"
        elif "ct" in state:
            self.state["colormode"] = "ct"
        elif "hue" in state or "sat" in state:
            self.state["colormode"] = "hs"

    def setV1State(self, state, rgb=None):
        if "lights" not in state:
            state = incProcess(self.state, state)
            self.updateLightState(state)
            self.state.update(state)

        for protocol in protocols:
            if "lights.protocols." + self.protocol == protocol.__name__:
                try:
                    if self.protocol in ["mi_box", "esphome", "tasmota"]:
                        protocol.set_light(self, state, rgb)
                    else:
                        protocol.set_light(self, state)
                    self.state["reachable"] = True
                except Exception as e:
                    self.state["reachable"] = False
                    logging.warning(self.name + " light error, details: %s", e)
                return


    def getV2Api(self):
        result = {}
        if "xy" in self.state:
            colorgamut = lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamut"]
            result = {
                "color": {
                    "gamut": {
                        "blue":  {"x": colorgamut[0][0], "y": colorgamut[0][1]},
                        "green": {"x": colorgamut[1][0], "y": colorgamut[1][1]},
                        "red":   {"x": colorgamut[2][0], "y": colorgamut[2][1]}
                    },
                    "gamut_type": lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamuttype"],
                    "xy": {
                        "x": self.state["xy"][0],
                        "y": self.state["xy"][1]
                    }
                }
            }
        if "ct" in self.state:
            result["color_temperature"] = {
                "mirek": self.state["ct"]
            }
        if "bri" in self.state:
            result["dimming"] = {
                "brightness": self.state["bri"]
            }
        result["dynamics"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/lights/" + self.id_v1
        result["metadata"] = {"name": self.name}
        if "archetype" in lightTypes[self.modelid]["v1_static"]["config"]:
            result["metadata"]["archetype"] = lightTypes[self.modelid]["v1_static"]["config"]["archetype"]
        result["mode"] = "normal"
        result["on"] = {
            "on": self.state["on"]
        }
        result["type"] = "light"
        return result

    def getV2Entertainment(self):
        entertainmenUuid = uuid.uuid5(self.id_v2, 'entertainment')
        result = {
            "id": entertainmenUuid,
            "id_v1": "/lights/" + + self.id_v1,
            "proxy": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["proxy"],
            "renderer": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["renderer"]
        }
        result["segments"] = {
            "configurable": False,
            "max_segments": 1
        }
        if self.modelid in ["LCX001", "LCX002", "LCX003"]:
            result["segments"]["segments"] = [
                {
                    "length": 2,
                    "start": 0
                },
                {
                    "length": 2,
                    "start": 2
                },
                {
                    "length": 4,
                    "start": 4
                },
                {
                    "length": 4,
                    "start": 8
                },
                {
                    "length": 4,
                    "start": 12
                },
                {
                    "length": 2,
                    "start": 16
                },
                {
                    "length": 2,
                    "start": 18
                }]
        else:
            result["segments"]["segments"] = [{
                "length": 1,
                "start": 0
            }]
        result["type"] = "entertainment"
        return result

    def getObjectPath(self):
        return {"resource": "lights","id" :self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "modelid": self.modelid, "swversion": self.swversion, "state": self.state, "config": self.config, "protocol": self.protocol, "protocol_cfg": self.protocol_cfg}
        return result


class Group():

    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.icon_class = data["icon_class"] if "icon_class" in data else "Other"
        self.lights = data["lights"] if "lights" in data else []
        self.action = {"on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none", "xy": [
            0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"}
        self.sensors = []
        self.type = data["type"] if "type" in data else "LightGroup"
        self.locations = data["locations"] if "locations" in data else {}
        self.stream = {"proxymode": "auto",
                       "proxynode": "/bridge", "active": False, "owner": None}
        self.state = {"all_on": False, "any_on": False}
        self.dxstate = {"all_on": None, "any_on": None}

    def add_light(self, light):
        self.lights.append(light)

    def add_sensor(self, sensor):
        self.sensors.append(sensor)

    def update_attr(self,newdata):
        for key,value in newdata.items():
            updateAttribute = getattr(self,key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self,key,updateAttribute)
            else:
                setattr(self,key,value)

    def setV1Action(self, state, scene):
        lightsState = {}
        if scene != None:
            for light, state in scene.lightstates.items():
                lightsState[light.id_v1] = state
        else:
            state = incProcess(self.action, state)
            for light in self.lights:
                lightsState[light.id_v1] = state
            if "xy" in state:
                self.action["colormode"] = "xy"
            elif "ct" in state:
                self.action["colormode"] = "ct"
            elif "hue" in state or "sat" in state:
                self.action["colormode"] = "hs"

            if "on" in state:
                print("on in")
                print(state["on"])
                self.state["any_on"] = state["on"]
                self.state["all_on"] = state["on"]
            self.action.update(state)

        queueState = {}
        for light in self.lights:
            if light.id_v1 in lightsState: # apply only if the light belong to this group
                light.state.update(lightsState[light.id_v1])
                light.updateLightState(lightsState[light.id_v1])
                if light.protocol in ["native_multi", "mqtt"]:
                    light.updateLightState(lightsState[light.id_v1])
                    if light.protocol_cfg["ip"] not in queueState:
                        queueState[light.protocol_cfg["ip"]] = {"object": light, "lights":{}}
                    if light.protocol == "native_multi":
                        queueState[light.protocol_cfg["ip"]]["lights"][light.protocol_cfg["light_nr"]] = lightsState[light.id_v1]
                    elif  light.protocol == "mqtt":
                        queueState[light.protocol_cfg["ip"]]["lights"][light.protocol_cfg["command_topic"]] = lightsState[light.id_v1]
                else:
                    light.setV1State(state)
        for device, state in queueState.items():
            state["object"].setV1State(state)



    def update_state(self):
        all_on = True
        any_on = False
        if len(self.lights) == 0:
            all_on = False
        for light in self.lights:
            if light.state["on"]:
                any_on = True
            else:
                all_on = False
        return {"all_on": all_on, "any_on": any_on}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        lights = []
        for light in self.lights:
            lights.append(light.id_v1)
        sensors = []
        for sensor in self.sensors:
            sensors.append(sensor.id_v1)
        result["lights"] = lights
        result["sensors"] = sensors
        result["type"] = self.type
        result["state"] = self.update_state()
        result["recycle"] = False
        if self.id_v1 == "0":
            result["presence"] = {"state": {"presence": None,"presence_all": None,"lastupdated": "none"}}
            result["lightlevel"] = {"state": {"dark": None, "dark_all": None, "daylight": None, "daylight_any": None,"lightlevel": None,"lightlevel_min": None,"lightlevel_max": None,"lastupdated": "none"}}
        else:
            result["class"] = self.icon_class
        result["action"] = self.action

        if self.type == "Entertainment":
            result["locations"] = self.locations
            result["stream"] = self.stream
        return result

    def getV2Room(self):
        result = {"grouped_services": [], "services": []}
        result["grouped_services"].append({
            "reference_id": self.id_v2,
            "reference_type": "grouped_light",
            "rid": self.id_v2,
            "rtype": "grouped_light"

        })
        result["id"] = uuid.uuid5(self.id_v2, 'room')
        result["id_v1"] = "/groups/" + self.id_v1
        result["metadata"] = {
            "archetype": self.icon_class.replace(" ", "_").replace("'", "").lower(),
            "name": self.name
        }
        for light in self.lights:
            result["services"].append({
                "reference_id": light.id_v1,
                "reference_type": "light",
                "rid": light.id_v1,
                "rtype": "light"
            })

        result["type"] = "room"
        return result


    def getV2GroupedLight(self):
        result = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/groups/" + self.id_v1
        result["on"] = self.update_state()["any_on"]
        result["type"] = "grouped_light"
        return result

    def getV2EntertainmentConfig(self):

        gradienStripPositions = [[-0.4000000059604645, 0.800000011920929, -0.4000000059604645],
                                 [-0.4000000059604645, 0.800000011920929, 0.0],
                                 [-0.4000000059604645, 0.800000011920929,
                                     0.4000000059604645],
                                 [0.0, 0.800000011920929, 0.4000000059604645],
                                 [0.4000000059604645, 0.800000011920929,
                                     0.4000000059604645],
                                 [0.4000000059604645, 0.800000011920929, 0.0],
                                 [0.4000000059604645, 0.800000011920929, -0.4000000059604645]]

        entertainmenUuid = uuid.uuid5(self.id_v2, 'entertainment')
        result = {
            "channels": [],
            "configuration_type": "screen",
            "id": uuid,
            "id_v1": "/groups/" + self.id_v1,
            "locations": {
                "service_locations": []
            },
            "name": self.name,
            "status": "active" if self.stream["active"] else "inactive",
            "stream_proxy": {
                "mode": "auto",
                "node": {
                    "reference_id": "57a9ebc9-406d-4a29-a4ff-42acee9e9be9",
                    "reference_type": "entertainment",
                    "rid": "57a9ebc9-406d-4a29-a4ff-42acee9e9be9",
                    "rtype": "entertainment"
                }
            },
            "type": "entertainment_configuration"

        }
        channel_id = 0
        for light in self.lights:
            loops = 1
            entertainmentUuid = uuid.uuid5(light.id_v2, 'entertainment')
            gradientStrip = False
            if light.modelid in ["LCX001", "LCX002", "LCX003"]:
                loops = 7
                gradientStrip = True
            for x in range(loops):
                result["channels"].append({
                    "channel_id": channel_id,
                    "members": [
                        {
                            "index": x,
                            "service": {
                                "reference_id": entertainmentUuid,
                                "reference_type": "entertainment",
                                "rid": entertainmentUuid,
                                "rtype": "entertainment"
                            }
                        }
                    ],
                    "position": {
                        "x": gradienStripPositions[x][0] if gradientStrip else self.locations[light.id_v1][0],
                        "y": gradienStripPositions[x][1] if gradientStrip else self.locations[light.id_v1][1],
                        "z": gradienStripPositions[x][2] if gradientStrip else self.locations[light.id_v1][2]
                    }
                })
            channel_id += 1

        return result

    def getObjectPath(self):
        return {"resource": "groups","id" :self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "icon_class": self.icon_class, "lights": [], "action": self.action, "type": self.type}
        for light in self.lights:
            result["lights"].append(light.id_v1)
        if self.type == "Entertainment":
            result["locations"] = self.locations
        return result

class Scene():

    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.owner = data["owner"] if "owner" in data else "none"
        self.appdata = data["appdata"] if "appdata" in data else {}
        self.type = data["type"] if "type" in data else "LightScene"
        self.picture = data["picture"] if "picture" in data else ""
        self.image = data["image"] if "image" in data else ""
        self.recycle = data["recycle"] if "recycle" in data else False
        self.lastupdated = data["lastupdated"] if "lastupdated" in data else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.lightstates = data["lightstates"] if "lightstates" in data else {}
        self.group = data["group"] if "group" in data else None
        self.lights = data["lights"] if "lights" in data else []

    def add_light(self, light):
        self.lights.append(light)

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["type"] = self.type
        result["lights"] = []
        if self.type == "LightScene":
            for light in self.lights:
                result["lights"].append(light.id_v1)
        elif self.type == "GroupScene":
            result["group"] = self.group.id_v1
            for light in self.group.lights:
                result["lights"].append(light.id_v1)
        lightstates = {}
        for lightstate in self.lightstates:
            lightstates[lightstate.id_v1] = self.lightstates[lightstate]
        result["lightstates"] = lightstates
        result["owner"] = self.owner.username
        result["recycle"] = self.recycle
        # must be fuction to check the presece in rules or schedules
        result["locked"] = False
        result["appdata"] = self.appdata
        result["picture"] = self.picture
        result["image"] = self.image
        result["lastupdated"] = self.lastupdated
        return result

    def getV2Api(self):
        result = {"actions": []}
        for lightstate in self.lightstates:
            v2State = {}
            if "on" in self.lightstates[lightstate]:
                v2State["on"] = {"on": self.lightstates[lightstate]["on"]}
            if "bri" in self.lightstates[lightstate]:
                v2State["dimming"] = {
                    "brightness": self.lightstates[lightstate]["bri"]}
            if "xy" in self.lightstates[lightstate]:
                v2State["color"] = {"xy": {"x": self.lightstates[lightstate]
                                           ["xy"][0], "y": self.lightstates[lightstate]["xy"][1]}}
            if "ct" in self.lightstates[lightstate]:
                v2State["color_temperature"] = {
                    "mirek": self.lightstates[lightstate]["ct"]}

            result["actions"].append(
                {
                    "action": v2State,
                    "target": {
                        "reference_id": lightstate.id_v2,
                        "reference_type": "light",
                        "rid": lightstate.id_v2,
                        "rtype": "light",
                    },
                }
            )

        if self.type == "GroupScene":
            result["group"] = {
                "reference_id": self.group.id_v2,
                "reference_type": "room",
                "rid": self.group.id_v2,
                "rtype": "room"
            }
        result["metadata"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/scenes/" + self.id_v1
        result["name"] = self.name
        result["type"] = "scene"
        return result

    def getObjectPath(self):
        return {"resource": "scenes","id" :self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "owner": self.owner.username,"type": self.type, "picture": self.picture, "image": self.image, "recycle": self.recycle, "lastupdated": self.lastupdated, "lights": [], "lightstates": {}}
        for light in self.lights:
            result["lights"].append(light.id_v1)
        for light in self.lightstates:
            result["lightstates"][light.id_v1] = self.lightstates[light]
        if self.group != None:
            result["group"] = self.group.id_v1
        return result


class Rule():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.actions = data["actions"] if "actions" in data else []
        self.conditions = data["conditions"] if "conditions" in data else []
        self.owner = data["owner"]
        self.recycle = data["recycle"] if "recycle" in data else False
        self.created = data["created"] if "created" in data else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.lasttriggered = data["lasttriggered"] if "lasttriggered" in data else "none"
        self.timestriggered = data["timestriggered"] if "timestriggered" in data else 0

    def add_actions(self, action):
        self.actions.append(action)

    def add_conditions(self, condition):
        self.condition.append(condition)

    def getObjectPath(self):
        return {"resource": "rules","id" :self.id_v1}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["actions"] = self.actions
        result["conditions"] = self.conditions
        result["owner"] = self.owner.username
        result["recycle"] = self.recycle
        result["created"] = self.created
        result["lasttriggered"] = self.lasttriggered
        result["timestriggered"] = self.timestriggered
        return result

    def save(self):
        return self.getV1Api()


class Sensor():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.config = data["config"] if "config" in data else {}
        self.modelid = data["modelid"]
        self.type = data["type"]
        self.state = data["state"] if "state" in data else {}
        self.dxstate = {}
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else ""

    def getV1Api(self):
        result = {}
        if self.modelid in sensorTypes:
            result = sensorTypes[self.modelid][self.type].copy()
        result["name"] = self.name
        result["config"] = self.config
        result["modelid"] = self.modelid
        result["state"] = self.state
        result["uniqueid"] = self.uniqueid
        return result

    def getObjectPath(self):
        return {"resource": "sensors","id" :self.id_v1}

    def save(self):
        result = {}
        result["name"] = self.name
        result["id_v1"] = self.id_v1
        result["id_v2"] = self.id_v2
        result["config"] = self.config
        result["type"] = self.type
        result["modelid"] = self.modelid
        result["state"] = self.state
        result["uniqueid"] = self.uniqueid
        return result


class ResourceLink():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.classid = data["classid"]
        self.description = data["description"] if "description" in data else ""
        self.links = data["links"] if "links" in data else []
        self.owner = data["owner"]

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["classid"] = self.classid
        result["description"] = self.description
        links = []
        for link in self.links:
            links.append("/" + link.getObjectPath()["resource"] + "/" + link.getObjectPath()["id"])
        result["links"] = links
        result["owner"] = self.owner.username
        return result

    def save(self):
        return self.getV1Api()


class Schedule():
    def __init__(self, data):
        self.name = data["name"] if "name" in data else "schedule " +  data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.description = data["description"] if "description" in data else "none"
        self.command = data["command"] if "command" in data else {}
        self.time = data["time"] if "time" in data else None
        self.created = data["created"] if "created" in data else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.status = data["status"] if "status" in data else "disabled"
        self.autodelete = data["autodelete"] if "autodelete" in data else True
        self.starttime = data["starttime"] if "starttime" in data else None

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["description"] = self.description
        result["command"] = self.command
        if self.time != None:
            result["time"] = self.time
        if self.starttime != None:
            result["starttime"] = self.starttime
        result["status"] = self.status
        result["autodelete"] = self.autodelete
        return result

    def getObjectPath(self):
        return {"resource": "schedule","id" :self.id_v1}

    def save(self):
        return  self.getV1Api()
