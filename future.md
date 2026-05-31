    2. Keep the UNO R3, add a WiFi/cellular companion module
    - ESP-01 (₹150) connected to UNO's TX/RX — UNO talks to ESP via AT commands, ESP handles WiFi. Cheap but fragile; AT-command protocol is a pain to debug.
    - SIM800L / SIM7600 GSM module (~₹600–1500) — gives the device its own cellular data, no WiFi needed. Best for real hospital deployment where WiFi isn't reliable.
    Needs a SIM card with data plan.
    
    3. Replace the whole compute with a Raspberry Pi Zero 2 W (~₹2000)
    - Pi runs your existing Python gateway script natively, has WiFi built-in, draws minimal power.
    - Not a true "no host" solution — the Pi is a tiny host — but it sits inside the patient device enclosure so externally it looks standalone.
    - Bonus: you can keep voice/TFT logic and add a camera, mic, or vitals sensors later.