"""
Initialize default optical zones in database
Run this once to populate zones
"""

from database import db
from config import Config

def initialize_default_zones():
    """Create default optical zones if they don't exist"""
    
    # Check if zones already exist
    existing_zones = db.get_all_zones()
    if len(existing_zones) > 0:
        print(f"Zones already initialized ({len(existing_zones)} zones found)")
        return
    
    # Default zones
    default_zones = [
        {
            'name': 'Zone-A',
            'location': 'Main Hospital Building - Floor 1',
            'description': 'General ward and patient rooms',
            'requested_by': 'system'
        },
        {
            'name': 'Zone-B',
            'location': 'Main Hospital Building - Floor 2',
            'description': 'Surgical preparation and recovery',
            'requested_by': 'system'
        },
        {
            'name': 'Zone-C',
            'location': 'Main Hospital Building - Floor 3',
            'description': 'Outpatient departments',
            'requested_by': 'system'
        },
        {
            'name': 'Zone-D',
            'location': 'Main Hospital Building - Floor 4',
            'description': 'Administrative offices',
            'requested_by': 'system'
        },
        {
            'name': 'ER',
            'location': 'Emergency Wing - Ground Floor',
            'description': 'Emergency room and trauma center',
            'requested_by': 'system'
        },
        {
            'name': 'ICU',
            'location': 'Critical Care Wing - Floor 2',
            'description': 'Intensive care unit',
            'requested_by': 'system'
        },
        {
            'name': 'OT',
            'location': 'Surgical Wing - Floor 3',
            'description': 'Operating theaters',
            'requested_by': 'system'
        },
        {
            'name': 'Reception',
            'location': 'Main Entrance - Ground Floor',
            'description': 'Front desk and waiting area',
            'requested_by': 'system'
        }
    ]
    
    # Create all zones and auto-activate them
    for zone_data in default_zones:
        zone_id = db.create_zone(zone_data)
        # Auto-approve system zones
        db.approve_zone(zone_id, 'system')
        print(f"[OK] Created and activated zone: {zone_data['name']}")
    
    print(f"\n[SUCCESS] Successfully initialized {len(default_zones)} optical zones!")

if __name__ == '__main__':
    print("=" * 60)
    print("Initializing Default Optical Zones")
    print("=" * 60)
    initialize_default_zones()
    print("=" * 60)
