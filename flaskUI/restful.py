import configManager
import logManager
import uuid
import json
import os
import requests
from subprocess import Popen
from threading import Thread
from time import sleep
from datetime import datetime
from lights.manage import updateGroupStats, splitLightsToDevices, groupZero, sendLightRequest, switchScene
from lights.discover import scanForLights
from functions.core import generateDxState, capabilities, staticConfig, nextFreeId
from flask_restful import Resource
from flask import request
from functions.rules import rulesProcessor
from services.entertainment import entertainmentService
import HueObjects

from pprint import pprint
logging = logManager.logger.get_logger(__name__)

bridgeConfig = configManager.bridgeConfig.yaml_config


def authorize(username, resource='', resourceId='', resourceParam=''):
    if username not in bridgeConfig["apiUsers"] and request.remote_addr != "127.0.0.1":
        return [{"error": {"type": 1, "address": "/" + resource + "/" + resourceId, "description": "unauthorized user"}}]

    if resourceId not in ["0", "new"] and resourceId != '' and resourceId not in bridgeConfig[resource]:
        return [{"error": {"type": 3, "address": "/" + resource + "/" + resourceId, "description": "resource, " + resource + "/" + resourceId + ", not available"}}]

    if resourceId != "0" and resourceParam != '' and not hasattr(bridgeConfig[resource][resourceId], resourceParam):
        return [{"error": {"type": 3, "address": "/" + resource + "/" + resourceId + "/" + resourceParam, "description": "resource, " + resource + "/" + resourceId + "/" + resourceParam + ", not available"}}]
    bridgeConfig["apiUsers"][username].last_use_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    return ["success"]


def buildConfig():
    result = staticConfig()
    config = bridgeConfig["config"]
    result.update({"apiversion": config["apiversion"], "bridgeid": config["bridgeid"], "ipaddress": config["ipaddress"], "netmask": config["netmask"],"gateway": config["gateway"], "mac": config["mac"], "name": config["name"], "swversion": config["swversion"], "timezone": config["timezone"]})
    result["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    result["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result["whitelist"] = {}
    for key, user in bridgeConfig["apiUsers"].items():
        result["whitelist"][key] = {"create date": user.create_date, "last use date": user.last_use_date, "name": user.name}
    return result



class NewUser(Resource):
    def get(self):
        return [{"error": {"type": 4, "address": "/api", "description": "method, GET, not available for resource, /"}}]

    def post(self):
        postDict = request.get_json(force=True)
        pprint(postDict)
        if "devicetype" in postDict:
            last_button_press = bridgeConfig["config"]["linkbutton"]["lastlinkbuttonpushed"]
            if last_button_press + 30 >= datetime.now().timestamp() or True:
                username = str(uuid.uuid1()).replace('-', '')
                if postDict["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                response = [{"success": {"username": username}}]
                client_key = None
                if "generateclientkey" in postDict and postDict["generateclientkey"]:
                    client_key = str(uuid.uuid4()).replace('-', '').upper()
                    #client_key = "321c0c2ebfa7361e55491095b2f5f9db"

                    response[0]["success"]["clientkey"] = client_key
                bridgeConfig["apiUsers"][username] = HueObjects.ApiUser(username, postDict["devicetype"], client_key)
                pprint(response)
                configManager.bridgeConfig.save_config()
                return response
            else:
                return [{"error": {"type": 101, "address": "/api/", "description": "link button not pressed"}}]
        else:
            return [{"error": {"type": 6, "address": "/api/" + list(postDict.keys())[0], "description":"parameter, " + list(postDict.keys())[0] + ", not available"}}]


class ShortConfig(Resource):
    def get(self):
        config = bridgeConfig["config"]
        return {"apiversion": config["apiversion"], "bridgeid": config["bridgeid"], "datastoreversion": staticConfig()["datastoreversion"], "factorynew": False, "mac": config["mac"], "modelid": "BSB002", "name": config["name"], "replacesbridgeid": None, "starterkitid": "", "swversion": config["swversion"]}


class EntireConfig(Resource):
    def get(self, username):
        authorisation = authorize(username)
        if "success" not in authorisation:
            return authorisation
        result = {}
        result["config"] = buildConfig()
        for resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "sensors"]:
            result[resource] = {}
            for resource_id in bridgeConfig[resource]:
                if resource_id != "0":
                    result[resource][resource_id] = bridgeConfig[resource][resource_id].getV1Api()
        return result


class ResourceElements(Resource):
    def get(self, username, resource):
        if username in bridgeConfig["apiUsers"]:
            if resource == "capabilities":
                return capabilities()
            else:
                response = {}
                if resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "sensors"]:
                    for object in bridgeConfig[resource]:
                        response[object] = bridgeConfig[resource][object].getV1Api()
                elif resource == "config":
                    response = buildConfig()
                return response
        elif resource == "config":
            config = bridgeConfig["config"]

            return {"name": config["name"], "datastoreversion": staticConfig()["datastoreversion"], "swversion": config["swversion"], "apiversion": config["apiversion"], "mac": config["mac"], "bridgeid": config["bridgeid"], "factorynew": False, "replacesbridgeid": None, "modelid": staticConfig()["modelid"], "starterkitid": ""}
        return [{"error": {"type": 1, "address": "/", "description": "unauthorized user"}}]

    def post(self, username, resource):
        authorisation = authorize(username, resource)
        if "success" not in authorisation:
            return authorisation
        if (resource == "lights" or resource == "sensors") and request.get_data(as_text=True) == "":
            print("scan for light")
            # if was a request to scan for lights of sensors
            Thread(target=scanForLights).start()
            return [{"success": {"/" + resource: "Searching for new devices"}}]
        postDict = request.get_json(force=True)
        pprint(postDict)
        # find the first unused id for new object
        new_object_id = nextFreeId(bridgeConfig, resource)
        postDict["id_v1"] = new_object_id
        if resource == "groups":
            if "lights" in postDict:
                objLights = []
                for light in postDict["lights"]:
                    objLights.append(bridgeConfig["lights"][light])
                postDict["lights"] = objLights
            bridgeConfig[resource][new_object_id] = HueObjects.Group(postDict)
        elif resource == "scenes":
            postDict["owner"] = bridgeConfig["apiUsers"][username]
            if "group" in postDict:
                postDict["group"] = bridgeConfig["groups"][postDict["group"]]
            if "lightstates" in postDict:
                objStates = {}
                for light, state in postDict["lightstates"].items():
                    objStates[bridgeConfig["lights"][light]] = state
                postDict["lightstates"] = objStates
            bridgeConfig[resource][new_object_id] = HueObjects.Scene(postDict)
        elif resource == "rules":
            bridgeConfig[resource][new_object_id] = HueObjects.Rule(postDict)
        elif resource == "resourcelinks":
            bridgeConfig[resource][new_object_id] = HueObjects.ResourceLink(postDict)
        elif resource == "sensors":
            bridgeConfig[resource][new_object_id] = HueObjects.Sensor(postDict)
        logging.info(json.dumps([{"success": {"id": new_object_id}}],
                                sort_keys=True, indent=4, separators=(',', ': ')))
        configManager.bridgeConfig.save_config()
        return [{"success": {"id": new_object_id}}]

    def put(self, username, resource):
        authorisation = authorize(username, resource)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        bridgeConfig[resource].update(putDict)
        if resource == "config" and "timezone" in putDict:
            os.environ['TZ'] = putDict["timezone"]
        responseDictionary = []
        response_location = "/" + resource + "/"
        for key, value in putDict.items():
            responseDictionary.append(
                {"success": {response_location + key: value}})
        pprint(responseDictionary)
        return responseDictionary


