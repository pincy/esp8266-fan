const int FAN_PIN = D5;
const int SIGNAL_PIN = D6;

const int sleeptime = 2 * 1000;

int FAN_SPEED_PERCENT = 50;

/* By default PWM frequency is 1000Hz and we are using same 
 for this application hence no need to set */
void setup()
{
  Serial.begin(9600);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(SIGNAL_PIN, INPUT);
  // power on FAN
  analogWrite(FAN_PIN, (FAN_SPEED_PERCENT/100.0)*255);
}

int getFanSpeedRpm() {
  int highTime = pulseIn(SIGNAL_PIN, HIGH);
  int lowTime = pulseIn(SIGNAL_PIN, LOW);
  int period = highTime + lowTime;
  if (period == 0) {
    return 0;
  }
  float freq = 1000000.0 / (float)period;
  return (freq * 60.0) / 2.0; // two cycles per revolution
}

void setFanSpeedPercent(int p) {
  int value = (p / 100.0) * 255;
  analogWrite(FAN_PIN, value);
}

void printStatus(int p) {
  Serial.print("{\"pwm\": ");
  Serial.print(FAN_SPEED_PERCENT);
  Serial.print(", \"rpm\": ");
  Serial.print(p);
  Serial.print("}");
  Serial.println();
}
 
void loop()
{
  char control;
  int actualFanSpeedRpm = getFanSpeedRpm();
  // check serial for new value
  if (Serial.available()) {
    control = Serial.read();
    // serial could hold multiple values, read until NULL
    while (control != 0) {
      FAN_SPEED_PERCENT = control - 1;
      setFanSpeedPercent(FAN_SPEED_PERCENT);
      if (Serial.available() > 0) {
        control = Serial.read();  
      }
      else {
        control = 0;
      }
    }
  }
  
  printStatus(actualFanSpeedRpm);
  
  delay(sleeptime);
}
