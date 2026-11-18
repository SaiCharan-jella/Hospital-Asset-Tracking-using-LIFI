"""
Utility helper functions for Hospital LiFi System
"""

from datetime import datetime
import os
from config import Config

def format_timestamp(iso_timestamp):
    """
    Format ISO timestamp to readable string
    Args:
        iso_timestamp: ISO format timestamp string
    Returns:
        Formatted date string
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_timestamp

def format_file_size(size_bytes):
    """
    Format file size in bytes to human-readable format
    Args:
        size_bytes: Size in bytes
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_role_display_name(role_code):
    """
    Get display name for role code
    Args:
        role_code: Role code ('admin', 'asset_manager', 'user')
    Returns:
        Display name string
    """
    return Config.ROLES.get(role_code, role_code.title())

def generate_session_id():
    """
    Generate unique session ID
    Returns:
        Session ID string
    """
    from security import security
    return security.generate_handoff_session_id()

def calculate_integrity_hash(data):
    """
    Calculate SHA256 hash for integrity verification
    Args:
        data: Data to hash (string or bytes)
    Returns:
        Hex digest string
    """
    from security import security
    return security.generate_integrity_hash(data)

def allowed_file(filename):
    """
    Check if file extension is allowed
    Args:
        filename: Name of file
    Returns:
        Boolean indicating if allowed
    """
    from security import security
    return security.validate_file_extension(filename)

def get_file_extension(filename):
    """
    Get file extension
    Args:
        filename: Name of file
    Returns:
        Extension string without dot
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''

def get_optical_zone_color(zone):
    """
    Get color code for optical zone visualization
    Args:
        zone: Zone name
    Returns:
        CSS color code
    """
    zone_colors = {
        'Zone-A': '#00d4ff',
        'Zone-B': '#00ff88',
        'Zone-C': '#ffaa00',
        'Zone-D': '#ff00aa',
        'ER': '#ff0000',
        'ICU': '#ff6600',
        'OT': '#00ffff',
        'Reception': '#0088ff'
    }
    return zone_colors.get(zone, '#888888')

def get_handoff_status_class(status):
    """
    Get CSS class for handoff status
    Args:
        status: Status string
    Returns:
        CSS class name
    """
    status_classes = {
        'stable': 'status-success',
        'unstable': 'status-warning',
        'failed': 'status-danger',
        'pending': 'status-info',
        'completed': 'status-success'
    }
    return status_classes.get(status, 'status-default')

def time_ago(iso_timestamp):
    """
    Get human-readable time difference
    Args:
        iso_timestamp: ISO format timestamp
    Returns:
        Time ago string (e.g., "2 hours ago")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except:
        return "unknown"

def validate_upload_file(file):
    """
    Validate uploaded file
    Args:
        file: FileStorage object from Flask
    Returns:
        Tuple (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "No file selected"
    
    if not allowed_file(file.filename):
        return False, f"File type not allowed. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
    
    return True, None
