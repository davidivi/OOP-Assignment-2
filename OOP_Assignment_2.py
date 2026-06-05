from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass(frozen=True)
class SensorReading:
    temperature_c: float
    timestamp: datetime


class SmartDevice(ABC):
    def __init__(self, device_id: str, name: str, room: str) -> None:
        self._device_id = device_id
        self._name = name
        self._room = room
        self._is_on = False

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def room(self) -> str:
        return self._room

    @property
    def is_on(self) -> bool:
        return self._is_on

    def turn_on(self) -> None:
        self._is_on = True

    def turn_off(self) -> None:
        self._is_on = False

    @abstractmethod
    def status(self) -> str:
        pass # Return a human-readable status string.


class Light(SmartDevice):
    def status(self) -> str:
        state = "ON" if self.is_on else "OFF"
        return f"{self.name} ({self.room}) - Light: {state}"


class Fan(SmartDevice):
    def status(self) -> str:
        state = "ON" if self.is_on else "OFF"
        return f"{self.name} ({self.room}) - Fan: {state}"


class AirConditioner(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str, target_temp: int = 24) -> None:
        super().__init__(device_id, name, room)
        self._target_temp = target_temp

    @property
    def target_temp(self) -> int:
        return self._target_temp

    def set_temperature(self, temperature_c: int) -> None:
        if not 16 <= temperature_c <= 30:
            raise ValueError("Air conditioner temperature must be between 16°C and 30°C.")
        self._target_temp = temperature_c

    def status(self) -> str:
        state = "ON" if self.is_on else "OFF"
        return f"{self.name} ({self.room}) - AC: {state}, target={self.target_temp}°C"


class TemperatureSensor:
    def __init__(self, sensor_id: str, room: str, initial_temp: float = 25.0) -> None:
        self._sensor_id = sensor_id
        self._room = room
        self._latest_reading = SensorReading(initial_temp, datetime.now())

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    @property
    def room(self) -> str:
        return self._room

    def update_temperature(self, temperature_c: float) -> None:
        self._latest_reading = SensorReading(temperature_c, datetime.now())

    def current_temperature(self) -> float:
        return self._latest_reading.temperature_c

    def status(self) -> str:
        return f"TemperatureSensor ({self.room}) - current={self.current_temperature():.1f}°C"


class AutomationRule(ABC):
    @abstractmethod
    def apply(self, controller: "SmartHomeController") -> List[str]:
        """Apply the rule and return action logs."""


class ComfortTemperatureRule(AutomationRule):
    def __init__(self, hot_threshold: float = 28.0, cool_threshold: float = 22.0, target_temp: int = 24) -> None:
        self.hot_threshold = hot_threshold
        self.cool_threshold = cool_threshold
        self.target_temp = target_temp

    def apply(self, controller: "SmartHomeController") -> List[str]:
        logs: List[str] = []
        temperature = controller.current_temperature()
        ac = controller.get_device("ac_living")
        fan = controller.get_device("fan_living")

        if not isinstance(ac, AirConditioner) or not isinstance(fan, Fan):
            return ["Automation skipped: required AC or fan device is missing."]

        if temperature >= self.hot_threshold:
            ac.turn_on()
            ac.set_temperature(self.target_temp)
            fan.turn_on()
            logs.append(f"Auto control: {temperature:.1f}°C is hot, AC ON at {self.target_temp}°C and fan ON.")
        elif temperature <= self.cool_threshold:
            ac.turn_off()
            fan.turn_off()
            logs.append(f"Auto control: {temperature:.1f}°C is cool, AC OFF and fan OFF.")
        else:
            ac.turn_off()
            fan.turn_on()
            logs.append(f"Auto control: {temperature:.1f}°C is comfortable, fan ON and AC OFF.")

        return logs


