import os
import re
import time

from carbontracker.components.handler import Handler

# RAPL Literature: https://www.researchgate.net/publication/322308215_RAPL_in_Action_Experiences_in_Using_RAPL_for_Power_Measurements

RAPL_DIR = "/sys/class/powercap/"
CPU = 0
DRAM = 2
MEASURE_DELAY = 1

class IntelCPU(Handler):
    def devices(self):
        """Returns the name of all RAPL Domains"""
        return self._devices

    def available(self):
        return os.path.exists(RAPL_DIR) and bool(os.listdir(RAPL_DIR))
    
    def power_usage(self):
        before_measures = self._get_measurements()
        time.sleep(MEASURE_DELAY)
        after_measures = self._get_measurements()

        return [self._compute_power(before, after) for before, after in zip(before_measures, after_measures)]
    
    def _compute_power(self, before, after):
        """Compute avg. power usage from two samples in microjoules."""
        joules = (after - before) / 1000000
        watt = joules / MEASURE_DELAY
        return watt

    def _read_energy(self, path):
        with open(os.path.join(path, "energy_uj"), 'r') as f:
            return int(f.read())
    
    def _get_measurements(self):
        measurements = []
        for package in self._devices:
            try:
                power_usage = self._read_energy(os.path.join(RAPL_DIR, package))
                measurements.append(power_usage)
            except FileNotFoundError:
                # check cpu/gpu/dram
                parts = [f for f in os.listdir(os.path.join(RAPL_DIR, package)) if re.match(self.parts_pattern, f)]
                total_power_usage = 0
                for part in parts:
                    total_power_usage += self._read_energy(os.path.join(RAPL_DIR, package, part))
                
                measurements.append(total_power_usage)

        return measurements

    def init(self):
        # get amount of intel-rapl folders
        packages = list(filter(lambda x: ':' in x, os.listdir(RAPL_DIR)))
        self.device_count = len(packages)
        self._devices = []
        self.parts_pattern = re.compile("intel-rapl:(\d):(\d)")
        devices_pattern = re.compile("intel-rapl:.")

        for package in packages:
            if re.fullmatch(devices_pattern, package):
                with open(os.path.join(RAPL_DIR, package, "name"), "r") as f:
                    name = f.read().strip()
                if name != "psys":
                    self._devices.append(package)

    def shutdown(self):
        pass