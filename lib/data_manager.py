# lib/data_manager.py

import os
import can # Assuming you have python-can installed for real CAN
from lib.can_interface import LiveTuningAccess, ECUException
from lib.mock_can_interface import MockLiveTuningAccess # For mock data source
from PyQt5.QtWidgets import QMessageBox

class DataManager:
    def __init__(self):
        self.active_communicator = None
        self._is_connected = False
        self.sram_dump_path = "ram/calram.bin" # Default path for mock or initial load

    # Modified connect_source method to accept ram_dump_path
    def connect_source(self, source_type, interface=None, channel=None, bitrate=None, ram_dump_path=None):
        self.disconnect_source() # Always disconnect existing before connecting new

        try:
            if source_type == "real_can":
                # Ensure LiveTuningAccess and can are imported and available
                from lib.can_interface import LiveTuningAccess
                self.active_communicator = LiveTuningAccess()
                self.active_communicator.open_can(interface, channel, bitrate)
                # Live CAN usually doesn't load a full dump, it reads as needed
                # But if you have an initial dump for setup, you might load it here too.
                # self.active_communicator.load_sram_content(self.sram_dump_path) # Example if real ECU has initial dump
                print(f"Data Manager: Connected to Real CAN: {interface}/{channel} @ {bitrate} bps")
                self._is_connected = True

            elif source_type == "mock_can":
                from lib.mock_can_interface import MockLiveTuningAccess
                self.active_communicator = MockLiveTuningAccess()
                # Use the provided ram_dump_path, or fall back to the default if not provided
                path_to_load = ram_dump_path if ram_dump_path else self.sram_dump_path
                self.active_communicator.load_sram_content(path_to_load) # Load mock RAM dump
                self.active_communicator.open_can("mock_interface", "mock_channel", 500000) # Open mock bus
                print(f"Data Manager: Connected to Mock CAN (loaded {path_to_load})")
                self._is_connected = True
            else:
                raise ValueError("Unknown source type")

        except Exception as e:
            print(f"Data Manager: Failed to connect to source: {e}")
            self._is_connected = False
            self.active_communicator = None # Ensure communicator is reset on failure
            QMessageBox.critical(None, "Connection Error", f"Failed to connect to data source: {e}")
            return False
        return True

    def read_data(self, address, length):
        if not self.active_communicator or not self._is_connected:
            print("Data Manager: Not connected to a source. Cannot read data.")
            return None
        try:
            return self.active_communicator.read_memory(address, length)
        except Exception as e:
            print(f"Data Manager: Error reading data from 0x{address:X} (length {length}): {e}")
            return None

    def write_data(self, address, data_bytes):
        if not self.active_communicator or not self._is_connected:
            print("Data Manager: Not connected to a source. Cannot write data.")
            return False
        try:
            self.active_communicator.write_memory(address, data_bytes)
            print(f"Data Manager: Wrote {len(data_bytes)} bytes to 0x{address:X}")
            return True
        except Exception as e:
            print(f"Data Manager: Error writing data to 0x{address:X}: {e}")
            return False

    def is_connected(self):
        return self._is_connected

    def shutdown(self):
        """Shuts down the active communicator when the application closes."""
        if self.active_communicator:
            try:
                self.active_communicator.shutdown()
                print("Data Manager: Communicator shut down.")
            except Exception as e:
                print(f"Error during communicator shutdown: {e}")
            finally:
                self.active_communicator = None
        self._is_connected = False # Ensure connection state is reset

    def disconnect_source(self):
        """Explicitly disconnects the current data source."""
        self.shutdown() # Re-use the shutdown logic for disconnecting