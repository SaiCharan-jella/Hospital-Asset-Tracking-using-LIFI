"""
Add all missing optical zones to database
"""

from database import db

# Get existing zones
existing_zones = db.get_all_zones()
existing_names = [z.get('name') for z in existing_zones]

print(f"Found {len(existing_zones)} existing zones: {existing_names}")

# All zones that should exist
all_zones = [
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

added = 0
for zone_data in all_zones:
    if zone_data['name'] not in existing_names:
        zone_id = db.create_zone(zone_data)
        db.approve_zone(zone_id, 'system')
        print(f"[+] Added and activated: {zone_data['name']}")
        added += 1
    else:
        print(f"[SKIP] Zone already exists: {zone_data['name']}")

print(f"\n[SUCCESS] Added {added} new zones. Total zones: {len(db.get_all_zones())}")
