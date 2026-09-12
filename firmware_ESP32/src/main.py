from time import sleep, ticks_ms, ticks_diff, sleep_ms
from line_sensor import LineSensorI2C
import lms_esp32
import os
import sys
import uselect
from machine import I2C, Pin, UART
from neopixel import NeoPixel

# test program for firmware 5.6

LOG_FILENAME = "test_log.txt"
LOG_READY = "LMS_LOG_READY"
LOG_REQUEST = "DOWNLOAD_LOG"
LOG_DELETE_REQUEST = "DELETE_LOG"
LOG_BEGIN = "LMS_LOG_BEGIN"
LOG_END = "LMS_LOG_END"
LOG_DELETED = "LMS_LOG_DELETED"
LOG_DELETE_ERROR = "LMS_LOG_DELETE_ERROR"
LOG_REQUEST_TIMEOUT_MS = 1000


def wait_for_log_command(timeout_ms=None, announce=False):
    """Wait for a download or delete command from the USB serial console."""
    poller = uselect.poll()
    poller.register(sys.stdin, uselect.POLLIN)
    command = ""
    start = ticks_ms()
    last_ready = start

    if announce:
        print(LOG_READY)

    while timeout_ms is None or ticks_diff(ticks_ms(), start) < timeout_ms:
        now = ticks_ms()
        if announce and ticks_diff(now, last_ready) >= 500:
            print(LOG_READY)
            last_ready = now

        if not poller.poll(50):
            continue

        character = sys.stdin.read(1)
        if character == "\r" or character == "\n":
            if command == LOG_REQUEST or command == LOG_DELETE_REQUEST:
                return command
            command = ""
        elif character:
            command = (command + character)[-64:]

    return None


def send_log():
    """Send the complete text log using line-based serial framing."""
    print(LOG_BEGIN)
    needs_newline = False
    try:
        log_file = open(LOG_FILENAME, "r")
    except OSError:
        log_file = None

    if log_file is not None:
        try:
            while True:
                chunk = log_file.read(128)
                if not chunk:
                    break
                sys.stdout.write(chunk)
                needs_newline = chunk[-1] != "\n"
        finally:
            log_file.close()

    if needs_newline:
        print("")
    print(LOG_END)


def delete_log():
    """Delete the stored test log and report the result over USB serial."""
    try:
        os.remove(LOG_FILENAME)
    except OSError as error:
        print(LOG_DELETE_ERROR, error)
        return False

    print(LOG_DELETED)
    return True


def service_log_requests():
    """Enter log-service mode when the browser responds during startup."""
    command = wait_for_log_command(LOG_REQUEST_TIMEOUT_MS, announce=True)
    if command is None:
        return False

    while True:
        if command == LOG_REQUEST:
            send_log()
        elif command == LOG_DELETE_REQUEST:
            delete_log()
        command = wait_for_log_command()


class TestLogger:
    """Report over USB UART and keep a best-effort backup on flash."""

    def __init__(self, filename):
        try:
            self.file = open(filename, "a")
        except OSError as error:
            self.file = None
            print("[!] Test log backup unavailable:", error)

    def print(self, *values):
        line = " ".join(str(value) for value in values)

        # stdout is the USB serial console and is the primary test report.
        print(line)

        if self.file is not None:
            try:
                self.file.write(line + "\n")
                self.file.flush()
            except OSError as error:
                failed_file = self.file
                self.file = None
                try:
                    failed_file.close()
                except OSError:
                    pass
                print("[!] Test log backup failed:", error)

class ProductionTest:
    DUT_ADDRESS = 0x33
    TU_ADDRESS = 0x34
    dut = None
    tu = None

    def __init__(self):
        self.logger = TestLogger(LOG_FILENAME)
        self.np = NeoPixel(Pin(25), 1)
        self.uart = UART(
            1,
            rx=lms_esp32.RX_PIN,
            tx=lms_esp32.TX_PIN,
            baudrate=115200,
        )
        self.i2c = I2C(1, scl=Pin(4), sda=Pin(5), freq=100000)

    def report(self, *values):
        self.logger.print(*values)

    def check_i2c(self):
        devices = self.i2c.scan()
        self.report("[.] check i2c devices")
        self.report("[*] devices found: ", devices)
        ok = True
        if self.DUT_ADDRESS not in devices:
            self.report("[!] Check I2C connection of DUT")
            ok = False
        if self.TU_ADDRESS not in devices:
            self.report("[!] Check I2C connection of TU")
            ok = False
        return ok

    def initialize_devices(self):
        self.dut = LineSensorI2C(device_addr=self.DUT_ADDRESS, freq=100000)
        self.tu = LineSensorI2C(device_addr=self.TU_ADDRESS, freq=100000)

