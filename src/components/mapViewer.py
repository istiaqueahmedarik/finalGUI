"""
Enhanced MapViewer — Continuous GPS tracking with path history
- Street map (OpenStreetMap) instead of satellite
- Accurate Web Mercator GPS-to-pixel projection
- Rover marker = arrow icon (rotates with heading), Red = waypoints, Trail = path history
"""

import os
import json
import math
from math import radians, cos, sin, sqrt, atan2

from PyQt6.QtCore import (
    pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QObject, pyqtProperty, QParallelAnimationGroup, Qt, QPointF
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QScrollArea
)
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor, QPen



# =============================================================================
# Web Mercator helpers — must match OSM tile projection exactly
# =============================================================================

def _mercator_y_frac(lat_deg):
    """Latitude → normalized Web Mercator Y (0=top/north, 1=bottom/south)"""
    lat_rad = math.radians(lat_deg)
    return (1.0 - math.log(
        math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0




def gps_to_pixel_mercator(lat, lon, map_bounds, img_width, img_height):
    """
    High-precision conversion using absolute Mercator fractions.
    Returns QPointF with floating-point precision to avoid rounding errors.
    At zoom 17, 1 pixel ≈ 1.2 meters, so int() conversion causes meters of error.
    """
    def lat_to_y(l):
        lat_rad = math.radians(l)
        # Standard OSM Web Mercator formula: ln(tan(lat) + sec(lat))
        return (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0

    # Get Mercator Y fractions for bounding box
    y_top = lat_to_y(map_bounds["max_lat"])
    y_bottom = lat_to_y(map_bounds["min_lat"])
    y_point = lat_to_y(lat)

    # X is linear (Longitude), Y is Mercator-transformed
    x_frac = (lon - map_bounds["min_lon"]) / (map_bounds["max_lon"] - map_bounds["min_lon"])
    y_frac = (y_point - y_top) / (y_bottom - y_top)

    # CRITICAL: Return QPointF (not int) to keep sub-pixel accuracy
    # This prevents the "nearby but not exact" problem
    return QPointF(x_frac * img_width, y_frac * img_height)


def pixel_to_gps_mercator(px, py, map_bounds, img_width, img_height):
    """
    Inverse projection: Pixel coordinates → GPS (lat, lon)
    Used for click-to-adjust waypoint positioning.
    """
    def y_to_lat(y_frac):
        # Inverse Web Mercator: lat = atan(sinh(pi * (1 - 2y)))
        # If y_frac is far outside [0,1], sinh() can overflow. Clamp for stability.
        y_norm = 1.0 - 2.0 * y_frac
        t = math.pi * y_norm
        # Beyond ~20, atan(sinh(t)) is effectively +/- pi/2 anyway.
        t = max(-20.0, min(20.0, t))
        lat_rad = math.atan(math.sinh(t))
        return math.degrees(lat_rad)

    # Normalize pixel coordinates to fractions.
    # Clamp to image bounds so reverse-projection can't overflow on out-of-range inputs.
    if img_width <= 0 or img_height <= 0:
        return 0.0, 0.0

    x_frac = px / img_width
    y_frac = py / img_height
    x_frac = max(0.0, min(1.0, x_frac))
    y_frac = max(0.0, min(1.0, y_frac))

    # Convert fractions back to GPS
    lon = map_bounds["min_lon"] + x_frac * (map_bounds["max_lon"] - map_bounds["min_lon"])
    lat = y_to_lat(y_frac)

    return lat, lon


# =============================================================================
# AnimatedMarker
# =============================================================================

class AnimatedMarker(QObject):
    position_changed = pyqtSignal()

    def __init__(self, lat, lon):
        super().__init__()
        self._lat = float(lat)
        self._lon = float(lon)

    @pyqtProperty(float)
    def lat(self): return self._lat

    @lat.setter
    def lat(self, value):
        self._lat = float(value)
        self.position_changed.emit()

    @pyqtProperty(float)
    def lon(self): return self._lon

    @lon.setter
    def lon(self, value):
        self._lon = float(value)
        self.position_changed.emit()

    def animate_to(self, target_lat, target_lon, duration=300):
        self._group = QParallelAnimationGroup(self)
        for attr, target in [(b"lat", target_lat), (b"lon", target_lon)]:
            anim = QPropertyAnimation(self, attr, self._group)
            anim.setDuration(duration)
            anim.setStartValue(getattr(self, attr.decode()))
            anim.setEndValue(float(target))
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            self._group.addAnimation(anim)
        self._group.start()
        return self._group


# =============================================================================
# MapViewer
# =============================================================================

class MapViewer(QWidget):

    waypoint_data    = pyqtSignal(list)
    position_updated = pyqtSignal(float, float)

    # ------------------------------------------------------------------
    # Tile configuration
    # OSM street map: zoom=17, 5×5 tiles → ~1400m × 1400m coverage
    # Change zoom to 16 for wider area, 18 for closer detail
    # ------------------------------------------------------------------
    DEFAULT_ZOOM   = 17
    DEFAULT_TILES_X = 5
    DEFAULT_TILES_Y = 5

    def __init__(self, tile_source='osm', tile_server_url='http://127.0.0.1:8765',
                 map_bounds=None, map_center_lat=None, map_center_lon=None,
                 mission_latitude=None, mission_longitude=None):
        super().__init__()

        self.TILE_SOURCE     = tile_source
        self.TILE_SERVER_URL = tile_server_url

        # Default world bounds — replaced once map is downloaded
        self.map_bounds = map_bounds or {
            "min_lat": -90, "max_lat": 90,
            "min_lon": -180, "max_lon": 180
        }

        self._map_center_lat = map_center_lat or 0.0
        self._map_center_lon = map_center_lon or 0.0

        # Mission location — Dhaka default, override via constructor
        self.mission_latitude  = mission_latitude  or 23.87701697119773
        self.mission_longitude = mission_longitude or 90.35928646267514

        self._map_downloaded      = False
        self._map_drift_threshold = 400  # re-download if rover drifts >400m

        # ---- UI ----
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)

        self.gps_status = QLabel("GPS: Waiting for data...")
        self.gps_status.setFixedHeight(24)
        self.gps_status.setStyleSheet(
            "color:orange;font-weight:bold;padding:3px 6px;"
            "background:#111;font-size:12px;")
        self.main_layout.addWidget(self.gps_status)

        # State
        self.current_lat   = self._map_center_lat
        self.current_lon   = self._map_center_lon
        self.gps_connected = False
        self.has_waypoints = False
        self.gps_path      = []
        self.max_path_points = 500
        self.waypoints     = []

        # Rover orientation (degrees, 0=north, 90=east). If no heading is provided,
        # we compute a bearing from the last two GPS points.
        self.rover_heading_deg = None

        # Rover icon (right-facing arrow). Drawn on top of the map as the rover marker.
        self._rover_icon_px = 34
        self._rover_arrow_pixmap = self._load_rover_arrow_pixmap()

        self.original_pixmap = None
        self.zoom_level = 1.0
        self.min_zoom   = 0.5
        self.max_zoom   = 3.0
        self.zoom_step  = 0.2

        self.animated_marker = AnimatedMarker(self.current_lat, self.current_lon)
        self.animated_marker.position_changed.connect(self._draw_marker_on_map)

        # Map display widget
        self.map_display = QLabel()
        self.map_display.setStyleSheet("background-color:#1a1a2e; border:1px solid #444;")
        self.map_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        scroll = QScrollArea()
        scroll.setWidget(self.map_display)
        scroll.setWidgetResizable(True)
        self.main_layout.addWidget(scroll, stretch=1)

        # Button bar
        btn_layout = QHBoxLayout()

        self.zoom_out_btn = QPushButton("− Zoom Out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        btn_layout.addWidget(self.zoom_out_btn)

        self.zoom_level_label = QLabel(f"Zoom: {self.zoom_level:.0%}")
        self.zoom_level_label.setStyleSheet("padding:0 10px; font-weight:bold;")
        btn_layout.addWidget(self.zoom_level_label)

        self.zoom_in_btn = QPushButton("+ Zoom In")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        btn_layout.addWidget(self.zoom_in_btn)

        btn_layout.addSpacing(20)

        self.refresh_map_btn = QPushButton("⟳ Refresh Map")
        self.refresh_map_btn.clicked.connect(self._refresh_map)
        btn_layout.addWidget(self.refresh_map_btn)

        self.main_layout.addLayout(btn_layout)

        # Load map
        self._load_map_with_fallback()
        self._page_ready = True

    def _load_rover_arrow_pixmap(self):
        icon_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "icon", "right-arrow.png")
        )
        if not os.path.exists(icon_path):
            print(f"[MAP] ⚠ Rover arrow icon missing: {icon_path}")
            return None
        pm = QPixmap(icon_path)
        if pm.isNull():
            print(f"[MAP] ⚠ Failed to load rover arrow icon: {icon_path}")
            return None
        return pm

    def _bearing_deg(self, la1, lo1, la2, lo2):
        """Initial bearing from point 1 to point 2 (degrees, 0=north)."""
        phi1 = radians(la1)
        phi2 = radians(la2)
        dlon = radians(lo2 - lo1)

        y = sin(dlon) * cos(phi2)
        x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dlon)
        brng = math.degrees(math.atan2(y, x))
        return (brng + 360.0) % 360.0

    # =========================================================================
    # Map loading
    # =========================================================================

    def _load_map_with_fallback(self):
        if hasattr(self, 'TILE_SOURCE') and self.TILE_SOURCE == 'local':
            print("[MAP] Using offline tile server...")
            if self._load_online_map():
                self._map_downloaded = True
                return

        print("[MAP] Checking for offline cached map...")
        if self._load_offline_map_image():
            b = self.map_bounds
            if (b["min_lat"] <= self.mission_latitude <= b["max_lat"] and 
                b["min_lon"] <= self.mission_longitude <= b["max_lon"]):
                self._map_downloaded = True
                return
            else:
                print("[MAP] Cached map exists but mission location is out of bounds. Will download new map.")

        print("[MAP] Trying online OSM street map...")
        if self._load_online_map():
            self._map_downloaded = True
            return
        
        print("[MAP] No map available, showing placeholder.")
        self._show_map_placeholder()

    def _load_online_map(self):
        if not (hasattr(self, 'TILE_SOURCE') and self.TILE_SOURCE == 'local'):
            try:
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=2)
            except Exception:
                print("[MAP] No internet connection.")
                return False

        ok, msg = self._download_osm_map(
            center_lat=self.mission_latitude,
            center_lon=self.mission_longitude,
            zoom=self.DEFAULT_ZOOM,
            tiles_x=self.DEFAULT_TILES_X,
            tiles_y=self.DEFAULT_TILES_Y
        )
        print(f"[MAP] {msg}")
        return ok

    def _download_osm_map(self, center_lat, center_lon,
                           zoom=17, tiles_x=5, tiles_y=5,
                           progress_callback=None):
        """
        Download OpenStreetMap street tiles and stitch into one image.

        OSM tile URL:    https://tile.openstreetmap.org/{z}/{x}/{y}.png
        Note: OSM uses {x}=column, {y}=row  (NOT swapped like ArcGIS)

        Saves live_map.png + live_map_bounds.json to assets/tiles/.
        Updates self.map_bounds with exact Web Mercator tile-edge bounds.
        """
        try:
            import requests
        except ImportError:
            return False, "requests not installed — pip install requests"
        try:
            from PIL import Image
            import io
        except ImportError:
            return False, "Pillow not installed — pip install Pillow"

        def _tile_col_row(lat, lon, z):
            """GPS → OSM tile column (x) and row (y)"""
            n = 2 ** z
            col = int((lon + 180.0) / 360.0 * n)
            lat_r = math.radians(lat)
            row = int((1.0 - math.log(
                math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
            return col, row

        def _tile_edge_bounds(col, row, z):
            """
            Exact Web Mercator lat/lon at the EDGES of tile (col, row).
            Returns (north_lat, west_lon, south_lat, east_lon)
            """
            n = 2.0 ** z
            west_lon  = (col / n) * 360.0 - 180.0
            east_lon  = ((col + 1) / n) * 360.0 - 180.0
            north_lat = math.degrees(math.atan(math.sinh(
                math.pi * (1.0 - 2.0 * row / n))))
            south_lat = math.degrees(math.atan(math.sinh(
                math.pi * (1.0 - 2.0 * (row + 1) / n))))
            return north_lat, west_lon, south_lat, east_lon

        center_col, center_row = _tile_col_row(center_lat, center_lon, zoom)
        half_x = tiles_x // 2
        half_y = tiles_y // 2
        n_max  = 2 ** zoom - 1
        tile_px = 256

        stitched = Image.new("RGB",
                             (tiles_x * tile_px, tiles_y * tile_px),
                             (30, 30, 40))

        # OSM requires a proper User-Agent
        headers = {
            "User-Agent": "RoverMissionDashboard/1.0 (rover navigation; educational)"
        }

        total = tiles_x * tiles_y
        done  = 0
        cols_used = []
        rows_used = []

        for grid_row in range(tiles_y):
            for grid_col in range(tiles_x):
                col = max(0, min(center_col - half_x + grid_col, n_max))
                row = max(0, min(center_row - half_y + grid_row, n_max))
                cols_used.append(col)
                rows_used.append(row)

                if progress_callback:
                    progress_callback(done, total,
                        f"Tile ({grid_col+1},{grid_row+1}) of {tiles_x}×{tiles_y}")

                # Use offline server if TILE_SOURCE is local, else OSM
                if hasattr(self, 'TILE_SOURCE') and self.TILE_SOURCE == 'local':
                    url = f"{self.TILE_SERVER_URL.rstrip('/')}/tiles/{zoom}/{col}/{row}.png"
                else:
                    url = f"https://tile.openstreetmap.org/{zoom}/{col}/{row}.png"

                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        tile_img = Image.open(io.BytesIO(resp.content))
                        stitched.paste(tile_img, (grid_col * tile_px, grid_row * tile_px))
                    else:
                        print(f"  ✗ HTTP {resp.status_code}: tile ({grid_col+1},{grid_row+1})")
                except Exception as e:
                    print(f"  ✗ tile ({grid_col+1},{grid_row+1}) → {e}")

                done += 1

        # ------------------------------------------------------------------
        # Exact bounds from actual tile edges — MUST match projection
        # col_min/row_min = top-left tile, col_max/row_max = bottom-right tile
        # ------------------------------------------------------------------
        col_min, col_max = min(cols_used), max(cols_used)
        row_min, row_max = min(rows_used), max(rows_used)

        north_lat, west_lon, _, _         = _tile_edge_bounds(col_min, row_min, zoom)
        _, _,       south_lat, east_lon   = _tile_edge_bounds(col_max, row_max, zoom)

        self.map_bounds = {
            "min_lat": south_lat,   # bottom / south
            "max_lat": north_lat,   # top    / north
            "min_lon": west_lon,    # left   / west
            "max_lon": east_lon,    # right  / east
        }

        area_lat_m = (north_lat - south_lat) * 111320
        area_lon_m = ((east_lon - west_lon) * 111320
                      * math.cos(math.radians(center_lat)))

        print(f"[MAP] Bounds: lat [{south_lat:.8f}, {north_lat:.8f}] "
              f"lon [{west_lon:.8f}, {east_lon:.8f}]")
        print(f"[MAP] Coverage: {area_lat_m:.0f}m × {area_lon_m:.0f}m "
              f"at zoom {zoom}")

        # Save image + sidecar bounds JSON
        save_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../assets/tiles"))
        os.makedirs(save_dir, exist_ok=True)
        save_path   = os.path.join(save_dir, "live_map.png")
        bounds_path = os.path.join(save_dir, "live_map_bounds.json")

        stitched.save(save_path)
        with open(bounds_path, "w") as f:
            json.dump(self.map_bounds, f, indent=2)
        print(f"[MAP] Saved → {save_path}")
        print(f"[MAP] Bounds → {bounds_path}")

        pixmap = QPixmap(save_path)
        if not pixmap.isNull():
            self.original_pixmap = pixmap.copy()
            self.map_display.setPixmap(
                self.original_pixmap.scaledToWidth(
                    700, Qt.TransformationMode.SmoothTransformation))
            self._draw_marker_on_map()
            size_kb = os.path.getsize(save_path) // 1024
            return True, (f"Downloaded {tiles_x}×{tiles_y} OSM tiles "
                          f"at zoom {zoom} ({size_kb} KB, "
                          f"{area_lat_m:.0f}m × {area_lon_m:.0f}m)")
        return False, "Map saved but QPixmap failed to load it"

    def _load_offline_map_image(self):
        candidates = [
            os.path.join(os.path.dirname(__file__), "../../assets/tiles/live_map.png"),
            "../assets/tiles/live_map.png",
        ]
        for map_path in candidates:
            if not os.path.exists(map_path):
                continue
            try:
                pixmap = QPixmap(map_path)
                if pixmap.isNull():
                    continue
                self.original_pixmap = pixmap.copy()

                bounds_path = map_path.replace(".png", "_bounds.json")
                if os.path.exists(bounds_path):
                    with open(bounds_path) as f:
                        self.map_bounds = json.load(f)
                    print(f"[MAP] Loaded cached bounds: {self.map_bounds}")
                else:
                    print("[MAP] ⚠ No bounds cache — using rough estimate")
                    pad = 0.005
                    self.map_bounds = {
                        "min_lat": self.mission_latitude  - pad,
                        "max_lat": self.mission_latitude  + pad,
                        "min_lon": self.mission_longitude - pad,
                        "max_lon": self.mission_longitude + pad,
                    }

                self.map_display.setPixmap(
                    pixmap.scaledToWidth(700, Qt.TransformationMode.SmoothTransformation))
                print(f"[MAP] Loaded offline: {map_path}")
                return True
            except Exception as e:
                print(f"[MAP] Error loading {map_path}: {e}")
        return False

    def _show_map_placeholder(self):
        ph = QPixmap(800, 600)
        ph.fill(QColor(26, 26, 46))
        p = QPainter(ph)
        p.setPen(QPen(QColor(40, 45, 70), 1))
        for x in range(0, 800, 40): p.drawLine(x, 0, x, 600)
        for y in range(0, 600, 40): p.drawLine(0, y, 800, y)
        p.setPen(QColor(160, 165, 190))
        f = QFont(); f.setPointSize(13)
        p.setFont(f)
        p.drawText(ph.rect(), Qt.AlignmentFlag.AlignCenter,
                   "MAP VIEWER\nWaiting for GPS + internet...\n\n"
                   "➡️  Arrow = Rover position (rotates)\n"
                   "━━  Line  = Path traveled\n"
                   "🔴 Red   = Destination waypoint")
        p.end()
        self.original_pixmap = ph.copy()
        pad = 0.005
        self.map_bounds = {
            "min_lat": self.mission_latitude  - pad,
            "max_lat": self.mission_latitude  + pad,
            "min_lon": self.mission_longitude - pad,
            "max_lon": self.mission_longitude + pad,
        }
        self.map_display.setPixmap(ph)

    def _refresh_map(self):
        """Refresh map button — re-downloads centered on current rover position"""
        lat = self.current_lat if self.gps_connected else self.mission_latitude
        lon = self.current_lon if self.gps_connected else self.mission_longitude
        print(f"[MAP] Refreshing around ({lat:.6f}, {lon:.6f})...")
        ok, msg = self._download_osm_map(
            lat, lon,
            zoom=self.DEFAULT_ZOOM,
            tiles_x=self.DEFAULT_TILES_X,
            tiles_y=self.DEFAULT_TILES_Y
        )
        print(f"[MAP] Refresh: {msg}")

    # =========================================================================
    # GPS → pixel  (single source of truth — Web Mercator)
    # =========================================================================

    def _to_pixel(self, lat, lon, display_w, display_h):
        """Convert GPS to pixel on the displayed image using exact Mercator projection.
        
        Args:
            lat, lon: GPS coordinates (degrees)
            display_w, display_h: CURRENT displayed width/height (not original image size)
        
        Returns:
            QPointF: Floating-point pixel coordinates (preserved for sub-pixel accuracy)
        """
        return gps_to_pixel_mercator(lat, lon, self.map_bounds, display_w, display_h)

    # =========================================================================
    # Drawing
    # =========================================================================

    def _draw_marker_on_map(self):
        """Draw markers with foolproof accuracy by using displayed dimensions."""
        if self.original_pixmap is None:
            return

        # Calculate display dimensions based on current zoom
        scaled_w = int(self.original_pixmap.width() * self.zoom_level) \
                   if self.zoom_level != 1.0 else 700
        
        # Create canvas at the actual displayed size
        canvas = self.original_pixmap.scaledToWidth(
            scaled_w, Qt.TransformationMode.SmoothTransformation)
        dw, dh = canvas.width(), canvas.height()

        p = QPainter(canvas)
        # CRITICAL: Enable both antialiasing and smooth transform for sub-pixel accuracy
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Path trail
        if len(self.gps_path) > 1:
            pen = QPen(QColor(100, 180, 255, 180))
            pen.setWidth(2)
            p.setPen(pen)
            for i in range(1, len(self.gps_path)):
                pt1 = self._to_pixel(*self.gps_path[i-1], dw, dh)
                pt2 = self._to_pixel(*self.gps_path[i],   dw, dh)
                # Use floating-point coordinates directly with drawLine
                p.drawLine(pt1, pt2)

        # Waypoints — red circle + label (FOOLPROOF: exact positioning for Tower-03)
        for wp in self.waypoints:
            pt = self._to_pixel(wp["lat"], wp["lon"], dw, dh)
            # Debug: reverse-projection can overflow if point is outside image/bounds; keep it non-fatal.
            try:
                gps_check = pixel_to_gps_mercator(pt.x(), pt.y(), self.map_bounds, dw, dh)
                print(f"[MAP DEBUG] WP{wp['id']}: GPS({wp['lat']:.8f}, {wp['lon']:.8f}) "
                      f"→ pixel({pt.x():.1f}, {pt.y():.1f}) → GPS check({gps_check[0]:.8f}, {gps_check[1]:.8f})")
            except Exception as e:
                print(f"[MAP DEBUG] WP{wp['id']}: reverse-projection skipped: {e}")
            
            # Draw using QPointF directly (no int() conversion = no rounding error)
            p.setPen(QPen(QColor(220, 50, 50), 2))
            p.setBrush(QColor(220, 50, 50, 200))
            p.drawEllipse(pt, 7.0, 7.0)  # Radius 7, centered at exact point
            # Label offset uses int() only for text positioning
            p.setPen(QColor(255, 255, 255))
            f = QFont(); f.setPointSize(8); f.setBold(True)
            p.setFont(f)
            p.drawText(int(pt.x()) + 10, int(pt.y()) + 4, f"WP{wp['id']}")

        # Rover — arrow icon (rotates with heading); fallback to blue dot if icon missing
        pt = self._to_pixel(self.animated_marker.lat, self.animated_marker.lon, dw, dh)
        if self._rover_arrow_pixmap is not None:
            icon_px = max(18, int(self._rover_icon_px))
            icon = self._rover_arrow_pixmap.scaled(
                icon_px,
                icon_px,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # The icon points EAST by default (right arrow). Convert bearing to painter rotation.
            bearing = self.rover_heading_deg
            rotation_deg = 0.0 if bearing is None else (90.0 - float(bearing))

            p.save()
            p.translate(pt.x(), pt.y())
            p.rotate(rotation_deg)
            p.translate(-icon.width() / 2.0, -icon.height() / 2.0)
            p.drawPixmap(0, 0, icon)
            p.restore()
        else:
            # Draw using QPointF directly for maximum accuracy
            p.setPen(QPen(QColor(0, 140, 255), 3))
            p.setBrush(QColor(0, 140, 255, 210))
            p.drawEllipse(pt, 9.0, 9.0)  # Outer circle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(pt, 3.0, 3.0)  # Inner dot

        p.end()
        self.map_display.setPixmap(canvas)

    # =========================================================================
    # Position update (called from UDP receiver)
    # =========================================================================

    def update_current_position(self, lat, lon):
        lat, lon = float(lat), float(lon)

        print(f"[GPS] lat={lat:.8f}  lon={lon:.8f}")

        # Track previous point for heading estimation
        prev_point = self.gps_path[-1] if self.gps_path else None

        # Add to path
        if not self.gps_path or self.gps_path[-1] != (lat, lon):
            self.gps_path.append((lat, lon))
            if len(self.gps_path) > self.max_path_points:
                self.gps_path.pop(0)

        # Heading update: infer from motion (bearing between last two points)
        try:
            if prev_point is not None and prev_point != (lat, lon):
                prev_lat, prev_lon = prev_point
                moved_m = self._haversine(prev_lat, prev_lon, lat, lon)
                if moved_m >= 0.5:
                    self.rover_heading_deg = self._bearing_deg(prev_lat, prev_lon, lat, lon)
        except Exception as e:
            print(f"[MAP] Heading update failed: {e}")

        # Expand bounds if rover leaves current map area
        pad = 0.0005
        b = self.map_bounds
        if (lat < b["min_lat"] or lat > b["max_lat"] or
                lon < b["min_lon"] or lon > b["max_lon"]):
            print("[MAP] Rover outside bounds — expanding")
            b["min_lat"] = min(b["min_lat"], lat - pad)
            b["max_lat"] = max(b["max_lat"], lat + pad)
            b["min_lon"] = min(b["min_lon"], lon - pad)
            b["max_lon"] = max(b["max_lon"], lon + pad)

        self.animated_marker.animate_to(lat, lon, duration=300)
        self.current_lat = lat
        self.current_lon = lon

        # Re-download map if rover drifts far from current center
        if self._map_downloaded:
            dist = self._haversine(lat, lon,
                                   self.mission_latitude, self.mission_longitude)
            if dist > self._map_drift_threshold:
                print(f"[MAP] Rover drifted {dist:.0f}m — re-downloading...")
                self.mission_latitude  = lat
                self.mission_longitude = lon
                ok, msg = self._download_osm_map(
                    lat, lon,
                    zoom=self.DEFAULT_ZOOM,
                    tiles_x=self.DEFAULT_TILES_X,
                    tiles_y=self.DEFAULT_TILES_Y
                )
                print(f"[MAP] {msg}")

        self.gps_status.setText(
            f"GPS ✓ | {lat:.6f}, {lon:.6f} | "
            f"pts:{len(self.gps_path)} | wps:{len(self.waypoints)}"
        )
        self._draw_marker_on_map()
        self.gps_connected = True
        self.position_updated.emit(lat, lon)

    # =========================================================================
    # Waypoints
    # =========================================================================

    def add_waypoint(self, lat, lon, waypoint_id=None):
        if waypoint_id is None:
            waypoint_id = len(self.waypoints) + 1
        self.waypoints.append({"id": waypoint_id, "lat": float(lat), "lon": float(lon)})
        self.has_waypoints = True
        self._draw_marker_on_map()

    def remove_waypoint(self, waypoint_id):
        self.waypoints = [w for w in self.waypoints if w["id"] != waypoint_id]
        self.has_waypoints = bool(self.waypoints)
        self._draw_marker_on_map()

    def clear_waypoints(self):
        self.waypoints = []
        self.has_waypoints = False
        self._draw_marker_on_map()

    def update_map(self, waypoint_list):
        self.waypoints = []
        for i, wp in enumerate(waypoint_list):
            try:
                if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                    self.waypoints.append({"id": i+1, "lat": float(wp[0]), "lon": float(wp[1])})
                elif isinstance(wp, dict) and "lat" in wp and "lon" in wp:
                    self.waypoints.append({"id": wp.get("id", i+1),
                                           "lat": float(wp["lat"]), "lon": float(wp["lon"])})
            except (ValueError, TypeError):
                print(f"[MAP] Skipping invalid waypoint: {wp}")
        
        # DEBUG: Show waypoint coordinates and bounds alignment
        if self.waypoints:
            for wp in self.waypoints:
                print(f"[MAP] Waypoint {wp['id']}: lat={wp['lat']:.8f}, lon={wp['lon']:.8f}")
            print(f"[MAP] Current bounds: lat [{self.map_bounds['min_lat']:.8f}, {self.map_bounds['max_lat']:.8f}] "
                  f"lon [{self.map_bounds['min_lon']:.8f}, {self.map_bounds['max_lon']:.8f}]")
        
        self.has_waypoints = bool(self.waypoints)
        self._draw_marker_on_map()
        self.gps_status.setText(f"GPS: Waiting... | {len(self.waypoints)} waypoint(s) set")

    def set_destination_to_latest_waypoint(self):
        self.has_waypoints = True

    # =========================================================================
    # Path history
    # =========================================================================

    def clear_path_history(self):
        self.gps_path = []
        self._draw_marker_on_map()

    def get_path_history(self):
        return self.gps_path.copy()

    def _calculate_total_distance(self):
        if len(self.gps_path) < 2:
            return 0.0
        return sum(self._haversine(*self.gps_path[i-1], *self.gps_path[i])
                   for i in range(1, len(self.gps_path)))

    # =========================================================================
    # Zoom
    # =========================================================================

    def zoom_in(self):
        nz = min(self.zoom_level + self.zoom_step, self.max_zoom)
        if nz != self.zoom_level:
            self.zoom_level = nz
            self.zoom_level_label.setText(f"Zoom: {nz:.0%}")
            self._draw_marker_on_map()

    def zoom_out(self):
        nz = max(self.zoom_level - self.zoom_step, self.min_zoom)
        if nz != self.zoom_level:
            self.zoom_level = nz
            self.zoom_level_label.setText(f"Zoom: {nz:.0%}")
            self._draw_marker_on_map()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.zoom_level_label.setText("Zoom: 100%")
        self._draw_marker_on_map()

    # =========================================================================
    # Helpers
    # =========================================================================

    def _haversine(self, la1, lo1, la2, lo2):
        R = 6371000
        p1, p2 = radians(la1), radians(la2)
        a = (sin(radians(la2-la1)/2)**2
             + cos(p1)*cos(p2)*sin(radians(lo2-lo1)/2)**2)
        return R * 2 * atan2(sqrt(a), sqrt(1-a))

    def is_at_destination(self, la1, lo1, la2, lo2, threshold=5):
        return self._haversine(la1, lo1, la2, lo2) <= threshold

    # API compatibility stubs
    def _build_and_load_map(self): pass
    def _on_page_loaded(self):     pass
    def _push_update(self):        self._draw_marker_on_map()
    def _generate_html(self):      return ""
    def _update_map_waypoints(self): self._draw_marker_on_map()
    def _load_rover_uri(self):     return None