class Element(Resource):

    def get(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        if resource in ["lights", "sensors"] and resourceid == "new":
            response = bridgeConfig["temp"]["scanResult"]
            pprint(response)
            return response
        if resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "sensors"]:
            return bridgeConfig[resource][resourceid].getV1Api()
            # return bridgeConfig["objects"]["lights"][resourceid].getV2Api()
        return bridgeConfig[resource][resourceid]

    def put(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        putDict = request.get_json(force=True)
        pprint(putDict)
        currentTime = datetime.now()

        if resource == "sensors":
            if resourceid == "1":
                bridgeConfig["sensors"]["1"].config["configured"] = True # mark daylight sensor as configured
                bridgeConfig["config"]["daylight"] = putDict["config"]
                return {"success": {"/sensors/1/config": putDict["config"]}}
            elif "state" in putDict:
                for state in putDict["state"].keys():
                    bridgeConfig["sensors"][resourceid].dxstate[state] = currentTime

        elif resource == "groups" and "stream" in putDict:
            if "active" in putDict["stream"]:
                if putDict["stream"]["active"]:
                    logging.info("start hue entertainment")
                    Thread(target=entertainmentService, args=[bridgeConfig["groups"][resourceid], bridgeConfig["apiUsers"][username]]).start()
                else:
                    logging.info("stop hue entertainent")
                    Popen(["killall", "entertain-srv"])

        updateDict = putDict.copy()
        if "lights" in putDict:
            lights = []
            for light in putDict["lights"]:
                lights.append(bridgeConfig["lights"][light])
            updateDict["lights"] = lights
        bridgeConfig[resource][resourceid].update_attr(updateDict)
        responseDictionary = []
        response_location = "/" + resource + "/" + resourceid + "/"
        for key, value in putDict.items():
            responseDictionary.append(
                {"success": {response_location + key: value}})
        return responseDictionary

    def delete(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if resource == "resourcelinks":
            for link in bridgeConfig[resourcelinks].links:
                if hasattr(link, "recycle") and link.recycle:
                    del link
        del bridgeConfig[resource][resourceid]
        return [{"success": "/" + resource + "/" + resourceid + " deleted."}]
        configManager.bridgeConfig.save_config()


class ElementParam(Resource):
    def get(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        return bridgeConfig[resource][resourceid][param]

    def put(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        currentTime = datetime.now()
        pprint(putDict)

        if param == "state":  # state is applied to a light
            bridgeConfig[resource][resourceid].setV1State(putDict)
        elif param == "action":  # state is applied to a light
            if "scene" in putDict:
                bridgeConfig[resource][resourceid].setV1Action(state={}, scene=bridgeConfig["scenes"][putDict["scene"]])
            else:
                bridgeConfig[resource][resourceid].setV1Action(state=putDict, scene=None)
        responseDictionary = []
        responseLocation = "/" + resource + "/" + resourceid + "/" + param + "/"
        for key, value in putDict.items():
            responseDictionary.append(
                {"success": {responseLocation + key: value}})
        return responseDictionary

    def delete(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error": {"type": 4, "address": "/" + resource + "/" + resourceid, "description": "method, DELETE, not available for resource,  " + resource + "/" + resourceid}}]

        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]
        configManager.bridgeConfig.save_config()