N_MEASURE = 10
"""
[*] info
[+] ok
[-] no / removed / skipped
[!] warning
[x] error
[?] question
[>] action
[.] progress
"""

def get_uid():
    uid = test.dut.uid_hex()
    test.report("[*] line Sensor (DUT) UID: ", uid)
    uid = test.tu.uid_hex()
    test.report("[*] line Sensor (TU)  UID: ", uid)
    
def uart_test():
    return test.dut.uart_test()==1

def neopixel_test():
    test.dut.led_mode(test.dut.LEDS_OFF)
    for i in range(9):
        test.dut.neopixel(i,30,0,0)
        sleep_ms(50)
    sleep_ms(200)
    for i in range(9):
        test.dut.neopixel(i,0,30,0)
        sleep_ms(50)
    sleep_ms(200)
    for i in range(9):
        test.dut.neopixel(i,0,0,30)
        sleep_ms(50)
    sleep_ms(200)
    for i in range(9):
        test.dut.neopixel(i,0,0,0)
        sleep_ms(30)
    #dut.led_mode(dut.LEDS_VALUES)




    
def _gpio_mark(result):
    """
    result should be (low_read, high_read)

    Expected:
        low_read  == 0
        high_read == 1

    Returns:
        O  = OK
        L  = error when LOW was expected
        H  = error when HIGH was expected
        LH = both LOW and HIGH failed
    """
    low_read, high_read = result

    mark = ""

    if low_read != 0:
        mark += "Lo"

    if high_read != 1:
        mark += "Hi"

    if mark == "":
        mark = "OK"

    return mark


def _center(text, width):
    text = str(text)
    if len(text) >= width:
        return text[:width]

    left = (width - len(text)) // 2
    right = width - len(text) - left
    return " " * left + text + " " * right


def _print_pin_box(pin, mark, result):
    width = 13

    test.report("+" + "-" * width + "+")
    test.report("|" + _center("PIN {}".format(pin), width) + "|")
    test.report("|" + _center(mark, width) + "|")
    test.report("|" + _center(str(result), width) + "|")
    test.report("+" + "-" * width + "+")


def test_uart_report():
    """
    Tests uart pins

    test_uart() command sends a short uremote frame from TX.
    using a connection cable, the received frame is checked on RX:
        True: when succesfull
    """

    test.report("[.] Testing UART")

    uart_result = uart_test()

    test.report("[?] Expected result: True")
    
    test.report("[.] UART test", uart_result == 1)

    if uart_result == 1 :
        test.report("[+] UART test OK")
        return True
    else:
        test.report("[x] UART test failed")
        return False


def vector_add(a, b):
    l=len(a)
    s=[0]*l
    for i in range(l):
        s[i] = a[i] + b[i]
    return s

def vector_div(a, d):
    l=len(a)
    s=[0]*l
    for i in range(l):
        s[i] = a[i]//d
    return s
    

def measure_avg(dev, nr):
    avg = [0]*8
    cnt = 0
    for i in range(nr):
        try:
            val = dev.sensors()
            #print(val)
        except e:
            continue
        cnt += 1
        avg = vector_add(avg, val)
        sleep_ms(20)
    return vector_div(avg, cnt)
    

PASS_LIMIT = 60


def _status_marks(values, limit=PASS_LIMIT):
    # O = OK/pass, * = fail
    return ["O" if v < limit else "*" for v in values]


PASS_LIMIT = 40


def _pass_off_on(off_value, on_value, limit=PASS_LIMIT):
    """
    Sensor is OK if:
    - without opposite emitter: value is high
    - with opposite emitter: value is low
    """
    return off_value > (255 - limit) and on_value < limit


