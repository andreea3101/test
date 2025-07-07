"""Serial output handler for NMEA sentences."""

from dataclasses import dataclass

@dataclass
class SerialOutputConfig:
    """Configuration for serial output."""

    port: str = "/dev/ttyS0"  # Default serial port
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = 'N'
    stopbits: int = 1
    timeout: float = 1.0  # seconds
    write_timeout: float = 1.0 # seconds

import serial
from .base import OutputHandler
from typing import Optional

class SerialOutput(OutputHandler):
    """Serial output handler for NMEA sentences."""

    def __init__(self, config: SerialOutputConfig):
        """Initialize Serial output handler."""
        super().__init__()
        self.config = config
        self.serial_port: Optional[serial.Serial] = None

    def start(self) -> None:
        """Start serial output."""
        if self.is_running:
            return

        try:
            self.serial_port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
                write_timeout=self.config.write_timeout
            )
            self.is_running = True
            print(f"Serial output started on {self.config.port} at {self.config.baudrate} baud")

        except serial.SerialException as e:
            self.is_running = False
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            raise RuntimeError(f"Failed to start serial output on {self.config.port}: {e}")

    def stop(self) -> None:
        """Stop serial output."""
        if not self.is_running:
            return

        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        print("Serial output stopped")

    def send_sentence(self, sentence: str) -> bool:
        """Send NMEA sentence via serial port."""
        if not self.is_running or not self.serial_port or not self.serial_port.is_open:
            return False

        try:
            # NMEA sentences should end with \r\n
            if not sentence.endswith('\r\n'):
                sentence += '\r\n'
            self.serial_port.write(sentence.encode('utf-8'))
            self.sentences_sent += 1
            return True
        except serial.SerialTimeoutException:
            print(f"Serial write timeout on {self.config.port}")
            return False
        except serial.SerialException as e:
            print(f"Serial write error on {self.config.port}: {e}")
            # Consider closing the port or attempting to reopen if specific errors occur
            return False
        except Exception as e:
            print(f"Unexpected error during serial send: {e}")
            return False

    def get_status(self) -> dict:
        """Get serial output status."""
        status = super().get_status()
        status.update({
            'port': self.config.port,
            'baudrate': self.config.baudrate,
            'is_open': self.serial_port.is_open if self.serial_port else False
        })
        return status

    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.is_running else "STOPPED"
        return f"SerialOutput({status}, {self.config.port}, {self.config.baudrate} baud, {self.sentences_sent} sentences)"
