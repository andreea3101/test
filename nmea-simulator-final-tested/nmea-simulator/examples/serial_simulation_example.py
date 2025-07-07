"""
NMEA Simulator - Serial Output Example

This script demonstrates how to configure and use the SerialOutput handler
to send NMEA sentences to a serial port.
"""

import time
import sys
import os

# Adjust path to import from parent directory (if running script directly from examples)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulator.outputs.serial import SerialOutput, SerialOutputConfig
from simulator.outputs.factory import OutputFactory # For potential use with full config parsing
from simulator.config.parser import OutputConfig as GlobalOutputConfig # For potential use with full config parsing

def run_serial_example():
    """
    Runs a simple demonstration of the SerialOutput handler.
    """
    print("NMEA Simulator - Serial Output Example")
    print("------------------------------------")

    # --- Configuration for Serial Output ---
    # Option 1: Direct instantiation of SerialOutputConfig
    # Replace 'YOUR_SERIAL_PORT_HERE' with your actual or virtual serial port.
    # Common examples:
    # - Linux: /dev/ttyS0, /dev/ttyUSB0, /dev/ttyACM0
    # - macOS: /dev/cu.usbmodemXXXX or /dev/cu.usbserial-XXXX
    # - Windows: COM1, COM3, etc.
    # For testing without physical hardware, you can use a virtual serial port pair.
    # Software like 'socat' (Linux/macOS) or 'com0com' (Windows) can create these.
    # If pyserial's 'loop://' works in your environment, you could also try that for simple tests.

    serial_port_name = "/dev/ttyS0"  # <<<< IMPORTANT: CHANGE THIS TO YOUR SERIAL PORT
    # On Windows, it might be "COM1", "COM2", etc.
    if os.name == 'nt': # Basic check for Windows
        serial_port_name = "COM1"

    print(f"Attempting to use serial port: {serial_port_name}")
    print("Please ensure this port exists and is configured correctly.")
    print("You might need to create a virtual serial port pair for this example to run without hardware.")
    print("For instance, using socat on Linux/macOS: ")
    print("  socat -d -d pty,raw,echo=0 pty,raw,echo=0")
    print("This will output two pseudo-terminal names (e.g., /dev/pts/X and /dev/pts/Y). Use one for this script")
    print("and the other to listen with a serial terminal (e.g., minicom, screen, PuTTY).")
    print("-" * 20)

    serial_config = SerialOutputConfig(
        port=serial_port_name,
        baudrate=4800,  # Common NMEA baud rate, but can be 9600 or higher
        timeout=1.0,
        write_timeout=1.0
    )

    # --- Create SerialOutput Handler ---
    try:
        serial_output_handler = SerialOutput(serial_config)
    except Exception as e:
        print(f"Error creating SerialOutput handler: {e}")
        print("Please check your serial port configuration and ensure pyserial is installed.")
        return

    # --- Start and Use the Handler ---
    try:
        with serial_output_handler: # Using context manager for automatic start/stop
            print(f"Serial output handler started on {serial_config.port} at {serial_config.baudrate} baud.")

            # Sample NMEA sentences
            nmea_sentences = [
                "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
                "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
                "$GPVTG,054.7,T,,M,005.5,N,010.2,K*48",
            ]

            for i in range(5): # Send a few batches of sentences
                print(f"\nSending batch {i+1}...")
                for sentence in nmea_sentences:
                    # Slightly modify sentence to see changes if looping
                    timestamp = time.strftime("%H%M%S", time.gmtime())
                    modified_sentence = sentence.replace("123519", timestamp)

                    # Recalculate checksum (simple placeholder, real NMEA lib would do this)
                    # For this example, we'll send with potentially incorrect checksum if time changes
                    # or use a fixed one. The important part is the sending.
                    # A real sentence generator would handle checksums.
                    # Let's assume sentences are pre-checksummed for this basic example.

                    print(f"  Sending: {modified_sentence}")
                    if serial_output_handler.send_sentence(modified_sentence):
                        print(f"    -> Sent successfully.")
                    else:
                        print(f"    -> Failed to send.")
                    time.sleep(0.5) # Pause between sentences

                if i < 4: # Don't sleep after the last batch
                    print("Waiting 2 seconds before next batch...")
                    time.sleep(2)

            print("\nFinished sending sentences.")
            status = serial_output_handler.get_status()
            print(f"Final status: Sent {status['sentences_sent']} sentences.")

    except RuntimeError as e:
        print(f"RuntimeError during serial communication: {e}")
        print("This often means the serial port could not be opened or there was a write error.")
        print(f"Please check that '{serial_config.port}' is available and not in use by another application.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("\nSerial output example finished.")

    # --- Alternative: Using OutputFactory (more aligned with main simulator) ---
    # This shows how it might be integrated if you were parsing a full config file.
    # For this example, direct instantiation above is simpler.
    #
    # print("\n--- Example using OutputFactory (conceptual) ---")
    # # This OutputConfig is from simulator.config.parser
    # # It's a generic wrapper around specific configs like SerialOutputConfig
    # global_output_conf = GlobalOutputConfig(
    #     type="serial",
    #     enabled=True,
    #     config=serial_config # Here, config is the SerialOutputConfig instance
    # )
    #
    # try:
    #     factory_handler = OutputFactory.create_output_handler(global_output_conf)
    #     with factory_handler:
    #         print(f"Factory handler started for type '{global_output_conf.type}'")
    #         factory_handler.send_sentence("$GPXXX,from_factory,1,2,3*CS")
    #         print("Sentence sent via factory-created handler.")
    # except ValueError as e:
    #     print(f"Error creating handler via factory: {e}")
    # except RuntimeError as e:
    #     print(f"RuntimeError with factory handler: {e}")


if __name__ == "__main__":
    run_serial_example()
