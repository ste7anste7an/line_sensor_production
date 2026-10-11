# Firmware for Line Sensor Modules

## DUT (Device under test)

This is the production firmware to be flashed on every new module using the WCHISPTool. This firmware listens to I2C address 0x33.



flash: 
```
CH32_DUT_line_sensor_v5_7.bin
```



## TU (Test unit)

This is the firmware to be flashed on the Test Unit (TU) using the WCHISPTool. It is identical to the firmware for the DUT, but only listens to address 0x34 on I2C.
flash:

```
CH32_TU_line_sensor_0x34_v5_7.bin
```

