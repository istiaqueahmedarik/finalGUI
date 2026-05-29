"""Mapping utility for rendering a static map image using staticmap.

This module provides a small MappingUtility class that renders an image
to assets/live_map.png using either OpenStreetMap tiles or ESRI World
Imagery (satellite) tiles. It's intentionally lightweight: it only
provides methods to render the map, update the center position, and
add simple red waypoint markers.
"""

import os
import staticmap
import PIL.ImageDraw

# PIL compatibility helper for some Pillow versions
if not hasattr(PIL.ImageDraw.ImageDraw, 'textsize'):
    def _textsize(self, text, font=None, *args, **kwargs):
        bbox = self.textbbox((0, 0), text, font, *args, **kwargs)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    PIL.ImageDraw.ImageDraw.textsize = _textsize


class MappingUtility:
    def __init__(self, lat, lon, zoom=15, provider='osm'):
        self.max_height = 1000
        self.max_width = 1200

        # Project root discovery (assumes this file is in src/utility)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(script_dir)
        project_dir = os.path.dirname(src_dir)

        assets_dir = os.path.join(project_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        self.tiles_cache_dir = os.path.join(assets_dir, 'tiles')
        os.makedirs(self.tiles_cache_dir, exist_ok=True)

        self.lat = float(lat)
        self.lon = float(lon)
        self.zoom = int(zoom)
        self.provider = provider.lower() if isinstance(provider, str) else 'osm'
        self.red_markers = []
        self.output_path = os.path.join(assets_dir, 'live_map.png')

        # Render initial map
        self.render_map()

    def map_exists(self):
        return os.path.exists(self.output_path)

    def render_map(self, desired_zoom=None):
        """Render the map image to `self.output_path` using the
        configured tile provider and any red markers present.
        """
        if self.provider == 'esri':
            url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
            min_zoom, max_zoom = 0, 23
        else:
            url = 'http://a.tile.osm.org/{z}/{x}/{y}.png'
            min_zoom, max_zoom = 0, 19

        # Determine starting zoom
        if desired_zoom is None:
            target_zoom = max(min(self.zoom, max_zoom), min_zoom)
        else:
            target_zoom = max(min(int(desired_zoom), max_zoom), min_zoom)

        last_exc = None
        while target_zoom >= min_zoom:
            m = staticmap.StaticMap(self.max_width, self.max_height, url_template=url)

            # center marker (blue)
            center_marker = staticmap.CircleMarker((self.lon, self.lat), 'blue', 12)
            m.add_marker(center_marker)

            # red waypoint markers
            for (lat, lon) in self.red_markers:
                mk = staticmap.CircleMarker((lon, lat), 'red', 10)
                m.add_marker(mk)

            try:
                image = m.render(zoom=target_zoom, center=(self.lon, self.lat))
                image.save(self.output_path)
                # Basic heuristic: detect placeholder tiles (large uniform light-gray areas)
                try:
                    from PIL import Image
                    img = Image.open(self.output_path).convert('L')
                    w, h = img.size
                    px = img.getdata()
                    # fraction of bright pixels
                    bright = sum(1 for v in px if v > 200) / float(w * h)
                    if bright > 0.65:
                        print(f"MappingUtility: rendered image looks like placeholder (bright frac={bright:.2f}) — falling back to lower zoom")
                        target_zoom -= 1
                        continue
                except Exception:
                    # If PIL check fails, ignore and accept the image
                    pass
                # record the zoom we actually used
                self.zoom = target_zoom
                if desired_zoom is not None and target_zoom != int(desired_zoom):
                    print(f"MappingUtility: fell back from requested zoom {desired_zoom} to {target_zoom} to render tiles")
                return target_zoom
            except Exception as e:
                last_exc = e
                print(f"MappingUtility.render_map: failed at zoom {target_zoom}: {e}")
                target_zoom -= 1

        # If we exit the loop, no zoom worked
        print(f"MappingUtility.render_map error: no tiles available (last error: {last_exc})")
        raise last_exc

    def update_position(self, lat, lon):
        lat, lon = float(lat), float(lon)
        if (lat, lon) != (self.lat, self.lon):
            self.lat = lat
            self.lon = lon
            self.render_map()

    def add_markers(self, marker_list=None):
        """marker_list is expected as an iterable of (lat, lon) pairs."""
        if not marker_list:
            self.red_markers = []
        else:
            self.red_markers = [(float(r[0]), float(r[1])) for r in marker_list]
        return self.render_map()

    def get_map_path(self):
        return self.output_path

               

               