# lib/can_interface.py

import can

BO_BE = 'big'

class ECUException(Exception):
    """Custom exception for ECU communication errors."""
    pass

class LiveTuningAccess: # Handles DMA over canbus
    zones = [
        ("T6: L0-L1 (Bootloader)", 0x00000000, 0x010000, "bootldr.bin"), # Don't touch
        ("T6: L2 (Learned)"      , 0x00010000, 0x00C000, "decram.bin"), # Adaptation values
        ("T6: L3 (Coding)"       , 0x0001C000, 0x004000, "coding.bin"), # Coding values
        ("T6: L4 (Calibration)"  , 0x00020000, 0x010000, "calrom.bin"), # Calibration (tuning) values
        ("T6: M0-H3 (Program)"   , 0x00040000, 0x0C0000, "prog.bin"), # Program data, modify for patches
        ("T6: RAM (Main RAM)"    , 0x40000000, 0x010000, "calram.bin"), # SRAM data
        ("T6: L0-H3 (Full ROM)"  , 0x00000000, 0x100000, "dump.bin")
    ]

    def __init__(self):
        self.bus = None

    def open_can(self, interface, channel, bitrate):
        if self.bus is not None:
            self.close_can() # Ensure previous bus is closed
        print(f"Opening CAN bus: {interface} {channel} @ {bitrate//1000:d} kbit/s")
        try:
            self.bus = can.Bus(
                interface=interface,
                channel=channel,
                can_filters=[{
                    "extended": False,
                    "can_id": 0x7A0,
                    "can_mask": 0x7FF
                }],
                bitrate=bitrate
            )
            # Workaround for socketcan interface, kept from T4e app
            self.bus._is_filtered = False
            print("CAN bus opened successfully.")
        except Exception as e:
            raise ECUException(f"Failed to open CAN bus: {e}")

    def close_can(self):
        if self.bus is None:
            return
        print("Closing CAN bus.")
        self.bus.shutdown()
        self.bus = None

    def shutdown(self):  # Shutdown method for consistency with DataManager
        self.close_can()

    def read_memory(self, address, size):
        if self.bus is None:
            raise ECUException("CAN bus is not open. Cannot read memory.")

        data = bytearray()
        bytes_read = 0
        original_size = size # Store original size for validation

        while bytes_read < original_size:
            # Determine the chunk size for this read.
            # The maximum buffer read size is 255 bytes per request.
            chunk_size = min(original_size - bytes_read, 255)

            if chunk_size == 4:
                msg = can.Message(
                    is_extended_id=False, arbitration_id=0x50,
                    data=(address + bytes_read).to_bytes(4, BO_BE)
                )
                self.bus.send(msg)
                msg = self.bus.recv(timeout=1.0)
                if msg is None:
                    raise ECUException("ECU Read Word failed: No response!")
                if msg.dlc != 4:
                    raise ECUException(f"ECU Read Word failed: Unexpected answer DLC {msg.dlc} (expected 4)!")
                data.extend(msg.data)
                bytes_read += 4
            elif chunk_size == 2:
                msg = can.Message(
                    is_extended_id=False, arbitration_id=0x51,
                    data=(address + bytes_read).to_bytes(4, BO_BE)
                )
                self.bus.send(msg)
                msg = self.bus.recv(timeout=1.0)
                if msg is None:
                    raise ECUException("ECU Read Half failed: No response!")
                if msg.dlc != 2:
                    raise ECUException(f"ECU Read Half failed: Unexpected answer DLC {msg.dlc} (expected 2)!")
                data.extend(msg.data)
                bytes_read += 2
            elif chunk_size == 1:
                msg = can.Message(
                    is_extended_id=False, arbitration_id=0x52,
                    data=(address + bytes_read).to_bytes(4, BO_BE)
                )
                self.bus.send(msg)
                msg = self.bus.recv(timeout=1.0)
                if msg is None:
                    raise ECUException("ECU Read Byte failed: No response!")
                if msg.dlc != 1:
                    raise ECUException(f"ECU Read Byte failed: Unexpected answer DLC {msg.dlc} (expected 1)!")
                data.extend(msg.data)
                bytes_read += 1
            elif chunk_size > 0: # Buffer read logic for up to 255 bytes
                msg = can.Message(
                    is_extended_id=False, arbitration_id=0x53,
                    data=(address + bytes_read).to_bytes(4, BO_BE) + chunk_size.to_bytes(1, BO_BE)
                )
                self.bus.send(msg)
                
                chunk_data = bytearray()
                sub_chunk_bytes_read = 0
                while sub_chunk_bytes_read < chunk_size:
                    expected_dlc = min(8, chunk_size - sub_chunk_bytes_read)
                    msg = self.bus.recv(timeout=1.0)
                    if msg is None:
                        raise ECUException(f"ECU Read Buffer failed: No response for chunk starting at 0x{address + bytes_read:X}!")
                    
                    # For the last sub-chunk, dlc might be less than 8
                    if msg.dlc != expected_dlc and (chunk_size - sub_chunk_bytes_read) > 8:
                        raise ECUException(f"ECU Read Buffer failed: Unexpected answer DLC {msg.dlc} (expected {expected_dlc}) for chunk starting at 0x{address + bytes_read:X}!")
                    
                    chunk_data.extend(msg.data)
                    sub_chunk_bytes_read += msg.dlc
                
                if len(chunk_data) != chunk_size:
                    raise ECUException(f"ECU Read Buffer failed: Read {len(chunk_data)} bytes, expected {chunk_size} bytes for chunk starting at 0x{address + bytes_read:X}!")
                
                data.extend(chunk_data)
                bytes_read += chunk_size
            else:
                break # Should not happen if size is positive

        if len(data) != original_size:
            raise ECUException(f"ECU Read failed: Read {len(data)} bytes in total, expected {original_size} bytes!")
        return data


    def write_memory(self, address, data, verify=False):
        if self.bus is None:
            raise ECUException("CAN bus is not open. Cannot write memory.")

        total_size = len(data)
        bytes_written = 0

        while bytes_written < total_size:
            chunk_size = min(total_size - bytes_written, 255) # Max 255 bytes per buffer write

            current_address = address + bytes_written
            current_data = data[bytes_written : bytes_written + chunk_size]

            if chunk_size == 4:
                msg = can.Message(
                    is_extended_id = False, arbitration_id = 0x54,
                    data = current_address.to_bytes(4, BO_BE) + current_data
                )
                self.bus.send(msg)
            elif chunk_size == 2:
                msg = can.Message(
                    is_extended_id = False, arbitration_id = 0x55,
                    data = current_address.to_bytes(4, BO_BE) + current_data
                )
                self.bus.send(msg)
            elif chunk_size == 1:
                msg = can.Message(
                    is_extended_id = False, arbitration_id = 0x56,
                    data = current_address.to_bytes(4, BO_BE) + current_data
                )
                self.bus.send(msg)
            elif chunk_size > 0:
                offset_in_chunk = 0
                # Send initial message with address and total size for this chunk
                msg = can.Message(
                    is_extended_id = False, arbitration_id = 0x57,
                    data = current_address.to_bytes(4, BO_BE) + chunk_size.to_bytes(1, BO_BE)
                )
                self.bus.send(msg)
                # Send data in 8-byte sub-chunks for this chunk
                while(offset_in_chunk < chunk_size):
                    sub_chunk_size = min(8, chunk_size - offset_in_chunk)
                    msg = can.Message(
                        is_extended_id = False, arbitration_id = 0x57,
                        data = current_data[offset_in_chunk : offset_in_chunk + sub_chunk_size]
                    )
                    self.bus.send(msg)
                    offset_in_chunk += sub_chunk_size
            else:
                break # Should not happen if data is not empty

            bytes_written += chunk_size

        # Write Verification
        if verify:
            try:
                # Read back the data that was just written
                read_data = self.read_memory(address, total_size) # Read the entire original size
                if data != read_data:
                    raise ECUException("ECU Write failed: Verification mismatch! Data written does not match data read back.")
            except ECUException as e:
                raise ECUException(f"ECU Write failed during verification: {e}")
            except Exception as e:
                raise ECUException(f"An unexpected error occurred during write verification: {e}")


