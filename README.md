# esp8266-mqtt-fan-control

Control a pwm fan with an ESP8266 board from a linux host.

Based on [esp8266-fan-control](https://github.com/stefanthoss/esp8266-fan-control/).

Connect a esp8266 based board by USB to a linux based computer and control the fan via serial port (ttyUSB).

## ESP8266 Firmware

* *FAN_PIN* D5
* *SIGNAL_PIN* D6

The firmware is simple and intended to give control to the connected system.

After boot, the esp8266 sets the PWM signal to 50%.
From then on, it tries to read the sense signal from D6 and checks for new values to set PWM to.
The current state is written to the serial port as json.

> {"pwm": 40, "rpm": 720}

I decided to go with basic int values, interpreted as percent and use the `0` byte (\0) as end of message mark.
So writing a value of 1 to the serial console will set the PWM to 0%, for 100% you need to write the value `101`.

The esp will read all bytes available per loop iteration, and stop reading on this iteration on `0`. This gave me reliable results on the control.

## Python Controller

The python controller is simple decoupling serial interaction from the controlling logic and consists of two parts.

### [mqtt-serial-bridge](controller/mqtt-serial-bridge.py)

Simple serial to mqtt bridge to publish the values read via serial `/dev/ttyUSB0` from the esp8266 published to `TOPIC`
> {"pwm": 40, "rpm": 720, "time": 1729550842}

 and write new values incoming with `TOPIC/SET`
> {"pwm": 1}

### [temp_controller](controller/temp_controller.py)

Simple controller, reading values from `sensors` and publishing new PWM values according to configuration.

On each iteration the controller checks all directives and applies the highest evaluated value to be published to `TOPIC/SET`.

### Configuration

Each block under the `sensors` directive is a regex pattern and consists of an array of key-value pairs 

**Temperature min trigger**: **PWM Value**

## Usecase Zimablade

Using 2 8TB HDDs in the HDD stand, with the Zimablade on top, the disks accumulated a little warmth on full disk rotation over time.
I observed values up to 55°C on both hdds.
In order to keep everything in a comfortable temperature area,
i just placed a 12cm PWM fan next to the front/back of the stand.

The fan is now in place for some weeks and the pwm values range from 0-40% most of the time,
while hdd temperatures are below 40°C.

The Zimablades FAN_PWN Pinout, it is documented well [here](https://community.zimaspace.com/t/fan-wiring-and-resource-tutorial-for-zimaboard/238).

| Zimablade Pin | Name | Arctic Pin |
| --- | ---- | --- |
| 1 | Ground | 1 |
| 2 | +12V | 2 |
| 3 | Sense | 3 |
| 4 | Control (PWM) | 4 |


To connect the Zimablade you need a Micro JST MX 1.25mm pitch.
You can connect the connected jumper cables directly into the female fan connector.

### Flaws of the Zimablade

[Zimablade BIOS issue 3](https://github.com/IceWhaleTech/ZimaBoard-BIOS/issues/3)
* The sensed value is only shown in UEFI and not propagated to the system
* The fan stays at 0 rpm as soon Control from Zimablade and PWM of the fan is connected

### Workaround

With the esp8266 the sensed rpm value is accessible in the system and the pwm is controllable, while the Zimablade supplies 12V for the fan.

![Circuit connections](esp8266-fan-control-diagram.drawio.svg)

The 2kΩ resistor is a [pull-up resistor](https://en.wikipedia.org/wiki/Pull-up_resistor) and can be replaced with any resistor with **at least** 2kΩ.
I only had 4.7kΩ resistors at hand and at it worked for me.

The 2kΩ was mentioned in the technical specifications by Arctic, found [here](https://support.arctic.de/f12-pwm-pst).

The pin layout on the Arctic F12 PWM matches the pin layout on the Zimablade, i only copied and altered the graphics from [esp8266-fan-control](https://github.com/stefanthoss/esp8266-fan-control/), but did not move the pins on the pwm fan for less intersections in the graphic.

## Requirements

* [Arduino IDE](https://www.arduino.cc/en/software)
> apt install arduino

* [Python requirements](controller/requirements.txt)

* `lm-sensors` with its `sensors` binary

* a mqtt-broker (e.g. [Eclipse Mosquitto](https://hub.docker.com/_/eclipse-mosquitto))

* Hardware:
  * PWM fan (i used Arctic F12 PWM)
  * esp8266 (i used a NodeMCU Board)
  * (at least) 2kΩ resistor
  * Micro JST MX 1.25mm pitch
  * enough jumper cables to connect everything


## DISCLAIMER

This is the time i programmed for Arduino.

Though the Noctua and Arctic pwm fans are seemingly comparable,
check your fan specifications before frying anything.

The linux host needs enough power to supply the esp board.

The python code is pretty simple and sufficient. Don't expect me to extend it
to your needs in the near future.

The mqtt client is without user password authentication.

The project is as-is, do your own research, if all applies to you.

