# How to Change Mission Location

If you go to America or any other location, you have **two simple options**:

## Option 1: Edit the config file (Recommended)

Edit `mission_config.json`:

```json
{
  "mission": {
    "name": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

**Just change the `name`, `latitude`, and `longitude` values!**

Then restart the dashboard. The map will automatically use the new coordinates.

### Location Examples:
- **Dhaka (Default)**: 23.837171, 90.357756
- **New York**: 40.7128, -74.0060
- **London**: 51.5074, -0.1278
- **Tokyo**: 35.6762, 139.6503
- **Sydney**: -33.8688, 151.2093

## Option 2: Edit code (Harder)

In `src/ui/dashboard_ui.py`, find this line:
```python
self.map_viewer = MapViewer(mission_latitude=mission_lat, mission_longitude=mission_lon)
```

Change it to:
```python
self.map_viewer = MapViewer(mission_latitude=40.7128, mission_longitude=-74.0060)  # New York
```

---

## What Happens When You Change Location?

1. **Map bounds are recalculated** around your new coordinates
2. **GPS markers will appear in the correct location** on the map
3. **Online map download** (if internet available) fetches tiles from your new area
4. **Offline maps** use the new location to align GPS coordinates properly

**No code changes needed!** Just edit the JSON file.
