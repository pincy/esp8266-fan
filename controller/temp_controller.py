#!/usr/bin/env python

import json
import logging
import re
import subprocess
import time
import yaml

import paho.mqtt.publish as publish

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s | %(message)s", level=logging.INFO)


def getSensors():
    res = subprocess.run(["sensors", "-jA"], capture_output=True, encoding="utf-8")
    if res.returncode == 0:
        return json.loads(res.stdout)
    logger.error(f"subprocess returned with exit code {res.returncode}\nstdout: {res.stdout}\nstderr: {res.stderr}")
    return None

def sendPWM(hostname, port, topic, pwm):
    message = json.dumps({"pwm": pwm})
    try:
        publish.single(topic, message, hostname=hostname, port=port)
    except Exception:
        logger.error(f"error sending new pwm message!")


def mainloop(cfg):
    if "sensors" not in cfg:
        print("no sensor configuration present! exit")
        exit(1)

    sleeptime = cfg["controller"]["timeout"]
    lastpwm = 0
    errcount = 0
    while 1:
        sleepiter = sleeptime
        targetpwm = 0
        sensormap = {}
        sensors = getSensors()
        if sensors is None:
            errcount += 1
            if errcount == 5:
                logger.error("could not get sensor data")
                exit(1)
            time.sleep(sleeptime)
            continue

        for dev in sensors.keys():
            for sensor in sensors[dev].keys():
                for temp in sensors[dev][sensor].keys():
                    if temp.endswith("input"):
                        sensormap[dev] = sensors[dev][sensor][temp]

        for dev in sensormap.keys():
            devpwm = 0
            logger.debug(f"{dev}: {sensormap[dev]}")
            for key in cfg["sensors"].keys():
                if re.match(key, dev):
                    for t in cfg["sensors"][key].keys():
                        if sensormap[dev] > t:
                            devpwm = cfg["sensors"][key][t]
                    logger.debug(f"match on {key}, new pwm {devpwm}")
                    break
            targetpwm = max(targetpwm, devpwm)
        if lastpwm != targetpwm:
            logger.info(f"new pwm {targetpwm}, keep it for 2 * timeout")
            if targetpwm > lastpwm:
                sleepiter = sleepiter * 2.0
            lastpwm = targetpwm
            sendPWM(cfg["mqtt"]["host"], cfg["mqtt"]["port"], f"{cfg['mqtt']['topic']}/SET", targetpwm) 
        time.sleep(sleepiter)


if __name__ == "__main__":
    cfg = yaml.load(open("config.yml", "r"), yaml.Loader)
    try:
        mainloop(cfg)
    except KeyboardInterrupt:
        pass