# Wrapper for DataManager
# This class is not directly used by DataManager's connect_source method, but remains here for potential future use.
class CanCommunicator:
    def __init__(self, interface='socketcan', channel='can0', bitrate=500000):
        self.live_tuning_access = LiveTuningAccess()
        
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate
        self._is_connected = False
        
        try:
            self.live_tuning_access.open_can(self.interface, self.channel, self.bitrate)
            self._is_connected = True
        except ECUException as e:
            print(f"Failed to connect to CAN bus (ECUException): {e}")
            self._is_connected = False
        except Exception as e:
            print(f"Failed to connect to CAN bus (General Error): {e}")
            self._is_connected = False

    @property
    def is_connected(self):
        return self._is_connected

    def read_bytes(self, address, length):
        if not self.is_connected:
            print("CAN not connected, cannot read bytes. Returning zeros.")
            return b'\x00' * length # Return zeros if not connected

        try:
            data = self.live_tuning_access.read_memory(address, length)
            return data
        except ECUException as e:
            print(f"ECU Read Error: {e}. Returning zeros.")
            return b'\x00' * length # Return zeros on ECU error
        except Exception as e:
            print(f"Unexpected CAN Read Error: {e}. Returning zeros.")
            return b'\x00' * length # Return zeros on unexpected error

    def write_bytes(self, address, data_bytes, verify=False):
        if not self.is_connected:
            print("CAN not connected, cannot write bytes.")
            return False # Indicate write failure

        try:
            self.live_tuning_access.write_memory(address, data_bytes, verify)
            return True # Indicate write success
        except ECUException as e:
            print(f"ECU Write Error: {e}")
            return False # Indicate write failure
        except Exception as e:
            print(f"Unexpected CAN Write Error: {e}")
            return False # Indicate write failure


    def disconnect(self):
        if self.is_connected:
            self.live_tuning_access.close_can()
            self._is_connected = False