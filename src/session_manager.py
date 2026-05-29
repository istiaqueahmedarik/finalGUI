#!/usr/bin/env python3
"""
Session Manager - Utility to view and manage recorded GPS path sessions
"""

import sys
import json
from pathlib import Path
from utility.path_history_manager import PathHistoryManager


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def list_sessions():
    """List all recorded sessions"""
    manager = PathHistoryManager()
    sessions = manager.list_sessions()
    
    print_header("Recorded Sessions")
    
    if not sessions:
        print("No sessions found in ./path_history/")
        return
    
    print(f"Total sessions: {len(sessions)}\n")
    
    for i, session_name in enumerate(sessions, 1):
        try:
            stats = manager.get_path_statistics(session_name)
            if stats:
                print(f"{i}. {session_name}")
                print(f"   📍 Path points: {stats['total_points']}")
                print(f"   📏 Distance: {stats['total_distance_m']:.2f}m")
                print(f"   🎯 Waypoints: {stats['waypoints_count']}")
                print(f"   📌 Bounds: [{stats['min_lat']:.6f}, {stats['min_lon']:.6f}]")
                print(f"              [{stats['max_lat']:.6f}, {stats['max_lon']:.6f}]")
                print()
        except Exception as e:
            print(f"{i}. {session_name} (Error reading: {e})\n")


def view_session(session_name):
    """View detailed information about a session"""
    manager = PathHistoryManager()
    
    try:
        session_data = manager.load_session(session_name)
        
        print_header(f"Session: {session_name}")
        
        print(f"Start Time: {session_data.get('start_time', 'N/A')}")
        print(f"End Time: {session_data.get('end_time', 'N/A')}")
        print()
        
        stats = manager.get_path_statistics(session_name)
        print(f"📊 Statistics:")
        print(f"   Total Points: {stats['total_points']}")
        print(f"   Total Distance: {stats['total_distance_m']:.2f} meters")
        print(f"   Center: ({stats['center_lat']:.6f}, {stats['center_lon']:.6f})")
        print(f"   Bounds:")
        print(f"     North: {stats['max_lat']:.6f}")
        print(f"     South: {stats['min_lat']:.6f}")
        print(f"     East: {stats['max_lon']:.6f}")
        print(f"     West: {stats['min_lon']:.6f}")
        print()
        
        print(f"📍 Waypoints: {len(session_data.get('waypoints', []))}")
        for wp in session_data.get('waypoints', [])[:5]:  # Show first 5
            print(f"   - WP{wp['id']}: ({wp['lat']:.6f}, {wp['lon']:.6f})")
        if len(session_data.get('waypoints', [])) > 5:
            print(f"   ... and {len(session_data['waypoints']) - 5} more")
        print()
        
        print(f"📋 Events:")
        for event in session_data.get('events', []):
            print(f"   [{event['type']}] {event['description']}")
        print()
        
        # Show first few and last few path points
        path = session_data.get('path_points', [])
        if path:
            print(f"🛤️  Path Points (first 3 and last 3):")
            for pt in path[:3]:
                print(f"   ({pt['lat']:.6f}, {pt['lon']:.6f}) @ {pt['timestamp']}")
            if len(path) > 6:
                print(f"   ... ({len(path)-6} more points) ...")
            for pt in path[-3:]:
                print(f"   ({pt['lat']:.6f}, {pt['lon']:.6f}) @ {pt['timestamp']}")
        
    except FileNotFoundError:
        print(f"❌ Session not found: {session_name}")
        print("Available sessions:")
        manager = PathHistoryManager()
        for s in manager.list_sessions():
            print(f"   - {s}")


def export_session(session_name, format_type="csv"):
    """Export session to file"""
    manager = PathHistoryManager()
    
    try:
        if format_type == "csv":
            output = manager.export_to_csv(session_name)
            print(f"✅ Exported to CSV: {output}")
        else:
            print(f"❌ Unknown format: {format_type}")
    except Exception as e:
        print(f"❌ Export failed: {e}")


def delete_session(session_name):
    """Delete a session"""
    manager = PathHistoryManager()
    session_dir = manager.storage_dir
    session_file = session_dir / f"{session_name}_path.json"
    
    if session_file.exists():
        session_file.unlink()
        print(f"✅ Deleted session: {session_name}")
    else:
        print(f"❌ Session not found: {session_name}")


def cleanup_old_sessions(days=7):
    """Delete sessions older than N days"""
    from datetime import datetime, timedelta
    
    manager = PathHistoryManager()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    deleted = 0
    for session_name in manager.list_sessions():
        try:
            session_data = manager.load_session(session_name)
            start_time = datetime.fromisoformat(session_data['start_time'])
            
            if start_time < cutoff_date:
                session_file = manager.storage_dir / f"{session_name}_path.json"
                session_file.unlink()
                deleted += 1
                print(f"Deleted: {session_name}")
        except Exception as e:
            print(f"Error processing {session_name}: {e}")
    
    print(f"\n✅ Cleanup complete. Deleted {deleted} old sessions.")


def help_text():
    """Print help message"""
    help_msg = """
GPS Path Session Manager
========================

Usage:
    python session_manager.py [command] [options]

Commands:
    list                          List all recorded sessions
    view <session_name>          View detailed info about a session
    export <session_name> [csv]  Export session to CSV
    delete <session_name>        Delete a specific session
    cleanup [days]               Delete sessions older than N days (default: 7)
    help                         Show this help message

Examples:
    python session_manager.py list
    python session_manager.py view 20250308_120000
    python session_manager.py export 20250308_120000 csv
    python session_manager.py delete 20250308_120000
    python session_manager.py cleanup 14
"""
    print(help_msg)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        help_text()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_sessions()
    
    elif command == "view":
        if len(sys.argv) < 3:
            print("❌ Please provide session name")
            list_sessions()
        else:
            view_session(sys.argv[2])
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("❌ Please provide session name")
        else:
            format_type = sys.argv[3].lower() if len(sys.argv) > 3 else "csv"
            export_session(sys.argv[2], format_type)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please provide session name")
        else:
            confirm = input(f"Delete session {sys.argv[2]}? (y/n): ")
            if confirm.lower() == 'y':
                delete_session(sys.argv[2])
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        confirm = input(f"Delete sessions older than {days} days? (y/n): ")
        if confirm.lower() == 'y':
            cleanup_old_sessions(days)
    
    elif command == "help" or command == "-h":
        help_text()
    
    else:
        print(f"❌ Unknown command: {command}")
        help_text()


if __name__ == "__main__":
    main()
