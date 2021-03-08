import pytz
from astral.sun import sun
from astral import LocationInfo
from functions.rules import rulesProcessor
from datetime import datetime
from time import sleep
import logManager
import configManager

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)

def daylightSensor():
    sensor = bridgeConfig["sensors"]["1"]
    localzone = LocationInfo('localzone', bridgeConfig["config"]["timezone"].split("/")[1], bridgeConfig["config"]["timezone"], float(bridgeConfig["config"]["daylight"]["lat"][:-1]), float(ridgeConfig["config"]["daylight"]["long"][:-1]))
    s = sun(localzone.observer, date=datetime.utcnow())
    deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.utcnow()
    deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.utcnow()
    deltaSunsetOffset = deltaSunset.total_seconds() + sensor.config["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + sensor.config["sunriseoffset"] * 60
    logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.utcnow()
    if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
        sensor.state = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to true")
    else:
        sensor.state = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to false")
    if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
        logging.info("will start the sleep for sunset")
        sleep(deltaSunsetOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        sensor.state = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        sensor.dxstate["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.info("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        sensor.state = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}

        sensor.dxstate["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)
