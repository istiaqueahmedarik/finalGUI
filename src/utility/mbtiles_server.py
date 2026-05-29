"""
Lightweight MBTiles tile server for offline map support.
Runs in background thread and serves tiles from an MBTiles database.
"""

import sqlite3
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import zlib

class TileRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for tile requests (MBTiles or PNG folder)"""
    
    # Class variables to share configuration
    mbtiles_path = None
    source_type = None  # 'mbtiles' or 'folder'
    
    def do_GET(self):
        """Handle GET requests for tiles"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Parse z/x/y from path: /tiles/z/x/y.png
        parts = path.strip('/').split('/')
        
        if len(parts) < 4 or parts[0] != 'tiles':
            self.send_error(404)
            return
        
        try:
            z = int(parts[1])
            x = int(parts[2])
            y = int(parts[3].split('.')[0])
            
            if self.source_type == 'folder':
                tile_data = self._get_tile_from_folder(z, x, y)
            else:
                tile_data = self._get_tile_from_mbtiles(z, x, y)
            
            if tile_data:
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                self.wfile.write(tile_data)
            else:
                self.send_error(404, "Tile not found")
        except (ValueError, IndexError):
            self.send_error(400, "Invalid tile path")
    
    def _get_tile_from_folder(self, z, x, y):
        """Fetch tile from PNG folder (z/x/y.png structure)"""
        if not self.mbtiles_path or not os.path.isdir(self.mbtiles_path):
            return None
        
        try:
            tile_path = os.path.join(self.mbtiles_path, str(z), str(x), f"{y}.png")
            
            if os.path.exists(tile_path):
                with open(tile_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Error fetching tile from folder: {e}")
            return None
    
    def _get_tile_from_mbtiles(self, z, x, y):
        """Fetch tile from MBTiles database"""
        if not self.mbtiles_path or not os.path.exists(self.mbtiles_path):
            return None
        
        try:
            # Flip y for TMS to standard format
            y_tms = (2 ** z) - 1 - y
            
            conn = sqlite3.connect(self.mbtiles_path, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT tile_data FROM tiles WHERE z_order=? AND tile_column=? AND tile_row=?",
                (z, x, y_tms)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                tile_data = result[0]
                # Decompress if needed
                try:
                    return zlib.decompress(tile_data)
                except:
                    return tile_data
            return None
        except Exception as e:
            print(f"Error fetching tile from MBTiles: {e}")
            return None
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass


class MBTilesServer:
    """Lightweight tile server for MBTiles or PNG folder"""
    
    def __init__(self, tiles_source, host="127.0.0.1", port=8765):
        """
        Initialize tile server
        
        Args:
            tiles_source: Path to .mbtiles file OR folder with z/x/y.png tiles
            host: Server host (default localhost)
            port: Server port (default 8765)
        """
        self.tiles_source = tiles_source
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.running = False
        
        # Detect source type
        if os.path.isdir(tiles_source):
            self.source_type = 'folder'  # PNG folder with z/x/y structure
            print(f"Tile source: PNG folder at {tiles_source}")
        elif os.path.isfile(tiles_source):
            self.source_type = 'mbtiles'  # SQLite MBTiles file
            print(f"Tile source: MBTiles file at {tiles_source}")
        else:
            raise FileNotFoundError(f"Tiles source not found: {tiles_source}")
        
        # Share source with handler
        TileRequestHandler.mbtiles_path = tiles_source
        TileRequestHandler.source_type = self.source_type
    
    def start(self):
        """Start tile server in background thread"""
        if self.running:
            return
        
        if self.source_type == 'mbtiles':
            if not os.path.exists(self.tiles_source):
                raise FileNotFoundError(f"MBTiles file not found: {self.tiles_source}")
        elif self.source_type == 'folder':
            if not os.path.isdir(self.tiles_source):
                raise FileNotFoundError(f"Tiles folder not found: {self.tiles_source}")
        
        self.server = HTTPServer((self.host, self.port), TileRequestHandler)
        self.running = True
        
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        print(f"✓ Tile server started at http://{self.host}:{self.port}")
        if self.source_type == 'folder':
            print(f"  Serving PNG tiles from: {self.tiles_source}")
    
    def _run_server(self):
        """Run server loop"""
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Stop tile server"""
        if self.server:
            self.server.shutdown()
            self.running = False
            print("✓ MBTiles server stopped")
    
    def get_url(self):
        """Get tile server URL"""
        return f"http://{self.host}:{self.port}"
    
    def get_metadata(self):
        """Get MBTiles metadata (name, bounds, etc.)"""
        try:
            conn = sqlite3.connect(self.mbtiles_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, value FROM metadata")
            metadata = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            return metadata
        except Exception as e:
            print(f"Error reading metadata: {e}")
            return {}


def create_dummy_mbtiles(filepath, bounds=[23.83, 90.35, 23.84, 90.36], zoom_range=(18, 20)):
    """
    Create a minimal MBTiles file for testing (without actual tiles).
    For production, download/generate real MBTiles using MOBAC or gdal2tiles.
    
    Args:
        filepath: Output MBTiles file path
        bounds: [min_lat, min_lon, max_lat, max_lon]
        zoom_range: (min_zoom, max_zoom)
    """
    import struct
    import io
    
    conn = sqlite3.connect(filepath)
    cursor = conn.cursor()
    
    # Create required tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            name TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
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
    min_lat, min_lon, max_lat, max_lon = bounds
    min_zoom, max_zoom = zoom_range
    
    metadata = {
        "name": "Offline Map",
        "type": "baselayer",
        "version": "1.0",
        "description": "Offline map tiles for drone operations",
        "format": "png",
        "bounds": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "minzoom": str(min_zoom),
        "maxzoom": str(max_zoom),
        "center": f"{(min_lon + max_lon) / 2},{(min_lat + max_lat) / 2},{min_zoom}"
    }
    
    for key, value in metadata.items():
        cursor.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)",
                      (key, value))
    
    conn.commit()
    conn.close()
    print(f"✓ Created minimal MBTiles: {filepath}")
    print(f"  To use: Download real tiles using MOBAC or gdal2tiles for your mission area")


if __name__ == "__main__":
    import tempfile
    
    # Example usage
    mbtiles_file = os.path.join(tempfile.gettempdir(), "test_map.mbtiles")
    
    if not os.path.exists(mbtiles_file):
        create_dummy_mbtiles(mbtiles_file)
    
    server = MBTilesServer(mbtiles_file)
    server.start()
    
    print(f"Tile URL: {server.get_url()}/tiles/18/123456/789012.png")
    print("Press Ctrl+C to stop")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
