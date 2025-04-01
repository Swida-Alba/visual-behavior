/*  

communication with python running in a PC
receiving command from PC to switch ON/OFF the LED or deliver pulses

Note: for the "pulse" ("p") mode, pulse on is set at the start of the period.
 */

int pin = 10; // the pin to control relay
int indicator_pin = 9; // indicator for LED, coordiated with "pin"
const long baudRate = 9600;
String light_switch; // read command from serial

// parameters for pulsing at given frequency and duty cycle
double frequency   = 0, // pulsing frequency in 'p' mode
       duty_cycle  = 0, // not currently used, replaced by pulse_width
       period      = 0; // pulsing period in 'p' mode, calculated from frequency
long   pulse_width = 0; // specified pulse width
unsigned long t_period  = 0, // elapsed time of the current period
              t0_period = 0, // start time of a period
              t_pulse   = 0; // elapsed time of the current pulse
boolean fpul = false; // true: is in peak (pulse-on) phase; false: is in trough (pulse-off) phase
long t_span = 0, // time of pulse span, in ms
     t_delay = 0; // 
int d_pos = 0,
    f_pos = 0,
    w_pos = 0,
    len   = 0;

void ResetPulse()
{
  digitalWrite(pin, HIGH);
  fpul = true;
  t_period    = 0;
  t0_period = millis();
  t_pulse   = 0;
}

void setup()
{
  Serial.begin(baudRate);
  pinMode(pin,OUTPUT);
  pinMode(indicator_pin,OUTPUT);
  for (int i = 0; i < 4; i++) // write pins 0-3 to constant HIGH
  {
    pinMode(i,OUTPUT);
    digitalWrite(i,HIGH);
  }
}

void loop()
{
  if (Serial.available() > 0) 
  {
    light_switch = Serial.readStringUntil('\n'); // read command from the connected PC
   
    if (light_switch == "on") 
    { // turn on the LED
      digitalWrite(pin,HIGH);
      digitalWrite(indicator_pin,HIGH);
      Serial.print("Light ON\n");
    }
    
    else if (light_switch == "off")
    { // turn off the LED
      digitalWrite(pin,LOW);
      digitalWrite(indicator_pin,LOW);
      Serial.print("Light OFF\n");
    }
    
    else if (light_switch.charAt(0) == 'r') // 'r' mode, constant LED
    { // "r" mode, timer for constant LED ON
      d_pos = light_switch.indexOf('d'); // delay time after 'd'
      len = light_switch.length();
      if (d_pos > -1)
      { // if the turn-on command will be delayed for given time
        String span_str = "", d_str = "";
        for (int i=1; i<d_pos; i++) span_str += String(light_switch[i]);
        for (int i=d_pos+1; i<len; i++) d_str += String(light_switch[i]);
        t_delay = d_str.toInt();
        t_span = span_str.toInt();
        unsigned long t_start = millis();
        unsigned long t_elapsed = 0;
        while (t_elapsed < t_delay)
        {
          t_elapsed = millis() - t_start;
        }
      }
      else
      {
        light_switch.remove(0,1);
        t_span = light_switch.toInt();
      }
      
      digitalWrite(pin,HIGH);
      digitalWrite(indicator_pin,HIGH);
      Serial.print("Light ON\n");
      unsigned long t_start = millis();
      unsigned long t_elapsed = 0;
      while (t_elapsed < t_span)
      {
        t_elapsed = millis() - t_start;
      }
      digitalWrite(pin,LOW);
      digitalWrite(indicator_pin,LOW);
      Serial.print("Light OFF\n");
    }
    
    else if (light_switch.charAt(0) == 'p') 
    { // 'p' mode, pulsing LED, required input as 'pXXXfXXXwXXX' where XXXs are integers in ms or Hz, 
      // e.g. "p5000f5w100" represents a 5 s pulsing series with frequency = 5 Hz, pulse_width = 100 ms
      
      // split span time, frequency, pulse width from the command string
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

      // start pulse series
      unsigned long t_start = millis();
      Serial.print("Pulsing ON\n");
      digitalWrite(indicator_pin,HIGH);
      ResetPulse(); // start the first pulse.
      // pulsing
      while (millis() - t_start < t_span)
      {
        if (t_period < period) // in the current period
          t_period = millis() - t0_period;
        else // start next period
        {
          ResetPulse();
        }
        if (fpul) // pulse is on
        {
          if (t_pulse < pulse_width) 
          {
            t_pulse = millis() - t0_period;
          }
          else // shut off the pulse and enter the pulse-off phase of the current period
          {
            digitalWrite(pin, LOW);
            fpul = false;
            t_pulse  = 0;
          }
        }
      } // end pulsing
      digitalWrite(pin, LOW);
      digitalWrite(indicator_pin,LOW);
      Serial.print("Pulsing OFF\n");
    }
    
    else
    {
      digitalWrite(13,HIGH); // if received unknown command, turn on the pin13 indicator
      Serial.print("Invalid Request\n");
    }
  }
}
