#!/usr/bin/env python3

import serial
import paho.mqtt.client as mqtt
import logging
import json
import time
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s | %(message)s", level=logging.DEBUG)


def testConnect(client, userdata, flags, reason_code, properties):
    #logger.debug(client, userdata, flags, reason_code, properties)
    if s:
        s.onConnect(client, userdata, flags, reason_code, properties)

def testMessage(client, userdata, message):
    #logger.debug(client, userdata, message)
    if s:
        s.onMessage(client, userdata, message)


class SerialClient:

    def __init__(self, port="/dev/ttyUSB0"):
        logger.debug(f"connecting to {port}")
        self.client = serial.Serial(port=port)

    def readIncoming(self):
        read = self.client.read_all().decode('ascii')
        logger.debug(f"reading serial incoming {read}")
        if read == "":
            return []
        return read.split('\r\n')

    def sendOutgoing(self, outgoing):
        if outgoing and len(outgoing) > 0:
            self.client.write(outgoing)


class PWMFAN:

    def __init__(self):
        self.pwm = 0
        self.rpm = 0

    def update(self, line):
        if line:
            parsed = None
            try:
                parsed = json.loads(line)
            except Exception:
                pass
            if parsed:
                if "pwm" in parsed:
                    self.pwm = parsed["pwm"]
                if "rpm" in parsed:
                    self.rpm = parsed["rpm"]

    def json(self):
        return json.dumps({"pwm": self.pwm, "rpm": self.rpm, "time": int(time.time())})

    def __str__(self):
        return json.dumps({"pwm": self.pwm, "rpm": self.rpm})


class Subscriber:

    def __init__(self, host="localhost", port=1883, topic="#", *args, **kwargs):
        self.host = host
        self.port = port
        self.topic = topic
        self._callbacks = {"on_connect": [], "on_message": []}
        if args:
            logger.debug("args:", args)
        self.args = args
        if kwargs:
            logger.debug("kwargs:", kwargs)
            if "on_publish" in kwargs:
                if isinstance(kwargs["callbacks"], dict):
                    self._callbacks = kwargs["callbacks"]
                elif isinstance(kwargs["callbacks"], (list, tuple)):
                    self._callbacks["on_message"] = kwargs["callbacks"]
                    self._callbacks["on_connect"] = kwargs["callbacks"]
        self.kwargs = kwargs
        self.incoming = []

    def callbacks(self, callbacks=None):
        if callbacks:
            self._callbacks = callbacks
        return self.callbacks

    def getIncoming(self):
        val = None
        if len(self.incoming) > 0:
            val = self.incoming[0]
            self.incoming = self.incoming[1:]
        return val


    def onConnect(self, client, userdata, flags, reason_code, properties):
        logger.debug(f"received connect: {[client, userdata, flags, reason_code, properties]}")
        for f in self._callbacks["on_connect"]:
            logger.debug(f"calling {f} with {[client, userdata, flags, reason_code, properties]}")
            f(client, userdata, flags, reason_code, properties)
        if self.topic:
            logger.debug(f"starting subscribe to {self.topic}")
            self.client.subscribe(f"{self.topic}/#")

    def onMessage(self, client, userdata, message):
        logger.debug(f"received message: {[client, userdata, message]}")
        for f in self._callbacks["on_message"]:
            logger.debug(f"calling {f} with {[client, userdata, message]}")
            f(client, userdata, message)
        if message:
            self.printMessage(message.topic, message.payload)
            if message.topic == f"{self.topic}/SET":
                self.incoming.append(message.payload)

    def printMessage(self, topic, payload):
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        logger.info(f"[{topic}]: {payload}")

    def connect(self, host=None, port=None):
        if host is None:
            host = self.host
        if port is None:
            port = self.port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = testConnect
        self.client.on_message = testMessage
        self.client.connect(host, port, 60)

    def loop(self):
        self.client.loop_start()

    def publish(self, topic, payload):
        self.client.publish(topic, payload)


def mainloop(cfg, s, sc, faninit):
    lastPublish = None
    fan = faninit
    while 1:
        if sc:
            serialIncoming = sc.readIncoming()
            for line in serialIncoming:
                if line == "":
                    continue
                logger.debug(f"parsing line: {line}")
                tmpfan = PWMFAN()
                tmpfan.update(line)
                if str(tmpfan) != str(fan):
                    if tmpfan.pwm != fan.pwm:
                        logger.debug(f"detected new value {tmpfan}")
                        lastPublish = None
                    fan = tmpfan
        if s:
            m = s.getIncoming()
            if m:
                payload = m
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8')
                parsed = json.loads(payload)
                if "pwm" in parsed and parsed["pwm"] != fan.pwm:
                    sc.sendOutgoing([parsed["pwm"], 0])
            if fan is not None:
                if lastPublish is None or time.time() - lastPublish > cfg["mqtt"]["publishInterval"]:
                    s.publish(cfg["mqtt"]["topic"], fan.json())
                    lastPublish = time.time()
            #s.loop()
        time.sleep(cfg["serial"]["timeout"])


if __name__ == "__main__":
    cfg = yaml.load(open("config.yml", "r"), yaml.Loader)
    fan = PWMFAN()
    sc = SerialClient(cfg["serial"]["port"])
    s = Subscriber(host=cfg["mqtt"]["host"], port=cfg["mqtt"]["port"], topic=cfg["mqtt"]["topic"])
    try:
        s.connect()
        s.loop()
        mainloop(cfg, s, sc, fan)
    except KeyboardInterrupt:
        if s.client:
            s.client.disconnect()
        logging.info("stopping connection")


