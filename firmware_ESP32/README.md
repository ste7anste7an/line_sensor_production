# Testfirmware for LMS-ESP32

This is the firmware that performs thests with two connected Line Sensor boards. 
The folowing tests are performed:

0 - Scanning the Neopixel LEDs in colors Red, Green and Blue
1 - Scan the I2C bus for the two Line Sensor boards at address 0x33 and 0x34
2 - Measure the RX and TX pins of the 2x3 connector using GPIO signals
3 - Do a measurement of the IR sensors and IR emitters of the Device Under Test.


The progress of tests 1, 2 and 3 is mindicated by LEDS S1, S2, and S3. When the tests passes, the LEDS become green. On failure they will turn RED.

## Serial output
The test report is sent live over the LMS-ESP32 USB serial console. Connect a
serial terminal at 115200 baud to follow the progress and final `PASS` or
`FAIL` result.

As a best-effort backup, the report is also appended to `test_log.txt` in the
ESP32 filesystem. A filesystem error does not stop the test or its live serial
report. On
startup the ESP32 sends `LMS_LOG_READY` over its USB serial connection and
waits three seconds for `DOWNLOAD_LOG`. When that command is received, it
sends the existing log instead of starting a new hardware test. If no command
arrives, the production test starts normally and its output is added to the
file.

Open `web/index.html` from an HTTPS server or localhost in Chrome or Edge to
download the log. The first connection needs a click on **Connect ESP32** to
grant serial-port permission; the page never opens a serial port automatically.
Use **Disconnect** to close the port. If the ESP32 has already passed its
three-second window, reset it while the page is connected and waiting.

After receiving a log, the page holds it in memory and enables **Save last log
as...**; it does not save anything automatically. The button opens a file
picker in supported browsers. If the file-picker API is unavailable, it saves
through the browser's normal download mechanism.

Use **Delete ESP log** to remove `test_log.txt` from the ESP32. The page asks
for confirmation before sending `DELETE_LOG` and reports whether the device
returned `LMS_LOG_DELETED` or `LMS_LOG_DELETE_ERROR`. After the browser has
selected log-service mode, reset the ESP32 to run another production test.

For example, serve the frontend from the repository root with:

```powershell
python -m http.server 8000 --directory firmware_ESP32/web
```

Then open `http://localhost:8000`.

## Test report
Below is the output of a succesful test

```
=======================================================

[*] Test procedure started

[.] check i2c devices
[*] devices found:  [51, 52]
[*] I2C connections OK


[*] line Sensor UID:  CD:AB:35:D4:24:BD:26:3D
[*] line Sensor UID:  CD:AB:31:D4:24:BD:22:3D



[.] Testing GPIO pins
[*] Expected result per pin: (0, 1)
[*] O = OK, L = LOW failed, H = HIGH failed, LH = both failed

+-------------+
|   PIN Rx    |
|     OK      |
|   (0, 1)    |
+-------------+
       ||
+-------------+
|   PIN Tx    |
|     OK      |
|   (0, 1)    |
+-------------+

[+] GPIO test OK



[.] Measuring DUT with IR emitter TU off
[*] values DUT:  [225, 241, 238, 238, 237, 245, 241, 250]
[.] Measuring DUT with IR emitter TU on
[*] values DUT:  [8, 8, 8, 9, 8, 8, 7, 7]
[.] Measuring TU with IR emitter DUT off
[*] values TU:   [228, 226, 218, 231, 233, 225, 235, 250]
[.] Measuring TU with IR emitter DUT on
[*] values TU:   [8, 10, 8, 8, 7, 8, 8, 7]


[*] DUT optical test
[*] O = OK, * = FAIL
[*] pass condition: OFF > 215, ON < 40
      +---+---+---+---+---+---+---+---+
EMIT  | O | O | O | O | O | O | O | O |
      +---+---+---+---+---+---+---+---+
RECV  | O | O | O | O | O | O | O | O |
      +---+---+---+---+---+---+---+---+
        S1  S2  S3  S4  S5  S6  S7  S8 

=======================================================
```
