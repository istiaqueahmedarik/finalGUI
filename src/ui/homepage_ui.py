from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from components.dashboardHeader import DashboardHeader
from ui.dashboard_ui import DashboardUI
from ui.staticmap_ui import StaticMapUI

class HomePageUI:
    def __init__(self):
        self.staticmap = None
        self.tabs = None
        self.dashboard = None

    def setup_ui(self, central_widget):
        layout = QVBoxLayout(central_widget)

        layout.addWidget(DashboardHeader())

        self.tabs = QTabWidget()
        
        self.dashboard = DashboardUI() 
        self.staticmap = StaticMapUI()
        
        self.tabs.addTab(self.dashboard, "Mission Dashboard")
        
        self.tabs.addTab(self.staticmap, "Map")

        layout.addWidget(self.tabs)