class SmartHomeController:
    def __init__(self) -> None:
        self._devices: Dict[str, SmartDevice] = {}
        self._temperature_sensor: TemperatureSensor | None = None
        self._automation_rules: List[AutomationRule] = []

    def add_device(self, device: SmartDevice) -> None:
        self._devices[device.device_id] = device

    def set_temperature_sensor(self, sensor: TemperatureSensor) -> None:
        self._temperature_sensor = sensor

    def add_automation_rule(self, rule: AutomationRule) -> None:
        self._automation_rules.append(rule)

    def get_device(self, device_id: str) -> SmartDevice:
        if device_id not in self._devices:
            raise KeyError(f"Unknown device id: {device_id}")
        return self._devices[device_id]

    def turn_on(self, device_id: str) -> None:
        self.get_device(device_id).turn_on()

    def turn_off(self, device_id: str) -> None:
        self.get_device(device_id).turn_off()

    def set_ac_temperature(self, device_id: str, temperature_c: int) -> None:
        device = self.get_device(device_id)
        if not isinstance(device, AirConditioner):
            raise TypeError(f"{device_id} is not an air conditioner.")
        device.set_temperature(temperature_c)

    def update_indoor_temperature(self, temperature_c: float) -> None:
        if self._temperature_sensor is None:
            raise RuntimeError("Temperature sensor is not configured.")
        self._temperature_sensor.update_temperature(temperature_c)

    def current_temperature(self) -> float:
        if self._temperature_sensor is None:
            raise RuntimeError("Temperature sensor is not configured.")
        return self._temperature_sensor.current_temperature()

    def run_automation(self) -> List[str]:
        logs: List[str] = []
        for rule in self._automation_rules:
            logs.extend(rule.apply(self))
        return logs

    def status_report(self) -> str:
        device_lines = [device.status() for device in self._devices.values()]
        sensor_line = self._temperature_sensor.status() if self._temperature_sensor else "No temperature sensor"
        return "\n".join([sensor_line, *device_lines])


def build_demo_home() -> SmartHomeController:
    controller = SmartHomeController()
    controller.add_device(Light("light_living", "Living Room Ceiling", "Living Room"))
    controller.add_device(AirConditioner("ac_living", "LG Dual Cool", "Living Room"))
    controller.add_device(Fan("fan_living", "Smart Circulator", "Living Room"))
    controller.set_temperature_sensor(TemperatureSensor("temp_living", "Living Room", initial_temp=25.0))
    controller.add_automation_rule(ComfortTemperatureRule())
    return controller


def run_demo() -> None:
    home = build_demo_home()

    print("=== Initial Device Status ===")
    print(home.status_report())

    print("\n=== Manual Control ===")
    home.turn_on("light_living")
    home.turn_on("ac_living")
    home.set_ac_temperature("ac_living", 23)
    print(home.status_report())

    print("\n=== Sensor Update: 30.5°C ===")
    home.update_indoor_temperature(30.5)
    for log in home.run_automation():
        print(log)
    print(home.status_report())

    print("\n=== Sensor Update: 21.0°C ===")
    home.update_indoor_temperature(21.0)
    for log in home.run_automation():
        print(log)
    print(home.status_report())


def baseline_status_report_without_polymorphism(devices: List[SmartDevice]) -> str:
    lines: List[str] = []
    for device in devices:
        state = "ON" if device.is_on else "OFF"
        if isinstance(device, Light):
            lines.append(f"{device.name} ({device.room}) - Light: {state}")
        elif isinstance(device, AirConditioner):
            lines.append(f"{device.name} ({device.room}) - AC: {state}, target={device.target_temp}°C")
        elif isinstance(device, Fan):
            lines.append(f"{device.name} ({device.room}) - Fan: {state}")
        else:
            lines.append(f"{device.name} ({device.room}) - Unknown device: {state}")
    return "\n".join(lines)


def run_polymorphism_experiment() -> None:
    home = build_demo_home()
    home.turn_on("light_living")
    home.turn_on("fan_living")

    devices = [
        home.get_device("light_living"),
        home.get_device("ac_living"),
        home.get_device("fan_living"),
    ]

    print("=== Comparative Experiment: Without Polymorphism ===")
    print(baseline_status_report_without_polymorphism(devices))
    print("Branch count needed in baseline: 3 concrete type checks")

    print("\n=== Comparative Experiment: With Polymorphism ===")
    print("\n".join(device.status() for device in devices))
    print("Branch count needed in controller/reporting logic: 0 concrete type checks")


if __name__ == "__main__":
    run_demo()
    print()
    run_polymorphism_experiment()
