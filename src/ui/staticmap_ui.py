import os
import staticmap
import PIL.ImageDraw

# Fix for PIL.ImageDraw compatibility
if not hasattr(PIL.ImageDraw.ImageDraw, 'textsize'):
    def textsize(self, text, font=None, *args, **kwargs):
        bbox = self.textbbox((0, 0), text, font, *args, **kwargs)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    PIL.ImageDraw.ImageDraw.textsize = textsize

class MappingUtility:
    def __init__(self, lat, lon, zoom=15):
        super().__init__()
        self.max_height = 1000
        self.max_width = 1200
        
        # Get project directory
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.dirname(self.script_dir)  # SenderGUI/src
        self.project_dir = os.path.dirname(self.project_dir)  # SenderGUI
        
        # Create assets directory if it doesn't exist
        assets_dir = os.path.join(self.project_dir, "assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            print(f"Created assets directory: {assets_dir}")
        
        self.tiles_cache_dir = os.path.join(assets_dir, "tiles")
        if not os.path.exists(self.tiles_cache_dir):
            os.makedirs(self.tiles_cache_dir)
            print(f"Created tiles cache directory: {self.tiles_cache_dir}")
        
        # Store current position
        self.lat = lat
        self.lon = lon
        self.zoom = zoom
        
        # Store red markers separately
        self.red_markers = []
        
        # Output path
        self.output_path = os.path.join(assets_dir, "live_map.png")
        
        # Create initial map
        self.render_map()

    def render_map(self):
        """Render the map with current position and all markers"""
        # Create FRESH context every time
        self.context = staticmap.StaticMap(
            self.max_width, 
            self.max_height, 
            url_template='http://a.tile.osm.org/{z}/{x}/{y}.png'
        )
        
        # Add blue marker for CURRENT position
        print(f"Creating map centered at: {self.lat}, {self.lon} (zoom: {self.zoom})")
        self.center_marker = staticmap.CircleMarker((self.lon, self.lat), 'blue', 12)
        self.context.add_marker(self.center_marker)
        
        # Add all red markers (waypoints)
        if self.red_markers:
            print(f"Adding {len(self.red_markers)} red waypoint markers")
            for marker_lat, marker_lon in self.red_markers:
                marker = staticmap.CircleMarker((marker_lon, marker_lat), 'red', 10)
                self.context.add_marker(marker)
        
        # Render and save
        try:
            image = self.context.render(zoom=self.zoom, center=(self.lon, self.lat))
            image.save(self.output_path)
            print(f"Map saved to: {self.output_path}")
        except Exception as e:
            print(f"Error rendering map: {e}")
            raise

    def update_position(self, lat, lon):
        """Update current GPS position and re-render"""
        print(f"Updating map center to: {lat}, {lon}")
        self.lat = lat
        self.lon = lon
        self.render_map()

    def add_markers(self, marker_list=None):
        """Add/update destination markers (red waypoints)"""
        if marker_list:
            print(f"Updating waypoint markers: {len(marker_list)} markers")
            self.red_markers = []
            for lat, lon in marker_list:
                self.red_markers.append((float(lat), float(lon)))
            self.render_map()
        else:
            print("No markers to add (marker_list is empty)")
    
    def get_map_path(self):
        return self.output_path