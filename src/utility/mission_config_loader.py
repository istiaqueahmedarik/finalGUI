"""
Mission Configuration Loader
Loads mission coordinates from mission_config.json so you can easily
change locations without editing code.
"""

import json
import os
from pathlib import Path


def load_mission_coordinates():
    """
    Load mission coordinates from mission_config.json
    Returns: (latitude, longitude) tuple
    Defaults to Dhaka if config file not found
    """
    config_paths = [
        "mission_config.json",
        "../mission_config.json",
        os.path.join(os.path.dirname(__file__), "..", "mission_config.json"),
    ]
    
    default_lat = 23.837701697119773  # Dhaka default
    default_lon = 90.35928646267514
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    mission = config.get('mission', {})
                    lat = mission.get('latitude', default_lat)
                    lon = mission.get('longitude', default_lon)
                    name = mission.get('name', 'Unknown')
                    print(f"✓ Loaded mission config: {name}")
                    print(f"  Location: {lat:.6f}, {lon:.6f}")
                    return lat, lon
            except Exception as e:
                print(f"✗ Error loading config from {config_path}: {e}")
    
    print(f"✓ Using default location: Dhaka ({default_lat}, {default_lon})")
    return default_lat, default_lon


def update_mission_config(name, latitude, longitude):
    """Update mission config file with new coordinates"""
    config_path = "mission_config.json"
    
    config = {
        "mission": {
            "name": name,
            "latitude": latitude,
            "longitude": longitude
        }
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Updated mission config: {name} ({latitude}, {longitude})")
        return True
    except Exception as e:
        print(f"✗ Error saving config: {e}")
        return False
