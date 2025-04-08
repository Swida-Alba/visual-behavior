//* communication with python running in a PC
//* receiving command from PC to switch ON/OFF the LED or deliver pulses

//* Note: for the "pulse" ("p") mode, pulse on is set at the start of the period.

int pin_LED = 5; //* the pin_LED to control relay
int pin_trigger = A0; //* the pin_LED to send trigger signal out
int pin_indicator = 13; //* indicator for LED, coordiated with "pin_LED" and "pin_trigger"

int pin_air = 10; //* the pin_air to control relay for air passage
int pin_odor_A = 11; //* the pin_odor_A to control relay for odor A 
int pin_odor_B = 12; //* * the pin_odor_B to control relay for odor B
int pin_shock = 8; //* the pin_shock to control relay for electric shock

int pin_pump = 3; //* the pin_pump to parse PWM signal to the air pump
int pump_value = 200; //* the value to control the pump, 0-255

const long baudRate = 9600;
String light_switch; //* read command from serial

//* parameters for pulsing at given frequency and duty cycle
double frequency   = 0, //* pulsing frequency in 'p' mode
       duty_cycle  = 0, //* not currently used, replaced by pulse_width
       period      = 0; //* pulsing period in 'p' mode, calculated from frequency
long   pulse_width = 0; //* specified pulse width
unsigned long t_period  = 0, //* elapsed time of the current period
              t0_period = 0, //* start time of a period
              t_pulse   = 0; //* elapsed time of the current pulse
boolean fpul = false; //* true: is in peak (pulse-on) phase; false: is in trough (pulse-off) phase
long t_span = 0, //* time of pulse span, in ms
     t_delay = 0; //* 
int d_pos = 0,
    f_pos = 0,
    w_pos = 0,
    len   = 0;

//* State tracking variables for non-blocking operation
String currentOperation = "none"; //* Current operation mode
unsigned long operationStartTime = 0; //* When the operation started
unsigned long operationEndTime = 0; //* When the operation should end
unsigned long delayEndTime = 0; //* When the delay should end
boolean isDelayed = false; //* If the operation is currently in delay

//* New state tracking variables for pump, shock, air, and odor controls
boolean pumpState = false;       //* Pump state (on/off)
boolean shockState = false;      //* Shock pulse state (on/off)
boolean airState = false;        //* Air state (on/off)
boolean odorAState = false;      //* Odor A state (on/off)
boolean odorBState = false;      //* Odor B state (on/off)

//* Shock pulse parameters
const float shockFrequency = 0.2;  //* Shock frequency in Hz
const long shockPulseWidth = 1250; //* Shock pulse width in ms (1.25s)
unsigned long shockPeriod = 5000;  //* Shock period in ms (5s = 1/0.2Hz)
unsigned long lastShockTime = 0;   //* Last time shock was triggered
boolean shockPulseOn = false;      //* Whether shock pulse is currently on
unsigned long shockPulseStart = 0; //* When current shock pulse started

void ResetPulse()
{
  digitalWrite(pin_LED, HIGH);
  digitalWrite(pin_indicator,HIGH);
  fpul = true;
  t_period    = 0;
  t0_period = millis();
  t_pulse   = 0;
}

//* Function to quit all operations
void quitAllOperations() {
  //* Turn off LED operations
  currentOperation = "none";
  digitalWrite(pin_LED, LOW);
  digitalWrite(pin_indicator, LOW);
  digitalWrite(pin_trigger, LOW);
  fpul = false;
  
  //* Turn off pump and related operations
  analogWrite(pin_pump, 0);
  pumpState = false;
  
  //* Turn off all solenoids (air, odor, shock)
  digitalWrite(pin_air, LOW);
  digitalWrite(pin_odor_A, LOW);
  digitalWrite(pin_odor_B, LOW);
  digitalWrite(pin_shock, LOW);
  airState = false;
  odorAState = false;
  odorBState = false;
  shockState = false;
  shockPulseOn = false;
  
  Serial.print("All operations terminated\n");
}

//* Define validateValveOperation function to check if pump is on before opening valves
boolean validateValveOperation() {
  if (!pumpState) {
    Serial.print("Warning: Cannot open valve - Pump is OFF\n");
    return false;
  }
  return true;
}

void setup()
{
  Serial.begin(baudRate);
  pinMode(pin_LED,OUTPUT);
  pinMode(pin_indicator,OUTPUT);
  pinMode(pin_trigger,OUTPUT);
  
  //* Set up new pin modes
  pinMode(pin_air, OUTPUT);
  pinMode(pin_odor_A, OUTPUT);
  pinMode(pin_odor_B, OUTPUT);
  pinMode(pin_shock, OUTPUT);
  pinMode(pin_pump, OUTPUT);
  
  //* Initialize all outputs to LOW
  digitalWrite(pin_air, LOW);
  digitalWrite(pin_odor_A, LOW);
  digitalWrite(pin_odor_B, LOW);
  analogWrite(pin_pump, 0);
  
  //* Calculate shock period from frequency
  shockPeriod = (unsigned long)(1000.0 / shockFrequency);
}

