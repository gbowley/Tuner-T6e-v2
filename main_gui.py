# main_gui.py

import sys
import math
import os
import time
import csv
import re
from collections import deque
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QDialog, QLineEdit, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QLabel, QInputDialog, QGridLayout
)
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QFont, QIntValidator, QResizeEvent, QDoubleValidator
from PyQt5.QtCore import Qt, QTimer, QPointF, QRect, QSize

from lib.ecu_definitions import ECU_DEFINITIONS, MAPTABLE_COLOR_GRADIENT
from lib.data_manager import DataManager


class GaugeWidget(QWidget):
    def __init__(self, description, unit, min_val, max_val, gauge_type, parent=None):
        super().__init__(parent)
        self.description = description
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.gauge_type = gauge_type
        self._value = 0

        self.setFixedSize(200, 150)

        if self.gauge_type == "gauge_chart":
            self.value_history = deque(maxlen=200) # Store last 10 seconds of data, assuming 20 updates/sec
            self.chart_update_timer = QTimer(self)
            self.chart_update_timer.timeout.connect(self.update)
            self.chart_update_timer.start(50) # Update every 50ms (20 times per second)

    def set_value(self, value):
        self._value = value
        if self.gauge_type == "gauge_chart":
            self.value_history.append((time.time(), value))
        self.update() # This will trigger paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.white)
        font = painter.font()

        # Draw background rectangle for the widget
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(self.rect())

        if self.gauge_type == "gauge_bar":
            self._paint_gauge_bar(painter, font)
        elif self.gauge_type == "gauge_chart":
            self._paint_gauge_chart(painter, font)

    def _paint_gauge_bar(self, painter, font):
        # This method remains UNCHANGED from the previous working version for gauge_bar.
        # Gauge Name and Units
        font.setPointSize(12)
        painter.setFont(font)
        name_unit_rect = self.rect().adjusted(5, 5, -5, -self.height() // 3 * 2 - 5)
        painter.drawText(name_unit_rect, Qt.AlignCenter, f"{self.description} ({self.unit})")

        # Current Value
        font.setPointSize(24)
        painter.setFont(font)
        value_rect = self.rect().adjusted(5, self.height() // 3, -5, -self.height() // 3)
        painter.drawText(value_rect, Qt.AlignCenter, f"{self._value:.1f}")

        # Bar Gauge
        bar_height = 20
        bar_margin = 10
        bar_width = self.width() - 2 * bar_margin
        bar_y = self.height() - bar_height - bar_margin
        bar_rect = self.rect().adjusted(bar_margin, bar_y, -bar_margin, -(self.height() - bar_y - bar_height))

        # Draw bar background
        painter.setBrush(QBrush(QColor(70, 70, 70)))
        painter.drawRect(bar_rect)

        # Calculate fill level
        normalized_value = (self._value - self.min_val) / (self.max_val - self.min_val)
        normalized_value = max(0, min(1, normalized_value)) # Clamp between 0 and 1

        fill_width = bar_width * normalized_value
        painter.setBrush(QBrush(QColor(0, 180, 0))) # Green bar
        painter.drawRect(bar_rect.x(), bar_rect.y(), int(fill_width), bar_rect.height())

    def _paint_gauge_chart(self, painter, font):
        # --- MODIFIED: Description, Unit, and Value on the top line ---
        font.setPointSize(14) # Slightly larger for readability
        painter.setFont(font)

        # Format the top text: "Description (Unit): Value"
        top_text = f"{self.description} ({self.unit}): {self._value:.1f}"
        
        # Adjust rectangle to center this text at the top
        # This rect will be roughly the top quarter of the widget
        text_rect = self.rect().adjusted(5, 5, -5, -self.height() // 4 * 3) # Adjusted to give space for chart below
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, top_text)


        # Chart drawing area - positioned below the top text
        chart_margin = 10
        
        # Calculate chart_rect.y() to start below the top text,
        # and adjust height accordingly
        chart_top_y = text_rect.bottom() + 5 # Start 5 pixels below the text_rect
        chart_height = self.height() - chart_top_y - chart_margin # Remaining height minus bottom margin

        chart_rect = self.rect().adjusted(
            chart_margin, 
            int(chart_top_y), 
            -chart_margin, 
            -(self.height() - chart_top_y - chart_height) # Adjust bottom of rect
        )
        # Ensure chart_rect has positive dimensions
        if chart_rect.height() <= 0:
            return # Not enough space to draw chart


        # Draw chart background
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawRect(chart_rect)

        if len(self.value_history) < 2:
            return # Not enough data to draw a line

        # Calculate X-axis (time) range - last 10 seconds
        current_time = time.time()
        start_time_chart = current_time - 10
        end_time_chart = current_time

        # Filter values within the last 10 seconds
        visible_history = [(t, v) for t, v in self.value_history if t >= start_time_chart]

        if len(visible_history) < 2:
            return # Still not enough data

        # Draw the chart line
        painter.setPen(QPen(QColor(0, 200, 255), 2)) # Blue line for the chart

        points = []
        for t, value in visible_history:
            # Normalize time for X-axis
            time_normalized = (t - start_time_chart) / (end_time_chart - start_time_chart)
            x = chart_rect.x() + time_normalized * chart_rect.width()

            # Normalize value for Y-axis (inverted because Y increases downwards)
            value_normalized = (value - self.min_val) / (self.max_val - self.min_val)
            value_normalized = max(0, min(1, value_normalized)) # Clamp
            y = chart_rect.y() + (1 - value_normalized) * chart_rect.height()
            points.append(QPointF(x, y))

        # Connect the points
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i+1])

        # Draw min/max lines for reference
        painter.setPen(QPen(QColor(100, 100, 100), 1, Qt.DotLine))
        # Min line
        y_min = chart_rect.y() + (1 - 0) * chart_rect.height() # 0 normalized value
        painter.drawLine(chart_rect.x(), y_min, chart_rect.right(), y_min)
        # Max line
        y_max = chart_rect.y() + (1 - 1) * chart_rect.height() # 1 normalized value
        painter.drawLine(chart_rect.x(), y_max, chart_rect.right(), y_max)

