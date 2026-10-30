"""Minimal BMP280 I2C driver returning pressure in hPa."""

import struct
import time


class BMP280:
    def __init__(self, i2c, address=0x76):
        self.i2c = i2c
        self.address = address
        chip_id = i2c.readfrom_mem(address, 0xD0, 1)[0]
        if chip_id != 0x58:
            raise OSError("Unexpected BMP280 chip ID 0x{:02x}".format(chip_id))
        calibration = i2c.readfrom_mem(address, 0x88, 24)
        values = struct.unpack("<HhhHhhhhhhhh", calibration)
        (self.t1, self.t2, self.t3, self.p1, self.p2, self.p3,
         self.p4, self.p5, self.p6, self.p7, self.p8, self.p9) = values
        # Temperature x2, pressure x16 oversampling, normal mode.
        i2c.writeto_mem(address, 0xF5, b"\x90")
        i2c.writeto_mem(address, 0xF4, b"\x57")
        time.sleep_ms(100)

    def read(self):
        """Return (temperature in C, pressure in hPa)."""
        data = self.i2c.readfrom_mem(self.address, 0xF7, 6)
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

        var1 = (((adc_t >> 3) - (self.t1 << 1)) * self.t2) >> 11
        var2 = (
            (((adc_t >> 4) - self.t1) * ((adc_t >> 4) - self.t1) >> 12)
            * self.t3
        ) >> 14
        t_fine = var1 + var2
        temperature = ((t_fine * 5 + 128) >> 8) / 100

        var1 = t_fine - 128000
        var2 = var1 * var1 * self.p6
        var2 += (var1 * self.p5) << 17
        var2 += self.p4 << 35
        var1 = ((var1 * var1 * self.p3) >> 8) + ((var1 * self.p2) << 12)
        var1 = (((1 << 47) + var1) * self.p1) >> 33
        if var1 == 0:
            raise OSError("BMP280 returned invalid calibration data")
        pressure = 1048576 - adc_p
        pressure = (((pressure << 31) - var2) * 3125) // var1
        var1 = (self.p9 * (pressure >> 13) * (pressure >> 13)) >> 25
        var2 = (self.p8 * pressure) >> 19
        pressure = ((pressure + var1 + var2) >> 8) + (self.p7 << 4)
        return temperature, pressure / 25600
