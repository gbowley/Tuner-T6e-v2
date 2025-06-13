# Lotus T6e Live Tuner

## Disclaimer

***Use at your own risk. I have labelled these tables and addresses based on my interpretation of the ECU firmware. Modifying your ECU calibration can result in unexpected behaviour, including damage. I accept no liability for any damage caused as a result of using this application.***

## Introduction

This tool is based on the tuner branch of Alcantor's LotusECU-T4e. I have used the previously described methods for CAN communication, and implemented them into a ground up rewrite that allows monitoring, logging, and live tuning of T6e cars.

This program is compatible with Lotus Exige V6 running the P138 firmware, with an unlocked calibration.

For firmware flashing continue to use [LotusECU-T4e](https://github.com/Alcantor/LotusECU-T4e).

I will update this tool, and definitions, as and when I have time.

## Installation (usb2can)

1.  **Python:** Ensure you have Python 3 installed. The recommended install is [3.9.7](https://www.python.org/downloads/release/python-397/) for environment compatibility with [Lotus Flasher](https://github.com/Alcantor/LotusECU-T4e)
2.  **Dependencies:** Install the required Python libraries. The primary dependencies are `python-can`, `pyserial`, and `pyqt5`. Open an elevated command prompt and run the following.
    ```bash
    pip install python-can
    pip install pyserial
    pip install pyqt5
    # pip install can-isotp # (Potentially needed depending on python-can version and usage)
    ```
3.  **CAN Interface Driver 1:** Install the necessary drivers for the [Korlan](https://shop.8devices.com/index.php?route=product/product&path=67&product_id=89) Adapter, including the [Windows Driver](https://drive.google.com/drive/folders/1gXWpuP20U2mhcW6IqtwhRo0PY9ZusSYv)
4. **CAN Interface Driver 2:** Install the [USB2CAN](https://drive.google.com/file/d/1_xSpR1bGE3OQN6w0EG9WmrvtgatyQa05/view) driver by placing `usb2can.dll` in your Python install directory.

## Usage

To run, launch `main_gui.py`

I have populated various basic parameters including RPM, MAF, O2 sensor voltage, fuel trims, etc. As well as some tables for live tuning. 

Variables and Map Tables (RPM, load, VE, Airmass etc) are defined in ecu_definitions.py.

## Changes

1. Rewrote application using pyqt5 as interface library.

## Issues
 
- Minimum cell size is slightly too large to fit entire 32x32 tables onto smaller screen (i.e. laptop).
- Dump and upload calram not yet added.
- Force zero STFT/LTFT not yet added.
- Only tested with USB2CAN.