class DataSourceDialog(QDialog):
    def __init__(self, data_manager_instance, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Data Source")
        self.setGeometry(100, 100, 400, 250) # Increased size to accommodate new fields

        self.source_type = None
        self.ram_dump_path = None
        self.can_interface = None
        self.can_channel = None
        self.can_bitrate = None

        main_layout = QVBoxLayout()

        source_label = QLabel("Choose Data Source:")
        self.source_combo = QComboBox()
        self.source_combo.addItem("Live CAN Data", "CAN")
        self.source_combo.addItem("RAM Dump File", "RAM")
        self.source_combo.currentIndexChanged.connect(self.update_option_visibility)
        main_layout.addWidget(source_label)
        main_layout.addWidget(self.source_combo)

        self.can_options_group = QWidget()
        can_layout = QVBoxLayout(self.can_options_group)
        can_layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins

        # Interface
        interface_layout = QHBoxLayout()
        interface_label = QLabel("Interface:")
        self.interface_combo = QComboBox()
        # Common CAN interfaces for python-can, add/remove as needed
        self.interface_combo.addItems(["socketcan", "usb2can", "pcan"])
        self.interface_combo.setCurrentText("usb2can") # Default interface
        interface_layout.addWidget(interface_label)
        interface_layout.addWidget(self.interface_combo)
        can_layout.addLayout(interface_layout)

        # Channel (Device ID)
        channel_layout = QHBoxLayout()
        channel_label = QLabel("Channel/Dev ID:")
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("e.g., can0, USBCAN-1")
        self.channel_input.setText("can0") # Default channel
        channel_layout.addWidget(channel_label)
        channel_layout.addWidget(self.channel_input)
        can_layout.addLayout(channel_layout)

        # Baud Rate
        bitrate_layout = QHBoxLayout()
        bitrate_label = QLabel("Baud Rate (bps):")
        self.bitrate_input = QLineEdit()
        self.bitrate_input.setValidator(QIntValidator(1, 10000000, self)) # Validator for integer input
        self.bitrate_input.setText("500000") # Default baud rate
        bitrate_layout.addWidget(bitrate_label)
        bitrate_layout.addWidget(self.bitrate_input)
        can_layout.addLayout(bitrate_layout)

        main_layout.addWidget(self.can_options_group)

        # --- RAM Dump Path Group ---
        self.ram_path_group = QWidget()
        ram_layout = QVBoxLayout(self.ram_path_group)
        ram_layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins

        ram_path_input_layout = QHBoxLayout()
        self.ram_path_label = QLabel("RAM Dump Path:")
        self.ram_path_input = QLineEdit()
        # Set default path for RAM dump
        self.ram_path_input.setText(os.path.normpath("./ram/calram.bin")) # Default path, normalize for OS
        self.ram_path_input.setPlaceholderText(os.path.normpath("./ram/calram.bin"))
        ram_path_input_layout.addWidget(self.ram_path_label)
        ram_path_input_layout.addWidget(self.ram_path_input)
        ram_layout.addLayout(ram_path_input_layout)

        main_layout.addWidget(self.ram_path_group)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        self.update_option_visibility() # Set initial visibility

    def update_option_visibility(self):
        """Shows/hides CAN options or RAM dump path based on source selection."""
        selected_type = self.source_combo.currentData()
        if selected_type == "CAN":
            self.can_options_group.show()
            self.ram_path_group.hide()
        elif selected_type == "RAM":
            self.can_options_group.hide()
            self.ram_path_group.show()
        else:
            self.can_options_group.hide()
            self.ram_path_group.hide()

    def accept(self):
        self.source_type = self.source_combo.currentData()
        if self.source_type == "RAM":
            self.ram_dump_path = self.ram_path_input.text().strip()
            # If the user clears the path, revert to default
            if not self.ram_dump_path:
                self.ram_dump_path = os.path.normpath("./ram/calram.bin")
        elif self.source_type == "CAN":
            self.can_interface = self.interface_combo.currentText().strip()
            self.can_channel = self.channel_input.text().strip()
            # Validate and convert bitrate
            try:
                self.can_bitrate = int(self.bitrate_input.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please provide a valid numeric baud rate.")
                return # Prevent dialog from closing

            if not self.can_channel:
                QMessageBox.warning(self, "Input Error", "Please provide a CAN channel/device ID.")
                return
            if not self.bitrate_input.hasAcceptableInput(): # Check if bitrate input is valid
                 QMessageBox.warning(self, "Input Error", "Please provide a valid numeric baud rate.")
                 return

        super().accept()

class MapTableWidget(QWidget):
    class _CustomTableWidget(QTableWidget):
        def __init__(self, *args, **kwargs):
            self._maptable_widget = kwargs.pop('maptable_parent', None)
            super().__init__(*args, **kwargs)

        def paintEvent(self, event):
            super().paintEvent(event)

            if self._maptable_widget:
                if self._maptable_widget.data_manager.is_connected() and \
                   self._maptable_widget.rpm_value is not None and \
                   self._maptable_widget.load_value is not None:
                    painter = QPainter(self.viewport())
                    self._maptable_widget.draw_cursor(painter)
                    painter.end()

    def __init__(self, maptable_definition, data_manager, parent=None):
        super().__init__(parent)
        self.definition = maptable_definition
        self.data_manager = data_manager
        self.table = QTableWidget(self.definition["data_rows"], self.definition["data_cols"])

        self._min_data_value = float('inf')
        self._max_data_value = float('-inf')

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # X-axis unit label
        self.x_axis_unit_label = QLabel("")
        self.x_axis_unit_label.setAlignment(Qt.AlignCenter)
        self.x_axis_unit_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.x_axis_unit_label.setStyleSheet("color: black;")
        self.x_axis_unit_label.hide()
        self.layout.addWidget(self.x_axis_unit_label)

        table_and_y_unit_layout = QHBoxLayout()
        self.layout.addLayout(table_and_y_unit_layout)

        # Y-axis unit label
        self.y_axis_unit_label = QLabel("")
        self.y_axis_unit_label.setAlignment(Qt.AlignCenter)
        self.y_axis_unit_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.y_axis_unit_label.setStyleSheet("color: black; padding-left: 5px; padding-right: 5px;")
        self.y_axis_unit_label.setFixedWidth(50)
        self.y_axis_unit_label.hide()
        table_and_y_unit_layout.addWidget(self.y_axis_unit_label)

        # Initialize the QTableWidget
        self.table = self._CustomTableWidget(maptable_parent=self)
        table_and_y_unit_layout.addWidget(self.table)

        self.table.setRowCount(self.definition["data_rows"])
        self.table.setColumnCount(self.definition["data_cols"])

        # Set up editable cells
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.AnyKeyPressed)
        # Connect the itemChanged signal to handler
        self.table.itemChanged.connect(self._handle_cell_edit)

        # Axis Data format
        header_font = QFont("Arial", 10, QFont.Bold)
        self.table.horizontalHeader().setFont(header_font)
        self.table.verticalHeader().setFont(header_font)

        # Adjust header sizing
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Define colors for headers
        header_border_color = "rgb(250, 250, 250)"  # Dark grey for borders
        header_fill_color = "rgb(180, 180, 180)"    # Slightly darker grey for fill
        header_text_color = "black"              # White text for contrast

        header_style_sheet = f"""
            QHeaderView::section {{
                background-color: {header_fill_color};
                border: 1px solid {header_border_color};
                color: {header_text_color};
                padding: 4px;
            }}
            /* Horizontal header sections */
            QHeaderView::horizontal {{
                border-bottom: 1px solid {header_border_color};
            }}
            /* Vertical header sections */
            QHeaderView::vertical {{
                border-right: 1px solid {header_border_color};
            }}
        """
        self.table.horizontalHeader().setStyleSheet(header_style_sheet)
        self.table.verticalHeader().setStyleSheet(header_style_sheet)

        # Cursor Setup
        self.rpm_value = None  # Current RPM value for cursor
        self.load_value = None  # Current Load value for cursor
        self.x_axis_values = []  # Store scaled X-axis values
        self.y_axis_values = []  # Store scaled Y-axis values
        self.min_data_val = float('inf') 
        self.max_data_val = float('-inf') 

        # Load and display initial data
        self._load_and_display_map_data()

        # Connect signals for cell editing
        self.table.itemChanged.connect(self._handle_cell_edit)

    def _update_min_max_data_values(self, new_value):
        if new_value < self._min_data_value:
            self._min_data_value = new_value
        if new_value > self._max_data_value:
            self._max_data_value = new_value

    def _convert_to_scaled(self, raw_val, scale, offset):
        return (raw_val * scale) + offset

    def _convert_to_raw(self, scaled_value, reverse_scale, reverse_offset, element_size):
        raw_value_float = (scaled_value - reverse_offset) * reverse_scale
        
        raw_value = int(round(raw_value_float))

        max_unsigned_val = (1 << (element_size * 8)) - 1
        min_signed_val = -(1 << (element_size * 8 - 1))
        max_signed_val = (1 << (element_size * 8 - 1)) - 1

        if raw_value < 0:
            raw_value = 0 

        raw_value = max(0, min(raw_value, max_unsigned_val))

        return raw_value.to_bytes(element_size, 'big', signed=False)

    def _load_and_display_map_data(self):
        self.table.blockSignals(True)

        x_axis_unit = self.definition['units'].get('x_axis', '')
        if x_axis_unit:
            self.x_axis_unit_label.setText(x_axis_unit)
            self.x_axis_unit_label.show()
        else:
            self.x_axis_unit_label.hide()

        y_axis_unit = self.definition['units'].get('y_axis', '')
        if y_axis_unit:
            self.y_axis_unit_label.setText(y_axis_unit)
            self.y_axis_unit_label.show()
        else:
            self.y_axis_unit_label.hide()

        if not self.data_manager.is_connected():
            print(f"MapTableWidget: Not connected. Populating '{self.definition['description']}' with 'N/A'.")
            x_values = [f"X{i}" for i in range(self.definition["data_cols"])]
            self.table.setHorizontalHeaderLabels(x_values)
            self.x_axis_values = []
            self.y_axis_values = []

            if "y_axis_address" in self.definition:
                y_values = [f"Y{i}" for i in range(self.definition["data_rows"])]
                self.table.setVerticalHeaderLabels(y_values)
                self.table.verticalHeader().show()
            else:
                self.table.verticalHeader().hide()

            for r in range(self.definition["data_rows"]):
                for c in range(self.definition["data_cols"]):
                    item = QTableWidgetItem("N/A")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(r, c, item)

            self.table.blockSignals(False)
            self.table.viewport().update()
            return

        try:
            x_axis_def = self.definition
            x_raw_bytes = self.data_manager.read_data(x_axis_def["x_axis_address"], x_axis_def["x_axis_length"])
            x_values_str = []
            self.x_axis_values = []
            if x_raw_bytes and len(x_raw_bytes) == x_axis_def["x_axis_length"]:
                for i in range(0, x_axis_def["x_axis_length"], x_axis_def["x_axis_element_size"]):
                    raw_val = int.from_bytes(x_raw_bytes[i:i+x_axis_def["x_axis_element_size"]], 'big', signed=False)
                    scaled_val = self._convert_to_scaled(raw_val, x_axis_def["x_axis_scale"], x_axis_def["x_axis_offset"])
                    self.x_axis_values.append(scaled_val)
                    x_values_str.append(f"{int(round(scaled_val))}")
            else:
                x_values_str = [f"X{i} (Err)" for i in range(self.definition["data_cols"])]
                print(f"Warning: Failed to read X-axis data for {self.definition['description']}")
            self.table.setHorizontalHeaderLabels(x_values_str)

            y_values_str = []
            self.y_axis_values = []
            if "y_axis_address" in self.definition:
                y_axis_def = self.definition
                y_raw_bytes = self.data_manager.read_data(y_axis_def["y_axis_address"], y_axis_def["y_axis_length"])
                if y_raw_bytes and len(y_raw_bytes) == y_axis_def["y_axis_length"]:
                    for i in range(0, y_axis_def["y_axis_length"], y_axis_def["y_axis_element_size"]):
                        raw_val = int.from_bytes(y_raw_bytes[i:i+y_axis_def["y_axis_element_size"]], 'big', signed=False)
                        scaled_val = self._convert_to_scaled(raw_val, y_axis_def["y_axis_scale"], y_axis_def["y_axis_offset"])
                        self.y_axis_values.append(scaled_val)
                        y_values_str.append(f"{int(round(scaled_val))}")
                else:
                    y_values_str = [f"Y{i} (Err)" for i in range(self.definition["data_rows"])]
                    print(f"Warning: Failed to read Y-axis data for {self.definition['description']}")
                self.table.setVerticalHeaderLabels(y_values_str)
                self.table.verticalHeader().show()
            else:
                self.table.verticalHeader().hide()

            data_def = self.definition
            data_block_length = data_def["data_rows"] * data_def["data_cols"] * data_def["data_element_size"]
            data_raw_bytes = self.data_manager.read_data(data_def["data_address"], data_block_length)

            if data_raw_bytes and len(data_raw_bytes) == data_block_length:
                idx = 0
                for r in range(data_def["data_rows"]):
                    for c in range(data_def["data_cols"]):
                        if idx + data_def["data_element_size"] <= len(data_raw_bytes):
                            cell_raw_bytes = data_raw_bytes[idx : idx + data_def["data_element_size"]]
                            cell_raw_val = int.from_bytes(cell_raw_bytes, 'big', signed=False)
                            scaled_val = self._convert_to_scaled(cell_raw_val, data_def["data_scale"], data_def["data_offset"])

                            item = QTableWidgetItem(f"{scaled_val:.1f}")
                            self.table.setItem(r, c, item)
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                            idx += data_def["data_element_size"]
                        else:
                            item = QTableWidgetItem("N/A")
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                            self.table.setItem(r, c, item)
                            print(f"Warning: Incomplete data block for {self.definition['description']} at row {r}, col {c}")
                            break

                    if idx + data_def["data_element_size"] > len(data_raw_bytes) and c < data_def["data_cols"] -1 : 
                         break

                self._apply_color_gradient() 
            else:
                print(f"Warning: Failed to read data for {self.definition['description']}. Populating with 'Error'.")
                for r in range(data_def["data_rows"]):
                    for c in range(data_def["data_cols"]):
                        item = QTableWidgetItem("Error")
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.table.setItem(r, c, item)

        except Exception as e:
            print(f"Error loading map data for {self.definition['description']}: {e}")
            QMessageBox.critical(self, "Map Load Error", f"Failed to load map '{self.definition['description']}': {e}")
            for r in range(self.definition["data_rows"]):
                for c in range(self.definition["data_cols"]):
                    item = QTableWidgetItem("Error")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(r, c, item)
        finally:
            self.table.blockSignals(False)
            self.table.viewport().update()
            self.table.repaint() 

    def _apply_color_gradient(self):

        current_min_val = float('inf')
        current_max_val = float('-inf')
        
        for r in range(self.definition["data_rows"]):
            for c in range(self.definition["data_cols"]):
                item = self.table.item(r, c)
                if item:
                    try:
                        scaled_value = float(item.text())
                        if scaled_value < current_min_val:
                            current_min_val = scaled_value
                        if scaled_value > current_max_val:
                            current_max_val = scaled_value
                    except ValueError:
                        pass

        if current_min_val == float('inf') or current_max_val == float('-inf') or \
           current_min_val == current_max_val:
            for r in range(self.definition["data_rows"]):
                for c in range(self.definition["data_cols"]):
                    item = self.table.item(r, c)
                    if item:
                        item.setBackground(QColor(240, 240, 240)) 
            return

        colors = MAPTABLE_COLOR_GRADIENT
        num_gradient_points = len(colors)

        value_range = current_max_val - current_min_val

        for r in range(self.definition["data_rows"]):
            for c in range(self.definition["data_cols"]):
                item = self.table.item(r, c)
                if item:
                    try:
                        scaled_value = float(item.text())
                        
                        normalized_value = (scaled_value - current_min_val) / value_range

                        normalized_value = max(0.0, min(1.0, normalized_value))

                        segment_index = int(normalized_value * (num_gradient_points - 1))
                        segment_index = min(segment_index, num_gradient_points - 2) 

                        color_start = colors[segment_index]
                        color_end = colors[segment_index + 1]

                        segment_start_norm_val = segment_index / (num_gradient_points - 1)
                        segment_end_norm_val = (segment_index + 1) / (num_gradient_points - 1)
                        
                        if (segment_end_norm_val - segment_start_norm_val) > 0:
                            interpolation_factor = (normalized_value - segment_start_norm_val) / \
                                                   (segment_end_norm_val - segment_start_norm_val)
                        else:
                            interpolation_factor = 0.0 

                        r_interp = int(color_start[0] * (1 - interpolation_factor) + color_end[0] * interpolation_factor)
                        g_interp = int(color_start[1] * (1 - interpolation_factor) + color_end[1] * interpolation_factor)
                        b_interp = int(color_start[2] * (1 - interpolation_factor) + color_end[2] * interpolation_factor)

                        item.setBackground(QColor(r_interp, g_interp, b_interp))
                        
                    except ValueError:
                        item.setBackground(QColor(255, 0, 0)) 
                    except Exception as e:
                        print(f"Error applying color to cell [{r},{c}]: {e}")
                        item.setBackground(QColor(200, 200, 200)) 

    def _handle_cell_edit(self, item):
        self.table.blockSignals(True)
        try:
            row = item.row()
            col = item.column()
            new_display_value_str = item.text()

            try:
                new_scaled_value = float(new_display_value_str)
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
                original_value = self._get_original_data_value(row, col)
                item.setText(f"{original_value:.2f}")
                return

            data_def = self.definition

            # Calculate address for the cell
            offset_in_block = (row * data_def["data_cols"] + col) * data_def["data_element_size"]
            target_address = data_def["data_address"] + offset_in_block

            # Convert scaled float value back to raw bytes
            raw_bytes_to_write = self._convert_to_raw(
                new_scaled_value,
                data_def["data_reverse_scale"],
                data_def["data_reverse_offset"],
                data_def["data_element_size"]
            )

            # Write the data using DataManager
            if self.data_manager.write_data(target_address, raw_bytes_to_write):
                self._apply_color_gradient()
            else:
                QMessageBox.critical(self, "Write Error",
                                     f"Failed to write changes to data source at address 0x{target_address:X}.")
                # Revert cell content if write failed
                original_value = self._get_original_data_value(row, col)
                item.setText(f"{original_value:.2f}")

        finally:
            self.table.blockSignals(False)

    def _get_original_data_value(self, row, col): #
        # Re-read the data from the data source to get the true original value (for robustness)
        data_def = self.definition #
        offset_in_block = (row * data_def["data_cols"] + col) * data_def["data_element_size"] #
        target_address = data_def["data_address"] + offset_in_block #
        length = data_def["data_element_size"] #

        raw_bytes = self.data_manager.read_data(target_address, length) #
        if raw_bytes: #
            raw_val = int.from_bytes(raw_bytes, 'big', signed=False) #
            scaled_val = self._convert_to_scaled(raw_val, data_def["data_scale"], data_def["data_offset"]) #
            return scaled_val #
        return 0.0 # Default if read fails #

    def adjust_selected_cells(self, adjustment_value, operation_type):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "No Cells Selected", "Please select cells to adjust.")
            return

        data_def = self.definition
        
        self.table.blockSignals(True)
        
        # Accumulate all changes for a single write operation, reads the entire block, modifies it in memory, then writes it back.
        data_block_length = data_def["data_rows"] * data_def["data_cols"] * data_def["data_element_size"]
        current_data_raw_bytes = self.data_manager.read_data(data_def["data_address"], data_block_length)

        if not current_data_raw_bytes:
            QMessageBox.critical(self, "Read Error", "Failed to read current data from ECU/RAM dump for adjustment.")
            self.table.blockSignals(False)
            return

        modified_data_bytes = bytearray(current_data_raw_bytes)

        try:
            for selected_range in selected_ranges:
                top_row = selected_range.topRow()
                bottom_row = selected_range.bottomRow()
                left_col = selected_range.leftColumn()
                right_col = selected_range.rightColumn()

                for r in range(top_row, bottom_row + 1):
                    for c in range(left_col, right_col + 1):
                        # Calculate offset within the data block for the current cell
                        offset_in_block = (r * data_def["data_cols"] + c) * data_def["data_element_size"]
                        
                        # Extract current cell's raw bytes
                        cell_raw_bytes = modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]]
                        
                        # Convert to scaled value
                        raw_val = int.from_bytes(cell_raw_bytes, 'big', signed=False)
                        current_scaled_val = self._convert_to_scaled(raw_val, data_def["data_scale"], data_def["data_offset"])
                        
                        new_scaled_val = current_scaled_val
                        if operation_type == "increment":
                            new_scaled_val += adjustment_value
                        elif operation_type == "decrement":
                            new_scaled_val -= adjustment_value
                        elif operation_type == "scale":
                            new_scaled_val *= adjustment_value
                        
                        # Convert new scaled value back to raw bytes
                        new_raw_bytes_for_cell = self._convert_to_raw(
                            new_scaled_val,
                            data_def["data_reverse_scale"],
                            data_def["data_reverse_offset"],
                            data_def["data_element_size"]
                        )
                        
                        # Update the bytearray with the new raw bytes for the cell
                        modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]] = new_raw_bytes_for_cell

                        # Update the QTableWidgetItem display
                        item = self.table.item(r, c)
                        if item:
                            item.setText(f"{new_scaled_val:.2f}")
                        else:
                            item = QTableWidgetItem(f"{new_scaled_val:.2f}")
                            self.table.setItem(r, c, item)
                        
            # After processing all selected cells, write the entire modified block back
            if self.data_manager.write_data(data_def["data_address"], bytes(modified_data_bytes)):
                self._apply_color_gradient() # Reapply gradient after successful write
                self.table.viewport().update() # Force repaint
                
                self._apply_color_gradient()
                self.table.viewport().update()

                QMessageBox.information(self, "Adjustment Applied", "Selected cells adjusted and map reloaded.")
            else:
                QMessageBox.critical(self, "Write Error",
                                    f"Failed to write adjusted data to source at address 0x{data_def['data_address']:X}.")
                self._load_and_display_map_data() 
        finally:
            self.table.blockSignals(False)

    def inc_data(self, increment_value): #
        self._apply_batch_operation(lambda val, inc=increment_value: val + inc) #

    def dec_data(self, decrement_value): #
        self._apply_batch_operation(lambda val, dec=decrement_value: val - dec) #

    def scale_data(self, scale_factor): #
        self._apply_batch_operation(lambda val, factor=scale_factor: val * factor) #

    def _apply_batch_operation(self, operation_func): #
        if not self.data_manager.is_connected(): #
            QMessageBox.warning(self, "Not Connected", "Please connect to a data source first.") #
            return #

        data_def = self.definition #
        data_block_length = data_def["data_rows"] * data_def["data_cols"] * data_def["data_element_size"] #
        
        # Read the entire data block
        current_data_raw_bytes = self.data_manager.read_data(data_def["data_address"], data_block_length) #

        if not current_data_raw_bytes: #
            QMessageBox.critical(self, "Read Error", "Failed to read current data from ECU/RAM dump.") #
            return #

        # Convert to a mutable bytearray for easier manipulation
        modified_data_bytes = bytearray(current_data_raw_bytes) #
        
        self.table.blockSignals(True) # Block signals during batch update #

        try:
            for r in range(data_def["data_rows"]): #
                for c in range(data_def["data_cols"]): #
                    # Calculate offset within the block
                    offset_in_block = (r * data_def["data_cols"] + c) * data_def["data_element_size"] #
                    
                    # Extract raw bytes for this cell
                    cell_raw_bytes = modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]] #
                    
                    # Convert to integer and then to scaled float
                    raw_val = int.from_bytes(cell_raw_bytes, 'big', signed=False) #
                    scaled_val = self._convert_to_scaled(raw_val, data_def["data_scale"], data_def["data_offset"]) #
                    
                    # Apply the operation
                    new_scaled_val = operation_func(scaled_val) #
                    
                    # Convert back to raw bytes
                    new_raw_bytes_for_cell = self._convert_to_raw( #
                        new_scaled_val, #
                        data_def["data_reverse_scale"], #
                        data_def["data_reverse_offset"], #
                        data_def["data_element_size"] #
                    ) #
                    
                    # Update the bytearray
                    modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]] = new_raw_bytes_for_cell #

                    # Update the QTableWidgetItem (display only, no signal emitted)
                    item = self.table.item(r, c) #
                    if item: #
                        item.setText(f"{new_scaled_val:.2f}") #
                    else:
                        item = QTableWidgetItem(f"{new_scaled_val:.2f}") #
                        self.table.setItem(r, c, item) #
                    # Update internal min/max for coloring
                    self._update_min_max_data_values(new_scaled_val) #

            # Write the entire modified block back to the data source
            if self.data_manager.write_data(data_def["data_address"], bytes(modified_data_bytes)): #
                QMessageBox.information(self, "Success", "Map data updated successfully.") #
                self._apply_color_gradient() # Reapply gradient after successful write #
                self.table.viewport().update() # Force repaint #
            else:
                QMessageBox.critical(self, "Write Error", #
                                     f"Failed to write batch changes to data source at address 0x{data_def['data_address']:X}.") #
                # Re-load data if write failed to revert to original state
        finally:
            self.table.blockSignals(False) #

    def update_cursor_position(self):
        # Dynamic selection of cursor axes based on maptable units
        x_axis_unit = self.definition["units"].get("x_axis")
        y_axis_unit = self.definition["units"].get("y_axis")

        # Find the gauge definitions based on the units specified for this maptable
        x_axis_gauge_def = next((d for d in ECU_DEFINITIONS if d["description"] == x_axis_unit and d["type"] == "gauge_bar"), None)
        y_axis_gauge_def = next((d for d in ECU_DEFINITIONS if d["description"] == y_axis_unit and d["type"] == "gauge_bar"), None)

        if not self.data_manager.is_connected() or not x_axis_gauge_def or not y_axis_gauge_def:
            self.rpm_value = None # This will effectively be self.x_axis_cursor_value
            self.load_value = None # This will effectively be self.y_axis_cursor_value
            self.table.viewport().update()
            return

        try:
            raw_x_axis_bytes = self.data_manager.read_data(x_axis_gauge_def["address"], x_axis_gauge_def["length"])
            if raw_x_axis_bytes and len(raw_x_axis_bytes) == x_axis_gauge_def["length"]:
                int_x_axis_value = int.from_bytes(raw_x_axis_bytes, byteorder='big', signed=False)
                self.rpm_value = (int_x_axis_value * x_axis_gauge_def.get("scale", 1.0)) + x_axis_gauge_def.get("offset", 0)
            else:
                self.rpm_value = None
                print(f"Warning: Could not read {x_axis_unit} for cursor or raw_x_axis_bytes is invalid.")

            raw_y_axis_bytes = self.data_manager.read_data(y_axis_gauge_def["address"], y_axis_gauge_def["length"])
            if raw_y_axis_bytes and len(raw_y_axis_bytes) == y_axis_gauge_def["length"]:
                int_y_axis_value = int.from_bytes(raw_y_axis_bytes, byteorder='big', signed=False)
                self.load_value = (int_y_axis_value * y_axis_gauge_def.get("scale", 1.0)) + y_axis_gauge_def.get("offset", 0)
            else:
                self.load_value = None
                print(f"Warning: Could not read {y_axis_unit} for cursor or raw_y_axis_bytes is invalid.")

            self.table.viewport().update()

        except Exception as e:
            print(f"Error updating cursor position: {e}")
            self.rpm_value = None
            self.load_value = None
            self.table.viewport().update()

    def draw_cursor(self, painter):
        if self.rpm_value is None or self.load_value is None or \
           not self.x_axis_values or not self.y_axis_values:
            return

        painter.setRenderHint(QPainter.Antialiasing)

        if self.table.rowCount() == 0 or self.table.columnCount() == 0:
            return

        first_cell_item = self.table.item(0, 0)
        if not first_cell_item:
            return

        first_cell_rect = self.table.visualItemRect(first_cell_item)
        if not first_cell_rect:
            return

        table_width = sum(self.table.columnWidth(c) for c in range(self.table.columnCount()))
        table_height = sum(self.table.rowHeight(r) for r in range(self.table.rowCount()))

        content_rect = QRect(first_cell_rect.left(), first_cell_rect.top(), table_width, table_height)

        # Calculate X-axis position
        x_pos_in_cells = 0.0
        if len(self.x_axis_values) > 1:
            idx1 = -1
            for i in range(len(self.x_axis_values) - 1):
                if self.x_axis_values[i] <= self.rpm_value <= self.x_axis_values[i+1]:
                    idx1 = i
                    break

            if idx1 == -1:
                if self.rpm_value < self.x_axis_values[0]:
                    x_pos_in_cells = 0.0
                else:
                    x_pos_in_cells = float(len(self.x_axis_values) - 1)
            else:
                idx2 = idx1 + 1
                val1 = self.x_axis_values[idx1]
                val2 = self.x_axis_values[idx2]

                if val2 != val1:
                    interpolation_factor = (self.rpm_value - val1) / (val2 - val1)
                    x_pos_in_cells = float(idx1) + interpolation_factor
                else:
                    x_pos_in_cells = float(idx1)
        elif len(self.x_axis_values) == 1:
            x_pos_in_cells = 0.0
        else:
            print("DEBUG: No X-axis values. Cannot calculate X position.")
            return


        # Calculate Y-axis position
        y_pos_in_cells = 0.0
        if len(self.y_axis_values) > 1:
            idx1 = -1
            for i in range(len(self.y_axis_values) - 1):
                if self.y_axis_values[i] <= self.load_value <= self.y_axis_values[i+1]:
                    idx1 = i
                    break

            if idx1 == -1:
                if self.load_value < self.y_axis_values[0]:
                    y_pos_in_cells = 0.0
                else:
                    y_pos_in_cells = float(len(self.y_axis_values) - 1)
            else:
                idx2 = idx1 + 1
                val1 = self.y_axis_values[idx1]
                val2 = self.y_axis_values[idx2]

                if val1 != val2:
                    interpolation_factor = (self.load_value - val1) / (val2 - val1)
                    y_pos_in_cells = float(idx1) + interpolation_factor
                else:
                    y_pos_in_cells = float(idx1)
        elif len(self.y_axis_values) == 1:
            y_pos_in_cells = 0.0
        else:
            print("DEBUG: No Y-axis values. Cannot calculate Y position.")
            return

        col_idx_int = int(math.floor(x_pos_in_cells))
        # Ensure col_idx_int is within valid column range
        col_idx_int = max(0, min(col_idx_int, self.table.columnCount() - 1))
        col_width = self.table.columnWidth(col_idx_int)
        x_start_pixel_of_cell = self.table.columnViewportPosition(col_idx_int)
        col_fraction = x_pos_in_cells - col_idx_int
        x_line_pixel = x_start_pixel_of_cell + col_width * col_fraction

        row_idx_int = int(math.floor(y_pos_in_cells))
        # Ensure row_idx_int is within valid row range
        row_idx_int = max(0, min(row_idx_int, self.table.rowCount() - 1))
        row_height = self.table.rowHeight(row_idx_int)
        y_start_pixel_of_cell = self.table.rowViewportPosition(row_idx_int)
        row_fraction = y_pos_in_cells - row_idx_int
        y_line_pixel = y_start_pixel_of_cell + row_height * row_fraction

        x_line_pixel = max(content_rect.left(), min(x_line_pixel, content_rect.right()))
        y_line_pixel = max(content_rect.top(), min(y_line_pixel, content_rect.bottom()))

        # Draw cursor lines first
        painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(int(x_line_pixel), content_rect.top(), int(x_line_pixel), content_rect.bottom())

        painter.drawLine(content_rect.left(), int(y_line_pixel), content_rect.right(), int(y_line_pixel))

        # Highlight the cell at the intersection
        primary_col_idx = int(math.floor(x_pos_in_cells))
        primary_row_idx = int(math.floor(y_pos_in_cells))

        # Clamp to valid table bounds for the single cell
        primary_col_idx = max(0, min(primary_col_idx, self.table.columnCount() - 1))
        primary_row_idx = max(0, min(primary_row_idx, self.table.rowCount() - 1))

        item = self.table.item(primary_row_idx, primary_col_idx)
        if item and item.text() not in ("N/A", "Error"):
            cell_rect = self.table.visualItemRect(item)

            painter.save()
            painter.setPen(QPen(QColor(255, 0, 0), 4))
            highlight_color_fill = QColor(255, 255, 255, 250)
            painter.setBrush(QBrush(highlight_color_fill))

            painter.drawRect(cell_rect)

            # Draw the cell text on top
            font = item.font() if item else painter.font()
            painter.setFont(font)
            text_color = QColor(0, 0, 0)
            painter.setPen(QPen(text_color))
            painter.drawText(cell_rect, Qt.AlignCenter | Qt.TextSingleLine, item.text())

            painter.restore()

