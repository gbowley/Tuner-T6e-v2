# lib/mock_can_interface.py

# This facilitates mock access to ECU SRAM, allows development and testing of UI without connection to ECU.
# To mockup the UI on a specific car the user must download calram (ECU memory) using LotusECU-T4e

import random
import os

BO_BE = 'big'

class ECUException(Exception):
    pass

class MockLiveTuningAccess:
    def __init__(self):
        self.mock_memory = {}
        self.sym_map = None
        self.sram_content = bytearray()
        self.sram_base_addr = 0x40000000
        self.bus = None

    def set_sym_map(self, sym_map_obj):
        self.sym_map = sym_map_obj

    def load_sram_content(self, filepath): # Loads binary into mock SRAM
        if not os.path.exists(filepath):
            print(f"DEBUG MODE: SRAM file not found at {filepath}. Initializing with 2KB empty data.")
            self.sram_content = bytearray(2048)
            return

        try:
            with open(filepath, 'rb') as f:
                self.sram_content = bytearray(f.read())
            print(f"DEBUG MODE: Loaded {len(self.sram_content)} bytes of SRAM content from {filepath}.")
        except Exception as e:
            print(f"DEBUG MODE: Error loading SRAM content from {filepath}: {e}")
            self.sram_content = bytearray(2048)

    def open_can(self, interface, channel, bitrate):
        """Simulates opening a CAN device connection."""
        print(f"DEBUG MODE: Simulating CAN device connection (Interface: {interface}, Channel: {channel}, Bitrate: {bitrate})")
        self.bus = True # Set bus status to "open"

    def close_can(self):
        """Simulates CAN device disconnection."""
        print("DEBUG MODE: Simulating CAN device disconnection.")
        self.bus = None # Reset bus status to "closed"

    def read_memory(self, address, size):
        # Check for SRAM content first if loaded and valid
        if self.sram_content:
            sram_end_addr = self.sram_base_addr + len(self.sram_content)
            if address >= self.sram_base_addr and address < sram_end_addr:
                offset = address - self.sram_base_addr
                available_bytes = max(0, len(self.sram_content) - offset)
                bytes_to_read = min(size, available_bytes)

                if bytes_to_read > 0:
                    read_data = self.sram_content[offset : offset + bytes_to_read]
                    if len(read_data) < size:
                        read_data += bytearray(size - len(read_data))
                    return bytes(read_data)
                else:
                    return bytes([random.randint(0, 255) for _ in range(size)])

        cal_base_addr = None
        if self.sym_map:
            try:
                cal_base_addr = self.sym_map.get_sym_addr("cal_base")
            except KeyError:
                pass

        if cal_base_addr is not None and address == cal_base_addr and size == 4:
            return b"P138" # Simulate the correct ECU firmware ID

        # Simulate sensor readings with random but plausible values, not required when user calram.bin is present
        if self.sym_map:
            try:
                if address == self.sym_map.get_sym_addr("engine_speed"):
                    return int(random.uniform(700, 6000)).to_bytes(2, BO_BE) # Random RPM (e.g., 700-6000)
                if address == self.sym_map.get_sym_addr("engine_load"):
                    return int(random.uniform(100, 800)).to_bytes(2, BO_BE) # Random Load (e.g., 100-800)
                if address == self.sym_map.get_sym_addr("coolant"):
                    return int(max(0, min(255, random.uniform(80, 100) * 8 / 5 + 40 * 8 / 5))).to_bytes(1, BO_BE) 
                if address == self.sym_map.get_sym_addr("air"):
                    return int(max(0, min(255, random.uniform(20, 50) * 8 / 5 + 40 * 8 / 5))).to_bytes(1, BO_BE)
            except KeyError:
                pass

        return bytes([random.randint(0, 255) for _ in range(size)])

    def write_memory(self, address, data_bytes, verify=False):
        if self.sram_content:
            sram_end_addr = self.sram_base_addr + len(self.sram_content)
            if address >= self.sram_base_addr and address < sram_end_addr:
                offset = address - self.sram_base_addr
                if offset + len(data_bytes) <= len(self.sram_content):
                    self.sram_content[offset : offset + len(data_bytes)] = data_bytes 
                else:
                    print(f"DEBUG MODE: Simulated write to SRAM at 0x{address:08X} ignored (out of loaded SRAM bounds).")
        
        if verify:
            print("DEBUG MODE: Write verification skipped in mock mode.") 
        
        return True 

    def shutdown(self):
        """Simulates shutting down the mock CAN bus."""
        print("Mock CAN: Virtual bus shut down.")
        self.bus = None
