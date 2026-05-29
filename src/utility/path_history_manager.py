"""
Path History Manager - Handles storage and retrieval of rover path data
Saves path history to files for persistence and analysis
"""

import json
import os
from datetime import datetime
from pathlib import Path


class PathHistoryManager:
    """Manages rover path history storage and retrieval"""

    def __init__(self, storage_dir="./path_history"):
        """
        Initialize path history manager
        
        Args:
            storage_dir: Directory to store path history files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = None
        self.session_data = None

    def start_new_session(self, session_name=None):
        """
        Start a new recording session
        
        Args:
            session_name: Optional name for the session, defaults to timestamp
        """
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.current_session = session_name
        self.session_data = {
            "session_name": session_name,
            "start_time": datetime.now().isoformat(),
            "path_points": [],
            "waypoints": [],
            "events": []
        }

    def add_gps_point(self, lat, lon, timestamp=None):
        """
        Add a GPS point to current session
        
        Args:
            lat: Latitude
            lon: Longitude
            timestamp: Optional timestamp, defaults to now
        """
        if self.session_data is None:
            self.start_new_session()

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        self.session_data["path_points"].append({
            "lat": float(lat),
            "lon": float(lon),
            "timestamp": timestamp
        })

    def add_waypoint(self, waypoint_id, lat, lon, timestamp=None):
        """
        Add a waypoint marker to session
        
        Args:
            waypoint_id: ID of the waypoint
            lat: Latitude
            lon: Longitude
            timestamp: Optional timestamp
        """
        if self.session_data is None:
            self.start_new_session()

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        self.session_data["waypoints"].append({
            "id": waypoint_id,
            "lat": float(lat),
            "lon": float(lon),
            "timestamp": timestamp
        })

    def add_event(self, event_type, description, timestamp=None):
        """
        Add an event marker (e.g., 'waypoints_assigned', 'arrival_at_waypoint')
        
        Args:
            event_type: Type of event
            description: Event description
            timestamp: Optional timestamp
        """
        if self.session_data is None:
            self.start_new_session()

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        self.session_data["events"].append({
            "type": event_type,
            "description": description,
            "timestamp": timestamp
        })

    def save_session(self):
        """Save current session to file"""
        if self.session_data is None:
            return None

        self.session_data["end_time"] = datetime.now().isoformat()
        
        # Calculate statistics
        if len(self.session_data["path_points"]) > 1:
            # Calculate total distance traveled
            total_distance = self._calculate_distance(
                self.session_data["path_points"]
            )
            self.session_data["total_distance_m"] = total_distance
        
        filename = self.storage_dir / f"{self.current_session}_path.json"
        with open(filename, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        print(f"Path history saved: {filename}")
        return filename

    def get_session_summary(self):
        """Get summary of current session"""
        if self.session_data is None:
            return None

        return {
            "session_name": self.current_session,
            "path_points": len(self.session_data["path_points"]),
            "waypoints": len(self.session_data["waypoints"]),
            "events": len(self.session_data["events"])
        }

    def load_session(self, session_name):
        """
        Load a previous session
        
        Args:
            session_name: Name of session to load
        """
        filename = self.storage_dir / f"{session_name}_path.json"
        
        if not filename.exists():
            raise FileNotFoundError(f"Session file not found: {filename}")
        
        with open(filename, 'r') as f:
            self.session_data = json.load(f)
        self.current_session = session_name
        return self.session_data

    def list_sessions(self):
        """List all available sessions"""
        sessions = []
        for file in self.storage_dir.glob("*_path.json"):
            session_name = file.stem.replace("_path", "")
            sessions.append(session_name)
        return sorted(sessions)

    def export_to_csv(self, session_name=None, output_file=None):
        """
        Export path history to CSV format
        
        Args:
            session_name: Session to export (defaults to current)
            output_file: Output file path
        """
        if session_name is None:
            session_data = self.session_data
            session_name = self.current_session
        else:
            session_data = self.load_session(session_name)

        if output_file is None:
            output_file = self.storage_dir / f"{session_name}_path.csv"

        import csv
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Index", "Latitude", "Longitude", "Timestamp"])
            
            for idx, point in enumerate(session_data["path_points"]):
                writer.writerow([
                    idx,
                    point["lat"],
                    point["lon"],
                    point["timestamp"]
                ])

        print(f"Path history exported to CSV: {output_file}")
        return output_file

    def _calculate_distance(self, path_points):
        """Calculate total distance from path points"""
        from math import radians, cos, sin, sqrt, atan2

        if len(path_points) < 2:
            return 0

        total = 0
        for i in range(1, len(path_points)):
            lat1 = path_points[i-1]["lat"]
            lon1 = path_points[i-1]["lon"]
            lat2 = path_points[i]["lat"]
            lon2 = path_points[i]["lon"]

            R = 6371000  # Earth radius in meters
            p1, p2 = radians(lat1), radians(lat2)
            a = sin(radians(lat2-lat1)/2)**2 + cos(p1)*cos(p2)*sin(radians(lon2-lon1)/2)**2
            total += R * 2 * atan2(sqrt(a), sqrt(1-a))

        return total

    def get_path_statistics(self, session_name=None):
        """Get detailed statistics about a path"""
        if session_name is None:
            session_data = self.session_data
        else:
            session_data = self.load_session(session_name)

        if not session_data or not session_data["path_points"]:
            return None

        points = session_data["path_points"]
        lats = [p["lat"] for p in points]
        lons = [p["lon"] for p in points]

        return {
            "total_points": len(points),
            "total_distance_m": self._calculate_distance(points),
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "center_lat": sum(lats) / len(lats),
            "center_lon": sum(lons) / len(lons),
            "waypoints_count": len(session_data.get("waypoints", [])),
            "events_count": len(session_data.get("events", []))
        }