class MockDataManager:
    def __init__(self, is_connected=True):
        self._connected = is_connected
        self._data_store = {}  # {address: bytearray}

    def is_connected(self):
        return self._connected

    def read_data(self, address, length):
        result = bytearray()

        for i in range(length):
            addr = address + i
            if addr in self._data_store:
                result.append(self._data_store[addr])
            else:
                result.append(i % 256)
        
        return bytes(result)

    def write_data(self, address, data):
        for i, byte in enumerate(data):
            self._data_store[address + i] = byte
        
        print(f"Mock: Writing {len(data)} bytes to address {hex(address)}")
        return True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.gauges = {}
        self.tables = {}
        self.maptables = {}
        self.ordered_maptable_widgets = []
        self.current_maptable_widget = None

        self.is_logging = False
        self.log_file = None
        self.log_writer = None
        self.log_header_written = False

        self.setWindowTitle("ECU Tuner - T6e")
        self.setGeometry(100, 100, 1000, 700)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_gui_data)

        self.init_ui()
        self.show_data_source_dialog()

    def init_ui(self):
        print("--- Initializing UI ---")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        control_bar = QHBoxLayout()
        self.reconnect_button = QPushButton("Reconnect Source")
        self.reconnect_button.clicked.connect(self.show_data_source_dialog)
        control_bar.addWidget(self.reconnect_button)

        # Logging button
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self._toggle_logging)
        self.log_button.setStyleSheet("background-color: lightgray;")
        control_bar.addWidget(self.log_button)

        control_bar.addStretch() 

        # Elements for maptable cell manipulation
        self.manipulation_layout = QHBoxLayout()
        
        self.value_input = QLineEdit("0.5")
        self.value_input.setValidator(QDoubleValidator()) # Allow only double values
        self.value_input.setFixedWidth(50)
        self.manipulation_layout.addWidget(QLabel("Value:"))
        self.manipulation_layout.addWidget(self.value_input)

        self.inc_button = QPushButton("Inc +")
        self.inc_button.clicked.connect(lambda: self._adjust_maptable_cells("increment"))
        self.manipulation_layout.addWidget(self.inc_button)

        self.dec_button = QPushButton("Dec -")
        self.dec_button.clicked.connect(lambda: self._adjust_maptable_cells("decrement"))
        self.manipulation_layout.addWidget(self.dec_button)

        self.scale_button = QPushButton("Scale *")
        self.scale_button.clicked.connect(lambda: self._adjust_maptable_cells("scale"))
        self.manipulation_layout.addWidget(self.scale_button)

        control_bar.addStretch()
        control_bar.addLayout(self.manipulation_layout)

        main_layout.addLayout(control_bar)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        print(f"QTabWidget created and added to main layout.")

        # Connect the 'tab changed' signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.gauge_tab_widget = QWidget()
        self.gauge_layout = QGridLayout(self.gauge_tab_widget) 
        self.gauge_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.tab_widget.addTab(self.gauge_tab_widget, "Gauges")
        print(f"Added 'Gauges' tab. Current tab count: {self.tab_widget.count()}")

        self.table_tab_widget = QWidget()
        self.table_layout = QVBoxLayout(self.table_tab_widget)
        self.tab_widget.addTab(self.table_tab_widget, "Tables")
        print(f"Added 'Tables' tab. Current tab count: {self.tab_widget.count()}")

        first_maptable_tab_index = -1

        print("\n--- Populating tabs from ECU_DEFINITIONS ---")
        
        gauge_row = 0
        gauge_col = 0
        max_gauges_per_row = 8

        for i, definition in enumerate(ECU_DEFINITIONS):
            print(f"Processing definition {i}: Description='{definition.get('description', 'N/A')}', Type='{definition.get('type', 'N/A')}'")

            if definition["type"] in ["gauge_bar", "gauge_chart"]:
                gauge = GaugeWidget(
                    definition["description"],
                    definition["unit"],
                    definition["min_val"],
                    definition["max_val"],
                    definition["type"]
                )
                self.gauges[definition["description"]] = gauge
                self.gauge_layout.addWidget(gauge, gauge_row, gauge_col)
                gauge_col += 1
                if gauge_col >= max_gauges_per_row:
                    gauge_col = 0
                    gauge_row += 1
                print(f"  - Added Gauge: {definition['description']} (Type: {definition['type']})")

            elif definition["type"] == "table":
                table = QTableWidget(1, len(definition["columns"]))
                table.setHorizontalHeaderLabels(definition["columns"])
                table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                table.verticalHeader().setVisible(False)
                table.setEditTriggers(QTableWidget.NoEditTriggers)
                table.setFixedSize(600, 60)
                self.tables[definition["description"]] = table
                
                table_group_box = QVBoxLayout()
                table_title = QLabel(definition["description"])
                table_title.setAlignment(Qt.AlignCenter)
                table_title.setFont(QFont("Arial", 12, QFont.Bold))
                table_group_box.addWidget(table_title)
                table_group_box.addWidget(table)
                self.table_layout.addLayout(table_group_box)
                print(f"  - Added Read-Only Table: {definition['description']}")

            elif definition["type"] == "maptable":
                try:
                    maptable_widget = MapTableWidget(definition, self.data_manager)
                    self.maptables[definition["description"]] = maptable_widget
                    self.ordered_maptable_widgets.append(maptable_widget)
                    tab_index = self.tab_widget.addTab(maptable_widget, definition["description"])
                    print(f"  - Added MAPTABLE '{definition['description']}' to tab index: {tab_index}. Total tabs now: {self.tab_widget.count()}")

                    if first_maptable_tab_index == -1:
                        first_maptable_tab_index = tab_index
                        print(f"  - Set '{definition['description']}' as first maptable tab index.")
                except Exception as e:
                    print(f"  - ERROR: Failed to create/add MapTableWidget for '{definition.get('description', 'N/A')}': {e}")


        print("\n--- Finalizing Tab Selection ---")
        if first_maptable_tab_index != -1:
            self.tab_widget.setCurrentIndex(first_maptable_tab_index)
            print(f"Set current tab to the first maptable at index: {first_maptable_tab_index}")
        else:
            self.tab_widget.setCurrentIndex(0)
            print(f"No maptables found, setting current tab to 'Gauges' (index 0).")
        
        self._on_tab_changed(self.tab_widget.currentIndex()) 

        print(f"Final current tab index: {self.tab_widget.currentIndex()}")
        print("--- UI Initialization Complete ---")

    def _adjust_maptable_cells(self, operation_type):
        self._on_tab_changed(self.tab_widget.currentIndex())

        print(f"DEBUG: Adjusting map: {self.current_maptable_widget.definition['description'] if self.current_maptable_widget else 'None'}")
        if not self.current_maptable_widget:
            QMessageBox.warning(self, "No Map Selected", "Please select a map to adjust cells.")
            return

        current_maptable = self.current_maptable_widget
        data_def = current_maptable.definition

        selected_ranges = current_maptable.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "No Cells Selected", "Please select cells to adjust.")
            return

        try:
            total_data_length = data_def["data_rows"] * data_def["data_cols"] * data_def["data_element_size"]
            current_data_bytes = bytearray(current_maptable.data_manager.read_data(data_def["data_address"], total_data_length))

            if current_data_bytes is None or len(current_data_bytes) != total_data_length:
                QMessageBox.critical(self, "Read Error", f"Failed to read expected amount of data from 0x{data_def['data_address']:X}. Expected {total_data_length} bytes, got {len(current_data_bytes)}.")
                return

            try:
                raw_value = self.value_input.text()
                if not raw_value:
                    if operation_type == "scale":
                        adjustment_value = 1.0
                    else:
                        adjustment_value = 0.0
                else:
                    adjustment_value = float(raw_value)
            except ValueError:
                QMessageBox.warning(self, "Invalid Value", "Please enter a valid number for adjustment.")
                return    

            # Define operations
            if operation_type == "increment":
                operation_func = lambda x: x + adjustment_value
            elif operation_type == "decrement":
                operation_func = lambda x: x - adjustment_value
            elif operation_type == "scale":
                operation_func = lambda x: x * adjustment_value # Use the float value directly
            else:
                QMessageBox.warning(self, "Invalid Operation", "Unknown adjustment operation.")
                return

            modified_data_bytes = bytearray(current_data_bytes)
            # Store changes to apply visually after successful write
            changes_to_apply_visually = []

            for selected_range in selected_ranges:
                for r in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                    for c in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                        offset_in_block = (r * data_def["data_cols"] + c) * data_def["data_element_size"]

                        cell_raw_bytes = modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]]

                        # Re-read raw bytes from memory for each cell
                        true_address = data_def["data_address"] + offset_in_block
                        live_cell_bytes = current_maptable.data_manager.read_data(true_address, data_def["data_element_size"])
                        if not live_cell_bytes or len(live_cell_bytes) != data_def["data_element_size"]:
                            continue  # skip this cell
                        raw_val = int.from_bytes(live_cell_bytes, 'big', signed=False)
                        current_scaled_val = current_maptable._convert_to_scaled(raw_val, data_def["data_scale"], data_def["data_offset"])


                        new_scaled_val = operation_func(current_scaled_val)
                        
                        new_raw_bytes_for_cell = current_maptable._convert_to_raw(
                            new_scaled_val,
                            data_def["data_reverse_scale"],
                            data_def["data_reverse_offset"],
                            data_def["data_element_size"]
                        )

                        # Update the bytearray that will be written
                        modified_data_bytes[offset_in_block : offset_in_block + data_def["data_element_size"]] = new_raw_bytes_for_cell
                        
                        # Store the visual change for later application
                        changes_to_apply_visually.append((r, c, new_scaled_val))

            current_maptable.table.blockSignals(True) # Block signals during batch update

            # Write the entire modified block back to the data source
            if current_maptable.data_manager.write_data(data_def["data_address"], bytes(modified_data_bytes)):
                
                # Apply changes visually directly to the cells in the UI
                for r, c, val in changes_to_apply_visually:
                    item = current_maptable.table.item(r, c)
                    if item:
                        item.setText(f"{val:.2f}")
                    else: # This case should ideally not happen if table is correctly initialized
                        item = QTableWidgetItem(f"{val:.2f}")
                        item.setTextAlignment(Qt.AlignCenter)
                        current_maptable.table.setItem(r, c, item)

                current_maptable._apply_color_gradient() # Reapply gradient after successful write
                current_maptable.table.repaint() # Ensure immediate repaint of the affected table
            else:
                QMessageBox.critical(self, "Write Error", f"Failed to write batch changes to data source at address 0x{data_def['data_address']:X}.")
                # If write failed, reload the table from the data_manager to show actual state (revert changes)
                current_maptable._load_and_display_map_data()
                current_maptable._apply_color_gradient() 
                current_maptable.table.repaint()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during map adjustment: {e}")
        finally:
            current_maptable.table.blockSignals(False)
            current_maptable.table.viewport().update()

    def show_data_source_dialog(self):
        dialog = DataSourceDialog(self.data_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            
            if dialog.source_type == "RAM":
                connection_successful = self.data_manager.connect_source(
                    "mock_can",
                    ram_dump_path=dialog.ram_dump_path
                )
            elif dialog.source_type == "CAN":
                connection_successful = self.data_manager.connect_source(
                    "real_can",
                    interface=dialog.can_interface,
                    channel=dialog.can_channel,
                    bitrate=dialog.can_bitrate
                )
            else:
                connection_successful = False 

            if connection_successful:
                self.reconnect_button.setText("Connected")
                self.reconnect_button.setStyleSheet("background-color: lightgray;")
                self.reconnect_button.setEnabled(False)
                self.update_all_maptables()
                
                if not self.timer.isActive():
                    self.timer.start()
            else:
                self.reconnect_button.setText("Reconnect Source")
                self.reconnect_button.setEnabled(True)

                if self.timer.isActive(): 
                    self.timer.stop()
        else: 

            self.reconnect_button.setText("Reconnect Source")
            self.reconnect_button.setEnabled(True)
            
            if self.timer.isActive():
                self.timer.stop()
            
            if self.data_manager.is_connected():
                self.data_manager.disconnect_source() 
                print("Disconnected source due to dialog cancellation.")

    def update_all_maptables(self):
        print("Main Window: Forcing reload of all maptables.")
        for maptable_widget in self.maptables.values():
            maptable_widget._load_and_display_map_data()

    def _on_tab_changed(self, index):
        current_widget = self.tab_widget.widget(index)
        
        if isinstance(current_widget, MapTableWidget):
            self.current_maptable_widget = current_widget
            print(f"DEBUG: Switched to tab {index}. Current MapTableWidget set to: {self.current_maptable_widget.definition['description']}")
        else:
            self.current_maptable_widget = None
            print(f"DEBUG: Switched to tab {index} (not a MapTableWidget). Current MapTableWidget set to None.")

    def _get_next_log_filename(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        base_filename = "gauge_log"
        extension = ".csv"
        i = 1
        while True:
            filename = os.path.join(log_dir, f"{base_filename}_{i:03d}{extension}")
            if not os.path.exists(filename):
                return filename
            i += 1

    def _toggle_logging(self):
        if not self.data_manager.is_connected():
            QMessageBox.warning(self, "Logging Error", "Cannot start logging: No data source connected.")
            return

        if self.is_logging:
            # Stop logging
            self.is_logging = False
            self.log_button.setText("Start Logging")
            self.log_button.setStyleSheet("background-color: lightgray;")
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.log_writer = None
            self.log_header_written = False
            print("Logging stopped.")
        else:
            # Start logging
            try:
                log_filename = self._get_next_log_filename()
                self.log_file = open(log_filename, 'w', newline='')
                self.log_writer = csv.writer(self.log_file)
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.log_button.setStyleSheet("background-color: lightgreen;")
                print(f"Logging started to: {log_filename}")
            except IOError as e:
                QMessageBox.critical(self, "Logging Error", f"Failed to open log file: {e}")
                self.is_logging = False
                self.log_button.setText("Start Logging")
                self.log_button.setStyleSheet("background-color: lightgray;")

    def update_gui_data(self):
        if not self.data_manager.is_connected():
            return

        gauge_values = {}  # Stores processed (scaled/calculated) values for all gauges.
                        # Keys will be 'DESCRIPTION_VALUE' (e.g., 'RPM_VALUE').
                        # Used for display, logging, and as dependencies for other calculations.
        raw_gauge_values = {}  # Stores raw integer values directly from the ECU.
                            # Keys will be 'DESCRIPTION_RAW' (e.g., 'RPM_RAW', 'MAF_RAW').

        # Pass 1: Read raw data for ALL definitions with an address and process simple gauges
        # This pass is crucial for populating 'raw_gauge_values' which might be used by calculated gauges in the second pass, and for updating simple gauges.
        for definition in ECU_DEFINITIONS: # ECU_DEFINITIONS is accessible from lib/ecu_definitions.py
            description = definition.get("description", "Unknown")

            if "address" not in definition or "length" not in definition:
                continue # Skip definitions that are not direct sensor readings (e.g., just calculated ones)

            try:
                # Read raw bytes from the ECU via the data manager
                raw_bytes = self.data_manager.read_data(definition["address"], definition["length"])

                if raw_bytes is None or len(raw_bytes) != definition["length"]:
                    print(f"Warning: Could not read {definition.get('length')} bytes for '{description}'. Length mismatch or None. Skipping raw data for this definition.")
                    raw_gauge_values.pop(f"{description}_RAW", None)
                    if definition.get("type") in ["gauge_bar", "gauge_chart"] and "calculation" not in definition:
                        gauge_values.pop(f"{description}_VALUE", None)
                    continue

                int_value = int.from_bytes(raw_bytes, byteorder='big', signed=False)

                # Store the raw integer value. This is critical for formulas using _RAW (like MAF_RAW).
                raw_gauge_values[f"{description}_RAW"] = int_value

                # If this is a simple gauge (not calculated), apply its scale/offset and update its display.
                if definition.get("type") in ["gauge_bar", "gauge_chart"] and "calculation" not in definition:
                    scale = definition.get("scale", 1.0)
                    offset = definition.get("offset", 0)
                    scaled_value = (int_value * scale) + offset

                    # Store scaled value using the convention 'DESCRIPTION_VALUE'
                    gauge_values[f"{description}_VALUE"] = scaled_value

                    # Update the GUI display object for this simple gauge
                    gauge_display_object = self.gauges.get(description)
                    if gauge_display_object:
                        gauge_display_object.set_value(scaled_value)
                    else:
                        print(f"Warning: Gauge display object for '{description}' not found in self.gauges during Pass 1.")

            except Exception as e:
                print(f"Error processing simple gauge '{description}' data in Pass 1: {e}")
                # Ensure values are cleared if an error occurs during reading/scaling
                raw_gauge_values.pop(f"{description}_RAW", None)
                gauge_values.pop(f"{description}_VALUE", None)
                gauge_display_object = self.gauges.get(description)
                if gauge_display_object:
                    gauge_display_object.set_value("N/A") # Show N/A on GUI for error

        # Pass 2: Process calculated gauges
        # This pass uses values gathered in Pass 1 (both raw_gauge_values and gauge_values) to perform calculations for gauges with a 'calculation' block.
        for definition in ECU_DEFINITIONS:
            # Only process gauge types that have a 'calculation' block
            if definition.get("type") in ["gauge_bar", "gauge_chart"] and "calculation" in definition:
                description = definition.get("description", "Unknown Calculated Gauge")
                try:
                    calculation_info = definition["calculation"]
                    calculation_type = calculation_info.get("type")

                    if calculation_type == "formula":
                        formula_string = calculation_info.get("formula_string")
                        dependencies = calculation_info.get("dependencies", [])

                        if not formula_string:
                            print(f"Error: Calculated gauge '{description}' has no 'formula_string'. Skipping.")
                            continue # Skip if formula string is missing

                        formula_scope = {} # This will hold variables available to eval()
                        all_dependencies_met = True # Flag to track if all needed dependencies are found/numeric

                        # 1. Add fixed parameters from the calculation block (e.g., num_cylinders)
                        for key, value in calculation_info.items():
                            if key not in ["type", "formula_string", "dependencies"]:
                                formula_scope[key] = value

                        # 2. Populate scope with dependency values (both scaled '_VALUE' and raw '_RAW')
                        for dep_desc in dependencies:
                            # Attempt to add scaled/processed value (e.g., 'RPM_VALUE')
                            value_key = f"{dep_desc}_VALUE"
                            if value_key in gauge_values and gauge_values[value_key] is not None:
                                formula_scope[value_key] = gauge_values[value_key]
                            elif f"{dep_desc}_VALUE" in formula_string: # If formula explicitly uses _VALUE but it's not present
                                print(f"Error updating calculated gauge '{description}': Missing or None dependency: '{value_key}'. Formula: '{formula_string}'")
                                all_dependencies_met = False
                                break

                            # Attempt to add raw value (e.g., 'MAF_RAW')
                            raw_key = f"{dep_desc}_RAW"
                            if raw_key in raw_gauge_values and raw_gauge_values[raw_key] is not None:
                                formula_scope[raw_key] = raw_gauge_values[raw_key]
                            elif f"{dep_desc}_RAW" in formula_string: # If formula explicitly uses _RAW but it's not present
                                print(f"Error updating calculated gauge '{description}': Missing or None dependency: '{raw_key}'. Formula: '{formula_string}'")
                                all_dependencies_met = False
                                break
                        
                        if not all_dependencies_met:
                            # Set gauge to an error state if dependencies are missing
                            gauge_display_object = self.gauges.get(description)
                            if gauge_display_object:
                                gauge_display_object.set_value("N/A")
                            gauge_values.pop(f"{description}_VALUE", None) # Ensure log reflects error
                            continue # Skip current calculation

                        # 3. Final check: Ensure all variable names in the formula string are in the scope
                        # This uses regex to find all potential variable names in the formula string
                        required_vars_in_formula = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', formula_string))
                        
                        # Remove any variables that are already in formula_scope from fixed parameters or dependencies
                        required_vars_in_formula = {v for v in required_vars_in_formula if v not in formula_scope}
                        
                        for var_name in required_vars_in_formula:
                            if var_name not in formula_scope:
                                print(f"Error updating calculated gauge '{description}': Variable '{var_name}' from formula is not in scope. Formula: '{formula_string}', Scope: {formula_scope}")
                                all_dependencies_met = False
                                break
                        
                        if not all_dependencies_met:
                            gauge_display_object = self.gauges.get(description)
                            if gauge_display_object:
                                gauge_display_object.set_value("N/A")
                            gauge_values.pop(f"{description}_VALUE", None)
                            continue

                        # 4. Type conversion for safety before evaluation
                        for key, value in list(formula_scope.items()):
                            if isinstance(value, (int, float)):
                                continue
                            try:
                                formula_scope[key] = float(value)
                            except (ValueError, TypeError):
                                print(f"Error: Could not convert '{key}' value '{value}' to number for '{description}' calculation. Setting to N/A.")
                                all_dependencies_met = False
                                break

                        if not all_dependencies_met:
                            gauge_display_object = self.gauges.get(description)
                            if gauge_display_object:
                                gauge_display_object.set_value("N/A")
                            gauge_values.pop(f"{description}_VALUE", None)
                            continue

                        # Perform the calculation
                        # Using {"__builtins__": None} for security to restrict eval's access to Python builtins.
                        calculated_value = eval(formula_string, {"__builtins__": None}, formula_scope)

                        # Update the GUI display object for this calculated gauge
                        gauge_display_object = self.gauges.get(description)
                        if gauge_display_object:
                            gauge_display_object.set_value(calculated_value)
                        else:
                            print(f"Warning: Gauge display object for calculated gauge '{description}' not found in self.gauges.")

                        # Store the final calculated value
                        gauge_values[f"{description}_VALUE"] = calculated_value

                except Exception as e:
                    # Catch errors during the calculation process
                    print(f"Critical Error updating calculated gauge '{description}': {e}. Formula String: '{formula_string}', Scope: {formula_scope}")
                    gauge_display_object = self.gauges.get(description)
                    if gauge_display_object:
                        gauge_display_object.set_value("ERROR") # Indicate a calculation error on GUI
                    gauge_values.pop(f"{description}_VALUE", None) # Remove value from logging if calculation failed


        # Process tables
        for definition in ECU_DEFINITIONS:
            if definition.get("type") == "table":
                description = definition.get("description", "Unknown Table")
                try:
                    if "address" not in definition or "length" not in definition:
                        print(f"Warning: Table '{description}' definition missing address or length. Skipping.")
                        continue

                    raw_bytes = self.data_manager.read_data(definition["address"], definition["length"])
                    if raw_bytes is None or len(raw_bytes) != definition["length"]:
                        print(f"Warning: Could not read data for table '{description}'. Length mismatch or None.")
                        continue

                    table = self.tables.get(description)
                    if table and "columns" in definition:
                        element_size = definition.get("element_size", 1)

                        definition_scale = definition.get("scale", 1.0)
                        definition_offset = definition.get("offset", 0)

                        for col_idx, i in enumerate(range(0, definition["length"], element_size)):
                            if i + element_size <= len(raw_bytes):
                                element_bytes = raw_bytes[i : i + element_size]
                                element_int_val = int.from_bytes(element_bytes, byteorder='big', signed=False)

                                current_offset = definition_offset
                                if isinstance(definition_offset, list):
                                    if col_idx < len(definition_offset):
                                        current_offset = definition_offset[col_idx]
                                    else:
                                        print(f"Warning: Offset list too short for column {col_idx} in '{description}'. Using default 0 offset.")
                                        current_offset = 0

                                element_scaled_val = (element_int_val * definition_scale) + current_offset

                                display_unit = definition.get("unit", "")
                                display_string = ""
                                if description == "Ignition Timing":
                                    display_string = f"{-element_scaled_val:.1f}{display_unit}"
                                else:
                                    display_string = f"{element_scaled_val:.1f} {display_unit}"

                                item = QTableWidgetItem(display_string)
                                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                                table.setItem(0, col_idx, item)
                            else:
                                table.setItem(0, col_idx, QTableWidgetItem("N/A"))
                                table.item(0, col_idx).setFlags(table.item(0, col_idx).flags() & ~Qt.ItemIsEditable)

                except Exception as e:
                    print(f"Error updating table '{description}': {e}")


        # Update map table cursor
        if self.current_maptable_widget and self.data_manager.is_connected():
            self.current_maptable_widget.update_cursor_position()

        # Log gauge data if logging is active
        if self.is_logging and self.log_writer:
            if not self.log_header_written:
                log_header = ["Timestamp"]
                for def_item in ECU_DEFINITIONS:
                    if def_item.get("type") in ["gauge_bar", "gauge_chart"]:
                        log_header.append(def_item["description"]) # Log by original description name
                self.log_writer.writerow(log_header)
                self.log_header_written = True

            row_data = [time.time()]
            for def_item in ECU_DEFINITIONS:
                if def_item.get("type") in ["gauge_bar", "gauge_chart"]:
                    # Retrieve the value by its 'DESCRIPTION_VALUE' key
                    # If not found (e.g., due to calculation error), log 'N/A'
                    value_to_log = gauge_values.get(f"{def_item['description']}_VALUE")
                    if value_to_log is not None:
                        row_data.append(f"{value_to_log:.2f}")
                    else:
                        row_data.append("N/A")
            self.log_writer.writerow(row_data)

    def closeEvent(self, event):
        print("Closing application...")
        if self.timer.isActive():
            self.timer.stop() 

        # Stop logging and close file if active
        if self.is_logging:
            self._toggle_logging() # This will stop logging and close the file

        self.data_manager.shutdown()
        
        event.accept()

if __name__ == '__main__':
    if not os.path.exists('ram'):
        os.makedirs('ram')
        with open('ram/calram.bin', 'wb') as f:
            f.write(os.urandom(2048))
        print("Created dummy ram/calram.bin for testing.")

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())