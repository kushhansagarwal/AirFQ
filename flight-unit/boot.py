import machine
from time import sleep_ms

led = machine.Pin("LED", machine.Pin.OUT)
for _ in range(10):
    led.on()
    sleep_ms(50)
    led.off()
    sleep_ms(50)
