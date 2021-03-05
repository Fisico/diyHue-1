import logManager
import configManager
import socket
import json
from time import sleep
from services.deconz import scanDeconz
from lights.protocols import mqtt, yeelight, native, native_single, native_multi, tasmota, shelly, esphome, tradfri
from functions.core import  generateDxState

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def addNewLight(modelid, name, emulatorLightConfig):
    newLightID = nextFreeId(bridgeConfig, "lights")
    if modelid in lightTypes:
        light = lightTypes[modelid]
        light["name"] = name
        light["modelid"] = modelid
        light["uniqueid"] = generate_unique_id()
        bridgeConfig["lights"][newLightID] = light.copy()
        bridgeConfig["emulator"]["lights"][newLightID] = emulatorLightConfig
        newLights[newLightID] = {"name": name}
        #add v2 uuid
        lightUuid = str(uuid.uuid4())
        zigBeeUuid = str(uuid.uuid4())
        deviceUuid = str(uuid.uuid4())
        bridgeConfig["emulator"]["links"]["v2"]["light"][lightUuid] = {"id_v1": newLightID, "zigBeeUuid": zigBeeUuid, "deviceUuid": deviceUuid}
        bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"][zigBeeUuid] = {"lightUuid": lightUuid, "id_v1": newLightID, "resource": "lights"}
        bridgeConfig["emulator"]["links"]["v2"]["device"][deviceUuid] = {"lightUuid": lightUuid, "id_v1": newLightID, "resource": "lights", "zigbee_connectivity": zigBeeUuid}
        bridgeConfig["emulator"]["links"]["v1"]["lights"][newLightID] = lightUuid
        if "streaming" in bridgeConfig["lights"][newLightID]["capabilities"]:
            entertianmentUuid = str(uuid.uuid4())
            bridgeConfig["emulator"]["links"]["v2"]["entertainment"][entertianmentUuid] = {"lightUuid": lightUuid, "id_v1": newLightID}
            bridgeConfig["emulator"]["links"]["v2"]["device"][deviceUuid]["entertianmentUuid"] = entertianmentUuid
            bridgeConfig["emulator"]["links"]["v2"]["light"][lightUuid]["entertianmentUuid"] = entertianmentUuid
        return newLightID
    return False


def scanForLights(): #scan for ESP8266 lights and strips
    newLights = {"lastscan": "active"}
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    mqtt.discover()
    yeelight.discover()
    native_multi.discover(device_ips) # native_multi probe all esp8266 lights with firmware from diyhue repo
    tasmota.discover(device_ips)
    shelly.discover(device_ips)
    esphome.discover(device_ips)
    tradfri.discover()
    scanDeconz()
    configManager.bridgeConfig.save_config()
    generateDxState()
