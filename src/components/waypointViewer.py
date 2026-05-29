from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QSizePolicy, QHBoxLayout, QPushButton
from PyQt6.QtWidgets import QAbstractItemView


class WaypointViewer(QWidget):
    mission_pushed = pyqtSignal(dict)
    waypoint_data = pyqtSignal(list)
    def __init__(self):
        super().__init__()

        self.primary_selected = -1

        self.layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()

        self.table.setColumnCount(7)
        self.table.setRowCount(0)

        self.table.setHorizontalHeaderLabels(["WP#", "Control", "Type", "Latitude", "Longitude", "Altitude(m)", "Status"])
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.table_control = QHBoxLayout()

        self.remove_selected_button = QPushButton("Remove Selected")
        self.remove_selected_button.clicked.connect(self.remove_selected)

        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self.clear_all)

        self.push_mission_button = QPushButton("Push Mission")
        self.push_mission_button.clicked.connect(self.emit_mission_data)


        self.table_control.addStretch()
        self.table_control.addWidget(self.remove_selected_button)
        self.table_control.addWidget(self.clear_all_button)
        self.table_control.addWidget(self.push_mission_button)

        self.layout.addWidget(self.table)
        self.layout.addLayout(self.table_control)

    def update_status(self, data):
        try:
            mission_state = data["mission_state"]
        except Exception:
            mission_state = "N/A"

        if self.primary_selected >= 0:
            self.clear_all_status()
            self.table.setItem(self.primary_selected, 6, QTableWidgetItem(str(mission_state)))
        print(data)

    def add_waypoint(self, data_dict):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        self.table.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))

        self.table.setItem(row_position, 1, QTableWidgetItem(str(data_dict["control"])))

        self.table.setItem(row_position, 2, QTableWidgetItem(data_dict["waypoint_type"]))

        self.table.setItem(row_position, 3, QTableWidgetItem(data_dict["latitude"]))

        self.table.setItem(row_position, 4, QTableWidgetItem(data_dict["longitude"]))

        self.table.setItem(row_position, 5, QTableWidgetItem(data_dict["altitude"]))

        self.table.setItem(row_position, 6, QTableWidgetItem("NULL"))

    def remove_selected(self):
        current_row = self.table.currentRow()

        if current_row >= 0:
            self.table.removeRow(current_row)
            self.reindex_waypoints()

    def clear_all(self):
        self.table.setRowCount(0)

    def reindex_waypoints(self):
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

    def emit_mission_data(self):
        current_row = self.table.currentRow()
        self.primary_selected = current_row

        if current_row >= 0:
            wp_id = self.table.item(current_row, 0).text()
            control = self.table.item(current_row, 1).text()
            wp_type = self.table.item(current_row, 2).text()
            latitude = self.table.item(current_row, 3).text()
            longitude = self.table.item(current_row, 4).text()
            altitude = self.table.item(current_row, 5).text()

            waypoint_data = dict()
            waypoint_data["wp_id"] = wp_id
            waypoint_data["control"] = control
            waypoint_data["wp_type"] = wp_type
            waypoint_data["latitude"] = latitude
            waypoint_data["longitude"] = longitude
            waypoint_data["altitude"] = altitude

            self.clear_all_status()
            self.table.setItem(current_row, 6, QTableWidgetItem("PUSHED"))

            self.mission_pushed.emit(waypoint_data)
        else:
            # Optional: handle the case where no row is selected
            print("No waypoint selected to push!")

    def clear_all_status(self):
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 6, QTableWidgetItem("NULL"))

    def get_all_mission_data(self):
        print("Button is clicked")
        all_waypoints = []

        for row in range(self.table.rowCount()):
            waypoint = {
                "wp_id": self.table.item(row, 0).text(),
                "control": self.table.item(row, 1).text(),
                "wp_type": self.table.item(row, 2).text(),
                "latitude": self.table.item(row, 3).text(),
                "longitude": self.table.item(row, 4).text(),
                "altitude": self.table.item(row, 5).text(),
                "status": self.table.item(row, 6).text()
            }
            all_waypoints.append((waypoint['latitude'], waypoint['longitude']))

        self.waypoint_data.emit(all_waypoints)