def print_dut_ascii(
    dut_rx_with_tu_off,
    dut_rx_with_tu_on,
    tu_rx_with_dut_off,
    tu_rx_with_dut_on,
    limit=PASS_LIMIT,
    reverse_tu=False,
):
    """
    Print DUT status as ASCII-art boxes.

    Upper row = DUT emitters.
        O if TU reads high when DUT emitter is OFF
        and TU reads low when DUT emitter is ON.

    Lower row = DUT receivers.
        O if DUT reads high when TU emitter is OFF
        and DUT reads low when TU emitter is ON.

    O = OK
    * = FAIL
    """

    if reverse_tu:
        tu_rx_with_dut_off = list(reversed(tu_rx_with_dut_off))
        tu_rx_with_dut_on = list(reversed(tu_rx_with_dut_on))

    dut_emitter_marks = []
    dut_receiver_marks = []

    for i in range(8):
        emitter_ok = _pass_off_on(
            tu_rx_with_dut_off[i],
            tu_rx_with_dut_on[i],
            limit,
        )

        receiver_ok = _pass_off_on(
            dut_rx_with_tu_off[i],
            dut_rx_with_tu_on[i],
            limit,
        )

        dut_emitter_marks.append("O" if emitter_ok else "*")
        dut_receiver_marks.append("O" if receiver_ok else "*")

    border = "      +" + "---+" * 8

    emitter_row = "EMIT  "
    receiver_row = "RECV  "
    index_row = "       "

    for i in range(8):
        emitter_row += "| {} ".format(dut_emitter_marks[i])
        receiver_row += "| {} ".format(dut_receiver_marks[i])
        index_row += " S{} ".format(i+1)

    emitter_row += "|"
    receiver_row += "|"

    test.report("\r\n\r\n[*] DUT optical test")
    test.report("[*] O = OK, * = FAIL")
    test.report("[*] pass condition: OFF > {}, ON < {}".format(255 - limit, limit))
    test.report(border)
    test.report(emitter_row)
    test.report(border)
    test.report(receiver_row)
    test.report(border)
    test.report(index_row)
    if '*' in dut_emitter_marks or '*' in dut_receiver_marks:
        return False
    else:
        return True

# Check IR sensors
# tu IR off
def test_sensors():
    test.dut.ir_power(False)
    test.tu.ir_power(False)
    sleep_ms(50)

    #dut.led_mode(dut.LEDS_VALUES)
    #tu.led_mode(tu.LEDS_VALUES)

    test.report("[.] Measuring DUT with IR emitter TU off")
    dut_with_tu_off = measure_avg(test.dut, N_MEASURE)
    test.report("[*] values DUT: ", dut_with_tu_off)

    test.tu.ir_power(True)
    sleep_ms(100)

    test.report("[.] Measuring DUT with IR emitter TU on")
    dut_with_tu_on = measure_avg(test.dut, N_MEASURE)
    test.report("[*] values DUT: ", dut_with_tu_on)

    test.dut.ir_power(False)
    test.tu.ir_power(False)
    sleep_ms(100)

    test.report("[.] Measuring TU with IR emitter DUT off")
    tu_with_dut_off = measure_avg(test.tu, N_MEASURE)
    test.report("[*] values TU:  ", tu_with_dut_off)

    test.dut.ir_power(True)
    sleep_ms(100)

    test.report("[.] Measuring TU with IR emitter DUT on")
    tu_with_dut_on = measure_avg(test.tu, N_MEASURE)
    test.report("[*] values TU:  ", tu_with_dut_on)

    test.dut.ir_power(False)
    test.tu.ir_power(False)

    OK = print_dut_ascii(
        dut_rx_with_tu_off=dut_with_tu_off,
        dut_rx_with_tu_on=dut_with_tu_on,
        tu_rx_with_dut_off=tu_with_dut_off,
        tu_rx_with_dut_on=tu_with_dut_on,
        limit=PASS_LIMIT,
        reverse_tu=False,
    )
    return OK

def run_production_test():
    global test

    test = ProductionTest()
    ok = True
    all_ok = True
    test.np[0] = (0, 0, 0)
    test.np.write()
    test.report("\r\n=======================================================")
    test.report("[*] Test procedure started\r\n")
    sleep_ms(100)

    if test.check_i2c():
        test.initialize_devices()
        test.tu.led_mode(test.tu.LEDS_OFF)
        neopixel_test()
        test.report("[*] I2C connections OK\r\n\r\n")
        get_uid()
        test.dut.neopixel(0, 0, 40, 0)
        test.report("\r\n")
        ok = test_uart_report()
        all_ok = all_ok & ok
        if ok:
            test.dut.neopixel(1, 0, 40, 0)
        else:
            test.dut.neopixel(1, 40, 0, 0)
        test.report("\r\n")
        ok = test_sensors()
        all_ok = all_ok & ok
        # dut.led_mode(dut.LEDS_OFF)
        if ok:
            test.dut.neopixel(2, 0, 40, 0)
        else:
            test.dut.neopixel(2, 40, 0, 0)
        if all_ok:
            test.report("[+] Test result: PASS")
            test.np[0] = (0, 50, 0)
            test.np.write()
        else:
            test.report("[x] Test result: FAIL")
            test.np[0] = (50, 0, 0)
            test.np.write()
        test.report("\r\n=======================================================\r\n")
    else:
        test.report("[!] Test aborted")
        test.report("[x] Test result: FAIL")
        while True:
            test.np[0] = (50, 0, 0)
            test.np.write()
            sleep_ms(300)
            test.np[0] = (0, 0, 0)
            test.np.write()
            sleep_ms(300)


if not service_log_requests():
    run_production_test()
