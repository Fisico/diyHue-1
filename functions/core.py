import logManager
import configManager
import random
import uuid
from time import sleep
from datetime import datetime
#from functions.rules import rulesProcessor

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights

def nextFreeId(bridgeConfig, element):
    i = 1
    while (str(i)) in bridgeConfig[element]:
        i += 1
    return str(i)

def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def longPressButton(sensor, buttonevent):
    print("running.....")
    logging.info("long press detected")
    sleep(1)
    while bridgeConfig["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        dxState["sensors"][sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(["sensors",sensor], current_time)
        sleep(0.5)
    return

def addHueMotionSensor(uniqueid, name="Hue motion sensor"):
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id
        else:
            uniqueid += new_sensor_id
    bridgeConfig["sensors"][nextFreeId(bridgeConfig, "sensors")] =  {"state": {"temperature": None,"lastupdated": "none"},"swupdate": {"state": "noupdates","lastinstall": "2019-03-16T21:16:40"},"config": {"on": False,"battery": 100,"reachable": True,"alert": "none","ledindication": False,"usertest": False,"pending": []},"name": "Hue temperature sensor " + new_sensor_id,"type": "ZLLTemperature","modelid": "SML001","manufacturername": "Signify Netherlands B.V.","productname": "Hue temperature sensor","swversion": "6.1.1.27575","uniqueid": uniqueid + ":d0:5b-02-0402","capabilities": {"certified": True,"primary": False}}
    motion_sensor = nextFreeId(bridgeConfig, "sensors")
    bridgeConfig["sensors"][motion_sensor] = { "state": {"lastupdated": "none","presence": None  }, "swupdate": {"state": "noupdates","lastinstall": "2019-03-16T21:16:40"  }, "config": {"on": False,"battery": 100,"reachable": True,"alert": "none","ledindication": False,"usertest": False,"sensitivity": 2,"sensitivitymax": 2,"pending": []  }, "name": name, "type": "ZLLPresence", "modelid": "SML001", "manufacturername": "Signify Netherlands B.V.", "productname": "Hue motion sensor", "swversion": "6.1.1.27575", "uniqueid": uniqueid + ":d0:5b-02-0406", "capabilities":{"certified":True,"primary":True}}
    bridgeConfig["sensors"][nextFreeId(bridgeConfig, "sensors")] = {"state": {"dark": True,"daylight": False,"lightlevel": 6000,"lastupdated": "none"},"swupdate": {  "state": "noupdates",  "lastinstall": "2019-03-16T21:16:40"},"config": {"on": False,"battery": 100,"reachable": True,"alert": "none","tholddark": 9346,"tholdoffset": 7000,"ledindication": False,"usertest": False,"pending": []},"name": "Hue ambient light sensor " + new_sensor_id,"type": "ZLLLightLevel","modelid": "SML001","manufacturername": "Signify Netherlands B.V.","productname": "Hue ambient light sensor","swversion": "6.1.1.27575","uniqueid": uniqueid + ":d0:5b-02-0400","capabilities": {  "certified": True,  "primary": False}}
    #add v2 uuids
    deviceUuid = str(uuid.uuid4())
    zigBeeUuid = str(uuid.uuid4())
    batteryUuid = str(uuid.uuid4())
    lightUuid = str(uuid.uuid4())
    motionUuId = str(uuid.uuid4())
    temperatureUuid = str(uuid.uuid4())
    bridgeConfig["emulator"]["links"]["v2"]["device"][deviceUuid] = {"id_v1": motion_sensor, "resource": "sensors", "deviceUuid": deviceUuid, "zigBeeUuid": zigBeeUuid, "batteryUuid": batteryUuid, "motionUuId": motionUuId, "temperatureUuid": temperatureUuid, "lightUuid": lightUuid}
    bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"][zigBeeUuid] = {"id_v1": motion_sensor, "resource": "sensors"}
    bridgeConfig["emulator"]["links"]["v2"]["motion"][zigBeeUuid] = {"id_v1": motion_sensor, "motionUuId": motionUuId, "deviceUuid": deviceUuid}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    bridgeConfig["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)

def generateDxState():
    for sensor in bridgeConfig["sensors"]:
        if sensor not in dxState["sensors"] and "state" in bridgeConfig["sensors"][sensor]:
            dxState["sensors"][sensor] = {"state": {}}
            for key in bridgeConfig["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in bridgeConfig["groups"]:
        if group not in dxState["groups"] and "state" in bridgeConfig["groups"][group]:
            dxState["groups"][group] = {"state": {}}
            for key in bridgeConfig["groups"][group]["state"].keys():
                dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in bridgeConfig["lights"]:
        if light not in dxState["lights"] and "state" in bridgeConfig["lights"][light]:
            dxState["lights"][light] = {"state": {}}
            for key in bridgeConfig["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    dxState["lights"][light]["state"].update({key: datetime.now()})

def staticConfig():
    return {
        "backup": {
            "errorcode": 0,
            "status": "idle"
        },
        "datastoreversion": "98",
        "dhcp": True,
        "factorynew": False,
        "internetservices": {
            "internet": "disconnected",
            "remoteaccess": "disconnected",
            "swupdate": "disconnected",
            "time": "disconnected"
        },
        "linkbutton": False,
        "modelid": "BSB002",
        "portalconnection": "disconnected",
        "portalservices": True,
        "portalstate": {
            "communication": "disconnected",
            "incoming": False,
            "outgoing": False,
            "signedon": False
        },
        "proxyaddress": "none",
        "proxyport": 0,
        "replacesbridgeid": None,
        "starterkitid": "",
        "swupdate": {
            "checkforupdate": False,
            "devicetypes": {
                "bridge": False,
                "lights": [],
                "sensors": []
            },
            "notify": True,
            "text": "",
            "updatestate": 0,
            "url": ""
        },
        "swupdate2": {
            "autoinstall": {
                "on": True,
                "updatetime": "T14:00:00"
            },
            "bridge": {
                "lastinstall": "2020-12-11T17:08:55",
                "state": "noupdates"
            },
            "checkforupdate": False,
            "lastchange": "2020-12-13T10:30:15",
            "state": "unknown"
        },
        "zigbeechannel": 25
    }

def capabilities():
    return  {"groups":{
         "available":64
      },
      "lights":{
         "available":63
      },
      "resourcelinks":{
         "available":64
      },
      "rules":{
         "actions":{
            "available":400
         },
         "available":200,
         "conditions":{
            "available":400
         }
      },
      "scenes":{
         "available":200,
         "lightstates":{
            "available":2048
         }
      },
      "schedules":{
         "available":100
      },
      "sensors":{
         "available":63,
         "clip":{
            "available":63
         },
         "zgp":{
            "available":63
         },
         "zll":{
            "available":63
         }
      },
      "streaming":{
            "available":63
      },
      "timezones":{
         "values":[
            "CET",
            "CST6CDT",
            "EET",
            "EST",
            "EST5EDT",
            "HST",
            "MET",
            "MST",
            "MST7MDT",
            "PST8PDT",
            "WET",
            "Africa/Abidjan",
            "Africa/Accra",
            "Africa/Addis_Ababa",
            "Africa/Algiers",
            "Africa/Asmara",
            "Africa/Bamako",
            "Africa/Bangui",
            "Africa/Banjul",
            "Africa/Bissau",
            "Africa/Blantyre",
            "Africa/Brazzaville",
            "Africa/Bujumbura",
            "Africa/Cairo",
            "Africa/Casablanca",
            "Africa/Ceuta",
            "Africa/Conakry",
            "Africa/Dakar",
            "Africa/Dar_es_Salaam",
            "Africa/Djibouti",
            "Africa/Douala",
            "Africa/El_Aaiun",
            "Africa/Freetown",
            "Africa/Gaborone",
            "Africa/Harare",
            "Africa/Johannesburg",
            "Africa/Juba",
            "Africa/Kampala",
            "Africa/Khartoum",
            "Africa/Kigali",
            "Africa/Kinshasa",
            "Africa/Lagos",
            "Africa/Libreville",
            "Africa/Lome",
            "Africa/Luanda",
            "Africa/Lubumbashi",
            "Africa/Lusaka",
            "Africa/Malabo",
            "Africa/Maputo",
            "Africa/Maseru",
            "Africa/Mbabane",
            "Africa/Mogadishu",
            "Africa/Monrovia",
            "Africa/Nairobi",
            "Africa/Ndjamena",
            "Africa/Niamey",
            "Africa/Nouakchott",
            "Africa/Ouagadougou",
            "Africa/Porto-Novo",
            "Africa/Sao_Tome",
            "Africa/Tripoli",
            "Africa/Tunis",
            "Africa/Windhoek",
            "America/Adak",
            "America/Anchorage",
            "America/Anguilla",
            "America/Antigua",
            "America/Araguaina",
            "America/Aruba",
            "America/Asuncion",
            "America/Atikokan",
            "America/Bahia",
            "America/Bahia_Banderas",
            "America/Barbados",
            "America/Belem",
            "America/Belize",
            "America/Blanc-Sablon",
            "America/Boa_Vista",
            "America/Bogota",
            "America/Boise",
            "America/Cambridge_Bay",
            "America/Campo_Grande",
            "America/Cancun",
            "America/Caracas",
            "America/Cayenne",
            "America/Cayman",
            "America/Chicago",
            "America/Chihuahua",
            "America/Costa_Rica",
            "America/Creston",
            "America/Cuiaba",
            "America/Curacao",
            "America/Danmarkshavn",
            "America/Dawson",
            "America/Dawson_Creek",
            "America/Denver",
            "America/Detroit",
            "America/Dominica",
            "America/Edmonton",
            "America/Eirunepe",
            "America/El_Salvador",
            "America/Fort_Nelson",
            "America/Fortaleza",
            "America/Glace_Bay",
            "America/Godthab",
            "America/Goose_Bay",
            "America/Grand_Turk",
            "America/Grenada",
            "America/Guadeloupe",
            "America/Guatemala",
            "America/Guayaquil",
            "America/Guyana",
            "America/Halifax",
            "America/Havana",
            "America/Hermosillo",
            "America/Inuvik",
            "America/Iqaluit",
            "America/Jamaica",
            "America/Juneau",
            "America/Kralendijk",
            "America/La_Paz",
            "America/Lima",
            "America/Los_Angeles",
            "America/Lower_Princes",
            "America/Maceio",
            "America/Managua",
            "America/Manaus",
            "America/Marigot",
            "America/Martinique",
            "America/Matamoros",
            "America/Mazatlan",
            "America/Menominee",
            "America/Merida",
            "America/Metlakatla",
            "America/Mexico_City",
            "America/Miquelon",
            "America/Moncton",
            "America/Monterrey",
            "America/Montevideo",
            "America/Montserrat",
            "America/Nassau",
            "America/New_York",
            "America/Nipigon",
            "America/Nome",
            "America/Noronha",
            "America/Ojinaga",
            "America/Panama",
            "America/Pangnirtung",
            "America/Paramaribo",
            "America/Phoenix",
            "America/Port-au-Prince",
            "America/Port_of_Spain",
            "America/Porto_Velho",
            "America/Puerto_Rico",
            "America/Punta_Arenas",
            "America/Rainy_River",
            "America/Rankin_Inlet",
            "America/Recife",
            "America/Regina",
            "America/Resolute",
            "America/Rio_Branco",
            "America/Santarem",
            "America/Santiago",
            "America/Santo_Domingo",
            "America/Sao_Paulo",
            "America/Scoresbysund",
            "America/Sitka",
            "America/St_Barthelemy",
            "America/St_Johns",
            "America/St_Kitts",
            "America/St_Lucia",
            "America/St_Thomas",
            "America/St_Vincent",
            "America/Swift_Current",
            "America/Tegucigalpa",
            "America/Thule",
            "America/Thunder_Bay",
            "America/Tijuana",
            "America/Toronto",
            "America/Tortola",
            "America/Vancouver",
            "America/Whitehorse",
            "America/Winnipeg",
            "America/Yakutat",
            "America/Yellowknife",
            "America/Argentina/Buenos_Aires",
            "America/Argentina/Catamarca",
            "America/Argentina/Cordoba",
            "America/Argentina/Jujuy",
            "America/Argentina/La_Rioja",
            "America/Argentina/Mendoza",
            "America/Argentina/Rio_Gallegos",
            "America/Argentina/Salta",
            "America/Argentina/San_Juan",
            "America/Argentina/San_Luis",
            "America/Argentina/Tucuman",
            "America/Argentina/Ushuaia",
            "America/Indiana/Indianapolis",
            "America/Indiana/Knox",
            "America/Indiana/Marengo",
            "America/Indiana/Petersburg",
            "America/Indiana/Tell_City",
            "America/Indiana/Vevay",
            "America/Indiana/Vincennes",
            "America/Indiana/Winamac",
            "America/Kentucky/Louisville",
            "America/Kentucky/Monticello",
            "America/North_Dakota/Beulah",
            "America/North_Dakota/Center",
            "America/North_Dakota/New_Salem",
            "Antarctica/Casey",
            "Antarctica/Davis",
            "Antarctica/DumontDUrville",
            "Antarctica/Macquarie",
            "Antarctica/Mawson",
            "Antarctica/McMurdo",
            "Antarctica/Palmer",
            "Antarctica/Rothera",
            "Antarctica/Syowa",
            "Antarctica/Troll",
            "Antarctica/Vostok",
            "Arctic/Longyearbyen",
            "Asia/Aden",
            "Asia/Almaty",
            "Asia/Amman",
            "Asia/Anadyr",
            "Asia/Aqtau",
            "Asia/Aqtobe",
            "Asia/Ashgabat",
            "Asia/Atyrau",
            "Asia/Baghdad",
            "Asia/Bahrain",
            "Asia/Baku",
            "Asia/Bangkok",
            "Asia/Barnaul",
            "Asia/Beirut",
            "Asia/Bishkek",
            "Asia/Brunei",
            "Asia/Chita",
            "Asia/Choibalsan",
            "Asia/Colombo",
            "Asia/Damascus",
            "Asia/Dhaka",
            "Asia/Dili",
            "Asia/Dubai",
            "Asia/Dushanbe",
            "Asia/Famagusta",
            "Asia/Gaza",
            "Asia/Hebron",
            "Asia/Ho_Chi_Minh",
            "Asia/Hong_Kong",
            "Asia/Hovd",
            "Asia/Irkutsk",
            "Asia/Istanbul",
            "Asia/Jakarta",
            "Asia/Jayapura",
            "Asia/Jerusalem",
            "Asia/Kabul",
            "Asia/Kamchatka",
            "Asia/Karachi",
            "Asia/Kathmandu",
            "Asia/Khandyga",
            "Asia/Kolkata",
            "Asia/Krasnoyarsk",
            "Asia/Kuala_Lumpur",
            "Asia/Kuching",
            "Asia/Kuwait",
            "Asia/Macau",
            "Asia/Magadan",
            "Asia/Makassar",
            "Asia/Manila",
            "Asia/Muscat",
            "Asia/Nicosia",
            "Asia/Novokuznetsk",
            "Asia/Novosibirsk",
            "Asia/Omsk",
            "Asia/Oral",
            "Asia/Phnom_Penh",
            "Asia/Pontianak",
            "Asia/Pyongyang",
            "Asia/Qatar",
            "Asia/Qyzylorda",
            "Asia/Riyadh",
            "Asia/Sakhalin",
            "Asia/Samarkand",
            "Asia/Seoul",
            "Asia/Shanghai",
            "Asia/Singapore",
            "Asia/Srednekolymsk",
            "Asia/Taipei",
            "Asia/Tashkent",
            "Asia/Tbilisi",
            "Asia/Tehran",
            "Asia/Thimphu",
            "Asia/Tokyo",
            "Asia/Tomsk",
            "Asia/Ulaanbaatar",
            "Asia/Urumqi",
            "Asia/Ust-Nera",
            "Asia/Vientiane",
            "Asia/Vladivostok",
            "Asia/Yakutsk",
            "Asia/Yangon",
            "Asia/Yekaterinburg",
            "Asia/Yerevan",
            "Atlantic/Azores",
            "Atlantic/Bermuda",
            "Atlantic/Canary",
            "Atlantic/Cape_Verde",
            "Atlantic/Faroe",
            "Atlantic/Madeira",
            "Atlantic/Reykjavik",
            "Atlantic/South_Georgia",
            "Atlantic/St_Helena",
            "Atlantic/Stanley",
            "Australia/Adelaide",
            "Australia/Brisbane",
            "Australia/Broken_Hill",
            "Australia/Currie",
            "Australia/Darwin",
            "Australia/Eucla",
            "Australia/Hobart",
            "Australia/Lindeman",
            "Australia/Lord_Howe",
            "Australia/Melbourne",
            "Australia/Perth",
            "Australia/Sydney",
            "Europe/Amsterdam",
            "Europe/Andorra",
            "Europe/Astrakhan",
            "Europe/Athens",
            "Europe/Belgrade",
            "Europe/Berlin",
            "Europe/Bratislava",
            "Europe/Brussels",
            "Europe/Bucharest",
            "Europe/Budapest",
            "Europe/Busingen",
            "Europe/Chisinau",
            "Europe/Copenhagen",
            "Europe/Dublin",
            "Europe/Gibraltar",
            "Europe/Guernsey",
            "Europe/Helsinki",
            "Europe/Isle_of_Man",
            "Europe/Istanbul",
            "Europe/Jersey",
            "Europe/Kaliningrad",
            "Europe/Kiev",
            "Europe/Kirov",
            "Europe/Lisbon",
            "Europe/Ljubljana",
            "Europe/London",
            "Europe/Luxembourg",
            "Europe/Madrid",
            "Europe/Malta",
            "Europe/Mariehamn",
            "Europe/Minsk",
            "Europe/Monaco",
            "Europe/Moscow",
            "Europe/Nicosia",
            "Europe/Oslo",
            "Europe/Paris",
            "Europe/Podgorica",
            "Europe/Prague",
            "Europe/Riga",
            "Europe/Rome",
            "Europe/Samara",
            "Europe/San_Marino",
            "Europe/Sarajevo",
            "Europe/Saratov",
            "Europe/Simferopol",
            "Europe/Skopje",
            "Europe/Sofia",
            "Europe/Stockholm",
            "Europe/Tallinn",
            "Europe/Tirane",
            "Europe/Ulyanovsk",
            "Europe/Uzhgorod",
            "Europe/Vaduz",
            "Europe/Vatican",
            "Europe/Vienna",
            "Europe/Vilnius",
            "Europe/Volgograd",
            "Europe/Warsaw",
            "Europe/Zagreb",
            "Europe/Zaporozhye",
            "Europe/Zurich",
            "Indian/Antananarivo",
            "Indian/Chagos",
            "Indian/Christmas",
            "Indian/Cocos",
            "Indian/Comoro",
            "Indian/Kerguelen",
            "Indian/Mahe",
            "Indian/Maldives",
            "Indian/Mauritius",
            "Indian/Mayotte",
            "Indian/Reunion",
            "Pacific/Apia",
            "Pacific/Auckland",
            "Pacific/Bougainville",
            "Pacific/Chatham",
            "Pacific/Chuuk",
            "Pacific/Easter",
            "Pacific/Efate",
            "Pacific/Enderbury",
            "Pacific/Fakaofo",
            "Pacific/Fiji",
            "Pacific/Funafuti",
            "Pacific/Galapagos",
            "Pacific/Gambier",
            "Pacific/Guadalcanal",
            "Pacific/Guam",
            "Pacific/Honolulu",
            "Pacific/Kiritimati",
            "Pacific/Kosrae",
            "Pacific/Kwajalein",
            "Pacific/Majuro",
            "Pacific/Marquesas",
            "Pacific/Midway",
            "Pacific/Nauru",
            "Pacific/Niue",
            "Pacific/Norfolk",
            "Pacific/Noumea",
            "Pacific/Pago_Pago",
            "Pacific/Palau",
            "Pacific/Pitcairn",
            "Pacific/Pohnpei",
            "Pacific/Port_Moresby",
            "Pacific/Rarotonga",
            "Pacific/Saipan",
            "Pacific/Tahiti",
            "Pacific/Tarawa",
            "Pacific/Tongatapu",
            "Pacific/Wake",
            "Pacific/Wallis",
            "US/Pacific-New"
         ]
      }
      }
