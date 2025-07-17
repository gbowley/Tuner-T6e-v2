# lib/ecu_definitions.py

MAPTABLE_COLOR_GRADIENT = [
    [153, 153, 255], # Blue (lowest)
    [152, 255, 125], # Green
    [255, 255, 115], # Yellow
    [255, 102, 102]  # Red (highest)
]

ECU_DEFINITIONS = [
    {
        "description": "RPM",
        "address": 0x400015bc,
        "length": 2,  # 2 bytes
        "scale": 0.25,
        "offset": 0,
        "unit": "RPM",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 8000,
    },
    {
        "description": "Load",
        "address": 0x400019bc,
        "length": 2, 
        "scale": 1,
        "offset": 0, 
        "unit": "mg/stroke",
        "type": "gauge_bar",
        "min_val": 30,
        "max_val": 900,
    },
    {
        "description": "Coolant",
        "address": 0x4000167e,
        "length": 1,
        "scale": 0.625,
        "offset": -40,
        "unit": "°C",
        "type": "gauge_bar",
        "min_val": -20,
        "max_val": 140,
    },
    {
        "description": "Air Temp",
        "address": 0x40001682,
        "length": 1,
        "scale": 0.625,
        "offset": -40,
        "unit": "°C",
        "type": "gauge_bar",
        "min_val": -50,
        "max_val": 50,
    },
    {
        "description": "MAF",
        "address": 0x4000168c,
        "length": 2,
        "unit": "g/s",
        "type": "gauge_chart",
        "min_val": 0,
        "max_val": 300,
        "calculation": {    # calculation may be used to define complex scaling involving other data. Here, 1.5 is cylinger count multiplied by LSB (0.25). 
            "type": "formula",
            "formula_string": "MAF_RAW * RPM_VALUE * 1.5 / 120000",
            "dependencies": ["RPM", "MAF"],
        }
    },
    {
        "description": "TPS",
        "address": 0x4000216a,
        "length": 2,
        "scale": 0.0978,
        "offset": 0,
        "unit": "%",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 100,
    },
    {
        "description": "PPS",
        "address": 0x40001ea6,
        "length": 2,
        "scale": 0.0978,
        "offset": 0,
        "unit": "%",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 100,
    },
    {
        "description": "Injector Pulse B1",
        "address": 0x40001334,
        "length": 2,
        "scale": 1,
        "offset": 0,
        "unit": "us",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 16000,
    },
    {
        "description": "Injector Pulse B2",
        "address": 0x40001336,
        "length": 2,
        "scale": 1,
        "offset": 0,
        "unit": "us",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 16000,
    },
    {
        "description": "O2-Bank1",
        "address": 0x400026ec,
        "length": 2,
        "scale": 0.0003052,
        "offset": 0,
        "unit": "v",
        "type": "gauge_chart",
        "min_val": 0,
        "max_val": 1,
    },
    {
        "description": "O2-Bank2",
        "address": 0x400026ee,
        "length": 2,
        "scale": 0.0003052,
        "offset": 0,
        "unit": "v",
        "type": "gauge_chart",
        "min_val": 0,
        "max_val": 1,
    },
    {
        "description": "STFT-B1",
        "address": 0x40001694,
        "length": 2,
        "scale": 0.05,
        "offset": 0,
        "unit": "%",
        "type": "gauge_chart",
        "min_val": -10,
        "max_val": 10,
    },
    {
        "description": "STFT-B2",
        "address": 0x40001696,
        "length": 2,
        "scale": 0.05,
        "offset": 0,
        "unit": "%",
        "type": "gauge_chart",
        "min_val": -10,
        "max_val": 10,
    },
    {
        "description": "LTFT-B1",
        "address": 0x40001ae0,
        "length": 2,
        "scale": 0.05,
        "offset": 0,
        "unit": "%",
        "type": "gauge_bar",
        "min_val": -10,
        "max_val": 10,
    },
    {
        "description": "LTFT-B2",
        "address": 0x40001ae2,
        "length": 2,
        "scale": 0.05,
        "offset": 0,
        "unit": "%",
        "type": "gauge_bar",
        "min_val": -10,
        "max_val": 10,
    },
    {
        "description": "AFR Target",
        "address": 0x40001792,
        "length": 2,
        "scale": 0.01,
        "offset": 0,
        "unit": "AFR",
        "type": "gauge_bar",
        "min_val": 8,
        "max_val": 17,
    },
    {
        "description": "Gear",
        "address": 0x4000186e,
        "length": 2,
        "scale": 1,
        "offset": 0,
        "unit": "#",
        "type": "gauge_bar",
        "min_val": 0,
        "max_val": 6,
    },
    {
        "description": "Ignition Timing",
        "address": 0x40002cdc,
        "length": 12,
        "element_size": 2,
        "scale": 0.25,
        "offset": [-387.5, -687.5, -987.5, -1287.5, -1587.5, -87.5],
        "unit": "°",
        "type": "table",
        "columns": ["Cyl 1", "Cyl 2", "Cyl 3", "Cyl 4", "Cyl 5", "Cyl 6"] 
    },
    {
        "description": "Knock Retard",
        "address": 0x40001bb8,
        "length": 12,
        "element_size": 2,
        "scale": 0.25,
        "offset": [0,0,0,0,0,0],
        "unit": "°",
        "type": "table",
        "columns": ["Cyl 1", "Cyl 2", "Cyl 3", "Cyl 4", "Cyl 5", "Cyl 6"] 
    },
    {
        "description": "Volumetric Efficiency",
        "type": "maptable",

        # Data Block Definition
        "data_address": 0x40009e0a,
        "data_rows": 32,
        "data_cols": 32,
        "data_element_size": 1,
        "data_scale": 0.5,
        "data_offset": 0,
        "data_reverse_scale": 2.0,
        "data_reverse_offset": 0,

        # X-Axis Definition (horizontal header)
        "x_axis_address": 0x40009dca,
        "x_axis_length": 32,
        "x_axis_element_size": 1,
        "x_axis_scale": 31.25,
        "x_axis_offset": 500,
        "x_axis_reverse_scale": 0.1,
        "x_axis_reverse_offset": 0,

        # Y-Axis Definition (vertical header)
        "y_axis_address": 0x40009dea,
        "y_axis_length": 32,
        "y_axis_element_size": 1,
        "y_axis_scale": 4,
        "y_axis_offset": 0,
        "y_axis_reverse_scale": 0.25,
        "y_axis_reverse_offset": 0,

        # Units for display
        "units": {
            "data": "%",
            "x_axis": "RPM",
            "y_axis": "Load"
        }
    },
    {
        "description": "Airmass",
        "type": "maptable",

        # Data Block Definition
        "data_address": 0x4000b5e2,
        "data_rows": 16,
        "data_cols": 16,
        "data_element_size": 1,
        "data_scale": 4,
        "data_offset": 0,
        "data_reverse_scale": 0.25,
        "data_reverse_offset": 0,

        # X-Axis Definition (horizontal header)
        "x_axis_address": 0x4000b5c2,
        "x_axis_length": 16,
        "x_axis_element_size": 1,
        "x_axis_scale": 31.25,
        "x_axis_offset": 500,
        "x_axis_reverse_scale": 0.1,
        "x_axis_reverse_offset": 0,

        # Y-Axis Definition (vertical header)
        "y_axis_address": 0x4000b5d2,
        "y_axis_length": 16,
        "y_axis_element_size": 1,
        "y_axis_scale": 0.392,
        "y_axis_offset": 0,
        "y_axis_reverse_scale": 2.551,
        "y_axis_reverse_offset": 0,

        # Units for display
        "units": {
            "data": "mg/stroke",
            "x_axis": "RPM",
            "y_axis": "TPS"
        }
    },
    {
        "description": "Ignition Timing",
        "type": "maptable",

        # Data Block Definition
        "data_address": 0x4000abaa,
        "data_rows": 20,
        "data_cols": 20,
        "data_element_size": 1,
        "data_scale": 0.25,
        "data_offset": -10,
        "data_reverse_scale": 4,
        "data_reverse_offset": 10,

        # X-Axis Definition (horizontal header)
        "x_axis_address": 0x4000ab82,
        "x_axis_length": 20,
        "x_axis_element_size": 1,
        "x_axis_scale": 31.25,
        "x_axis_offset": 500,
        "x_axis_reverse_scale": 0.032,
        "x_axis_reverse_offset": -500,

        # Y-Axis Definition (vertical header)
        "y_axis_address": 0x4000ab96,
        "y_axis_length": 20,
        "y_axis_element_size": 1,
        "y_axis_scale": 4,
        "y_axis_offset": 0,
        "y_axis_reverse_scale": 0.25,
        "y_axis_reverse_offset": 0,

        # Units for display
        "units": {
            "data": "°BTDC",
            "x_axis": "RPM",
            "y_axis": "Load"
        }
    },
    {
        "description": "Idle A",
        "type": "maptable",

        # Data Block Definition
        "data_address": 0x4000b5b2,
        "data_rows": 1,
        "data_cols": 16,
        "data_element_size": 1,
        "data_scale": 10,
        "data_offset": 0,
        "data_reverse_scale": 0.01,
        "data_reverse_offset": 0,

        # X-Axis Definition (horizontal header)
        "x_axis_address": 0x4000b5a2,
        "x_axis_length": 16,
        "x_axis_element_size": 1,
        "x_axis_scale": 0.625,
        "x_axis_offset": -40,
        "x_axis_reverse_scale": 0.032,
        "x_axis_reverse_offset": -500,

        # Units for display
        "units": {
            "data": "RPM",
            "x_axis": "ECT",
        }
    },
]