void loop()
{
  unsigned long currentTime = millis();
  
  //* Check for new commands
  if (Serial.available() > 0) 
  {
    light_switch = Serial.readStringUntil('\n'); //* read command from the connected PC
    
    //* Quit command takes precedence over all operations
    if (light_switch == "quit") {
      quitAllOperations();
    }
    else if (light_switch == "on") 
    { //* turn on the LED
      digitalWrite(pin_LED, HIGH);
      digitalWrite(pin_indicator, HIGH);
      currentOperation = "on";
      Serial.print("Light ON\n");
    }
    else if (light_switch == "off")
    { //* turn off the LED
      digitalWrite(pin_LED, LOW);
      digitalWrite(pin_indicator, LOW);
      currentOperation = "off";
      Serial.print("Light OFF\n");
    }
    else if (light_switch == "trigger")
    { //* send a 100ms trigger signal
      digitalWrite(pin_trigger, HIGH);
      digitalWrite(pin_indicator, HIGH);
      currentOperation = "trigger";
      operationStartTime = currentTime;
      operationEndTime = currentTime + 10; //* 10 ms trigger
      Serial.print("Trigger ON\n");
    }
    else if (light_switch.charAt(0) == 'r') //* 'r' mode, constant LED
    {
      //* Mutually exclusive with 'p' mode
      if (currentOperation == "p") {
        Serial.print("Error: Cannot start 'r' mode while in 'p' mode\n");
      } 
      else {
        d_pos = light_switch.indexOf('d'); //* delay time after 'd'
        len = light_switch.length();
        if (d_pos > -1)
        { //* if the turn-on command will be delayed for given time
          String span_str = "", d_str = "";
          for (int i=1; i<d_pos; i++) span_str += String(light_switch[i]);
          for (int i=d_pos+1; i<len; i++) d_str += String(light_switch[i]);
          t_delay = d_str.toInt();
          t_span = span_str.toInt();
          isDelayed = true;
          delayEndTime = currentTime + t_delay;
          currentOperation = "r";
          operationEndTime = delayEndTime + t_span;
        }
        else
        {
          light_switch.remove(0,1);
          t_span = light_switch.toInt();
          currentOperation = "r";
          operationStartTime = currentTime;
          operationEndTime = currentTime + t_span;
          digitalWrite(pin_LED, HIGH);
          digitalWrite(pin_indicator, HIGH);
          Serial.print("Light ON\n");
        }
      }
    }
    //* Pump commands
    else if (light_switch.startsWith("pump:")) {
      if (light_switch == "pump:on") {
        analogWrite(pin_pump, pump_value);
        pumpState = true;
        Serial.print("Pump ON\n");
      }
      else if (light_switch == "pump:off") {
        analogWrite(pin_pump, 0);
        pumpState = false;
        
        //* Turn off valves when pump is off to avoid overheating
        digitalWrite(pin_air, LOW);
        digitalWrite(pin_odor_A, LOW);
        digitalWrite(pin_odor_B, LOW);
        airState = false;
        odorAState = false;
        odorBState = false;

        Serial.print("Pump OFF and all valves are CLOSED\n");
      }
      else if (light_switch.startsWith("pump:value:")) {
        String value_str = light_switch.substring(11);
        int new_value = value_str.toInt();
        if (new_value >= 0 && new_value <= 255) {
          pump_value = new_value;
          if (pumpState) {
            analogWrite(pin_pump, pump_value);
          }
          Serial.print("Pump value set to ");
          Serial.print(pump_value);
          Serial.print("\n");
        } else {
          Serial.print("Invalid pump value. Must be between 0-255\n");
        }
      }
    }
    //* pulsing, 
    else if (light_switch.charAt(0) == 'p') 
    { //* 'p' mode, pulsing LED
      //* Mutually exclusive with 'r' mode
      if (currentOperation == "r") {
        Serial.print("Error: Cannot start 'p' mode while in 'r' mode\n");
      }
      else {
        f_pos = light_switch.indexOf('f');
        w_pos = light_switch.indexOf('w');
        len = light_switch.length();
        String f_str = "", w_str = "", t_str = "";
        for (int i=1; i<f_pos; i++) t_str += String(light_switch[i]);
        for (int i=f_pos+1; i<w_pos; i++) f_str += String(light_switch[i]);
        for (int i=w_pos+1; i<len; i++) w_str += String(light_switch[i]);
        t_span = t_str.toInt();
        long frequency_x1000 = f_str.toInt();
        pulse_width = w_str.toInt();
        frequency = double(frequency_x1000) / 1000;
        period = 1000.0 / frequency;

        //* Set up pulse mode
        currentOperation = "p";
        operationStartTime = currentTime;
        operationEndTime = currentTime + t_span;
        Serial.print("Pulsing ON\n");
        ResetPulse(); //* Start the first pulse
      }
    }
    //* Shock commands
    else if (light_switch.startsWith("shock:")) {
      if (light_switch == "shock:on") {
        shockState = true;
        digitalWrite(pin_shock, HIGH);
        shockPulseOn = true;
        shockPulseStart = currentTime;
        lastShockTime = currentTime;
        Serial.print("Shock pulses ON\n");
      }
      else if (light_switch == "shock:off") {
        shockState = false;
        digitalWrite(pin_shock, LOW);
        shockPulseOn = false;
        Serial.print("Shock pulses OFF\n");
      }
    }
    //* Air valve commands
    else if (light_switch.startsWith("air:")) {
      if (light_switch == "air:on") {
        if (validateValveOperation()) {  //* Keep this check to ensure pump is on
          digitalWrite(pin_air, HIGH);
          airState = true;
          Serial.print("Air valve OPEN\n");
        }
      }
      else if (light_switch == "air:off") {
        digitalWrite(pin_air, LOW);
        airState = false;
        Serial.print("Air valve CLOSED\n");
        //* No validation call here since we're just closing the valve
      }
    }
    //* Odor A valve commands
    else if (light_switch.startsWith("odor_a:")) {
      if (light_switch == "odor_a:on") {
        if (validateValveOperation()) {  //* Keep this check to ensure pump is on
          digitalWrite(pin_odor_A, HIGH);
          odorAState = true;
          Serial.print("Odor A valve OPEN\n");
        }
      }
      else if (light_switch == "odor_a:off") {
        digitalWrite(pin_odor_A, LOW);
        odorAState = false;
        Serial.print("Odor A valve CLOSED\n");
        //* No validation call here since we're just closing the valve
      }
    }
    //* Odor B valve commands
    else if (light_switch.startsWith("odor_b:")) {
      if (light_switch == "odor_b:on") {
        if (validateValveOperation()) {  //* Keep this check to ensure pump is on
          digitalWrite(pin_odor_B, HIGH);
          odorBState = true;
          Serial.print("Odor B valve OPEN\n");
        }
      }
      else if (light_switch == "odor_b:off") {
        digitalWrite(pin_odor_B, LOW);
        odorBState = false;
        Serial.print("Odor B valve CLOSED\n");
        //* No validation call here since we're just closing the valve
      }
    }
    else
    {
      digitalWrite(13, HIGH); //* if received unknown command, turn on the pin13 indicator
      Serial.print("Invalid Request\n");
    }
  }
  
  //* Handle ongoing operations - LED related
  if (currentOperation == "trigger") {
    if (currentTime >= operationEndTime) {
      digitalWrite(pin_trigger, LOW);
      digitalWrite(pin_indicator, LOW);
      Serial.print("Trigger OFF\n");
      currentOperation = "none";
    }
  }
  else if (currentOperation == "r") {
    if (isDelayed) {
      if (currentTime >= delayEndTime) {
        isDelayed = false;
        digitalWrite(pin_LED, HIGH);
        digitalWrite(pin_indicator, HIGH);
        Serial.print("Light ON\n");
      }
    }
    else if (currentTime >= operationEndTime) {
      digitalWrite(pin_LED, LOW);
      digitalWrite(pin_indicator, LOW);
      Serial.print("Light OFF\n");
      currentOperation = "none";
    }
  }
  else if (currentOperation == "p") {
    if (currentTime >= operationEndTime) {
      digitalWrite(pin_LED, LOW);
      digitalWrite(pin_indicator, LOW);
      Serial.print("Pulsing OFF\n");
      currentOperation = "none";
    }
    else {
      //* Update pulse timing
      if (t_period < period) { //* In the current period
        t_period = currentTime - t0_period;
      }
      else { //* Start next period
        ResetPulse();
      }
      
      if (fpul) { //* Pulse is on
        if (t_pulse < pulse_width) {
          t_pulse = currentTime - t0_period;
        }
        else { //* Shut off the pulse and enter the pulse-off phase of the current period
          digitalWrite(pin_LED, LOW);
          digitalWrite(pin_indicator, LOW);
          fpul = false;
          t_pulse = 0;
        }
      }
    }
  }
  
  //* Handle shock pulses - can run in parallel with other operations
  if (shockState) {
    if (!shockPulseOn && (currentTime - lastShockTime >= shockPeriod)) {
      //* Time to start a new shock pulse
      digitalWrite(pin_shock, HIGH);
      shockPulseOn = true;
      shockPulseStart = currentTime;
      lastShockTime = currentTime;
    }
    else if (shockPulseOn && (currentTime - shockPulseStart >= shockPulseWidth)) {
      //* Time to end the current shock pulse
      digitalWrite(pin_shock, LOW);
      shockPulseOn = false;
    }
  }
}
