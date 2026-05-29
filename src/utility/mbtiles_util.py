#!/usr/bin/env python3
"""
Utility script to create and test MBTiles for offline map operations.
Helps you prepare offline maps for your mission area.
"""

import os
import sys
import sqlite3
from datetime import datetime
import argparse

def create_mbtiles_template(filepath, name="Offline Map", bounds=None, minzoom=18, maxzoom=20):
    """
    Create a minimal MBTiles template (metadata only, no tiles).
    
    Use MOBAC or gdal2tiles to populate with actual tile data.
    
    Args:
        filepath: Output .mbtiles file path
        name: Map name (displayed in metadata)
        bounds: [min_lat, min_lon, max_lat, max_lon] (optional)
        minzoom: Minimum zoom level (default 18)
        maxzoom: Maximum zoom level (default 20)
    """
    
    if bounds is None:
        # Default: Bangladesh Pentagon area
        bounds = [23.837, 90.358, 23.838, 90.360]
    
    min_lat, min_lon, max_lat, max_lon = bounds
    
    conn = sqlite3.connect(filepath)
    cursor = conn.cursor()
    
    # Create metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            name TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Create tiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB,
            PRIMARY KEY (zoom_level, tile_column, tile_row)
        )
    """)
    
    # Add metadata
    metadata = {
        "name": name,
        "type": "baselayer",
        "version": "1.0",
        "description": "Offline map for autonomous drone operations",
        "format": "png",
        "bounds": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "minzoom": str(minzoom),
        "maxzoom": str(maxzoom),
        "center": f"{(min_lon + max_lon) / 2},{(min_lat + max_lat) / 2},{minzoom}",
        "attribution": "OpenStreetMap contributors",
    }
    
    for key, value in metadata.items():
        cursor.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)",
                      (key, value))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created MBTiles template: {filepath}")
    print(f"  Bounds: {bounds}")
    print(f"  Zoom: {minzoom}-{maxzoom}")
    print(f"  Size: ~0 KB (metadata only)")
    print(f"\n  Next: Use MOBAC or gdal2tiles to populate with tile data")
    return filepath

def validate_mbtiles(filepath):
    """
    Validate MBTiles file structure and contents.
    """
    if not os.path.exists(filepath):
        print(f"✗ File not found: {filepath}")
        return False
    
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        # Check metadata table
        cursor.execute("SELECT COUNT(*) FROM metadata")
        metadata_count = cursor.fetchone()[0]
        
        # Check tiles table
        cursor.execute("SELECT COUNT(*) FROM tiles")
        tile_count = cursor.fetchone()[0]
        
        # Get file size
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        
        # Fetch some metadata
        cursor.execute("SELECT name, value FROM metadata LIMIT 10")
        metadata = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        print(f"✓ Valid MBTiles file: {filepath}")
        print(f"  Size: {size_mb:.2f} MB")
        print(f"  Metadata entries: {metadata_count}")
        print(f"  Tile entries: {tile_count}")
        print(f"\n  Metadata:")
        for key, value in sorted(metadata.items()):
            print(f"    {key}: {value}")
        
        if tile_count == 0:
            print(f"\n  ⚠ No tiles found! Use MOBAC or gdal2tiles to populate.")
        else:
            print(f"\n  ✓ Contains {tile_count} tiles (ready for use)")
        
        return True
    
    except sqlite3.DatabaseError:
        print(f"✗ Invalid MBTiles format: {filepath}")
        return False
    except Exception as e:
        print(f"✗ Error validating MBTiles: {e}")
        return False

def show_locations():
    """Show where MBTiles files are searched for."""
    print("MBTiles search locations (in order):")
    locations = [
        "offline_map.mbtiles",
        "map.mbtiles",
        "assets/map.mbtiles",
        os.path.expanduser("~/.cache/dashboard_map.mbtiles"),
    ]
    for i, loc in enumerate(locations, 1):
        exists = "✓" if os.path.exists(loc) else "✗"
        print(f"  {i}. {exists} {loc}")

def show_pentagon_area():
    """Show Pentagon waypoint area information."""
    waypoints = [
        {"id": 1, "lat": 23.8375519, "lon": 90.3593628},
        {"id": 2, "lat": 23.8375553, "lon": 90.3594229},
        {"id": 3, "lat": 23.8375275, "lon": 90.3594903},
        {"id": 4, "lat": 23.8374657, "lon": 90.3593868},
        {"id": 5, "lat": 23.8374912, "lon": 90.3593552},
    ]
    
    lats = [wp["lat"] for wp in waypoints]
    lons = [wp["lon"] for wp in waypoints]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Expand by 20% for context
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    
    bounds = [
        min_lat - lat_range * 0.2,
        min_lon - lon_range * 0.2,
        max_lat + lat_range * 0.2,
        max_lon + lon_range * 0.2,
    ]
    
    print("Pentagon Mission Waypoints (Bangladesh):")
    for wp in waypoints:
        print(f"  Waypoint {wp['id']}: {wp['lat']:.6f}°N, {wp['lon']:.6f}°E")
    
    print(f"\nRecommended MBTiles bounds (with 20% context):")
    print(f"  {bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}")
    
    print(f"\nFor MOBAC: Draw rectangle covering:")
    print(f"  {bounds[0]:.4f}°N to {bounds[2]:.4f}°N")
    print(f"  {bounds[1]:.4f}°E to {bounds[3]:.4f}°E")
    
    return bounds

def main():
    parser = argparse.ArgumentParser(
        description="MBTiles utility for offline map operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mbtiles_util.py create offline_map.mbtiles
  python mbtiles_util.py validate offline_map.mbtiles
  python mbtiles_util.py locations
  python mbtiles_util.py pentagon
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create MBTiles template')
    create_parser.add_argument('output', help='Output MBTiles file')
    create_parser.add_argument('--name', default='Offline Map', help='Map name')
    create_parser.add_argument('--bounds', nargs=4, type=float, 
                              help='Bounds: min_lat min_lon max_lat max_lon')
    create_parser.add_argument('--minzoom', type=int, default=18, help='Min zoom level')
    create_parser.add_argument('--maxzoom', type=int, default=20, help='Max zoom level')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate MBTiles file')
    validate_parser.add_argument('input', help='MBTiles file to validate')
    
    # Locations command
    subparsers.add_parser('locations', help='Show MBTiles search locations')
    
    # Pentagon command
    subparsers.add_parser('pentagon', help='Show Pentagon mission area info')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'create':
        create_mbtiles_template(
            args.output,
            name=args.name,
            bounds=args.bounds,
            minzoom=args.minzoom,
            maxzoom=args.maxzoom
        )
    
    elif args.command == 'validate':
        validate_mbtiles(args.input)
    
    elif args.command == 'locations':
        show_locations()
    
    elif args.command == 'pentagon':
        show_pentagon_area()

if __name__ == "__main__":
    main()
