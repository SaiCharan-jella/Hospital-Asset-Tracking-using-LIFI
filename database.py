"""
TinyDB wrapper for Hospital LiFi Handoff System
Manages all database collections and operations
"""

from tinydb import TinyDB, Query, where
from tinydb.operations import increment, set as db_set
from datetime import datetime
import os
from config import Config

class HospitalDatabase:
    """Centralized database management for hospital system"""
    
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
        
        # Initialize TinyDB
        self.db = TinyDB(Config.DB_PATH, indent=2)
        
        # Define collections (tables)
        self.users = self.db.table('users')
        self.roles = self.db.table('roles')
        self.assets = self.db.table('assets')
        self.encrypted_files = self.db.table('encrypted_files')
        self.shared_secrets = self.db.table('shared_secrets')
        self.handoff_logs = self.db.table('handoff_logs')
        self.zones = self.db.table('zones')
        self.routing_logs = self.db.table('routing_logs')
        
        # Initialize default roles
        self._initialize_roles()
    
    def _initialize_roles(self):
        """Initialize default role definitions"""
        if len(self.roles.all()) == 0:
            default_roles = [
                {
                    'role_name': 'admin',
                    'display_name': 'Hospital Administrator',
                    'permissions': [
                        'view_all_files',
                        'decrypt_all_files',
                        'approve_users',
                        'manage_permissions',
                        'view_logs',
                        'manage_assets'
                    ]
                },
                {
                    'role_name': 'asset_manager',
                    'display_name': 'Asset Management Officer',
                    'permissions': [
                        'manage_assets',
                        'upload_files',
                        'download_files',
                        'validate_handoffs',
                        'send_secrets'
                    ]
                },
                {
                    'role_name': 'user',
                    'display_name': 'Hospital User',
                    'permissions': [
                        'upload_files',
                        'download_own_files',
                        'view_assets',
                        'send_secrets'
                    ]
                }
            ]
            self.roles.insert_multiple(default_roles)
    
    # User Operations
    def create_user(self, username, password_hash, role, email=None):
        """Create a new user account"""
        user_data = {
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'email': email,
            'approved': True if role == 'admin' else False,  # Auto-approve first admin
            'shared_secret_access': False,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        return self.users.insert(user_data)
    
    def get_user(self, username):
        """Get user by username"""
        User = Query()
        return self.users.get(User.username == username)
    
    def approve_user(self, username):
        """Approve a pending user account"""
        User = Query()
        self.users.update({'approved': True}, User.username == username)
    
    def update_shared_secret_access(self, username, access):
        """Grant or revoke shared secret access"""
        User = Query()
        self.users.update({'shared_secret_access': access}, User.username == username)
    
    def get_pending_users(self):
        """Get all users awaiting approval"""
        User = Query()
        return self.users.search(User.approved == False)
    
    def get_all_users(self):
        """Get all users"""
        return self.users.all()
    
    # Asset Operations
    def create_asset(self, asset_data):
        """Create a new hospital asset"""
        asset_data['created_at'] = datetime.now().isoformat()
        return self.assets.insert(asset_data)
    
    def get_asset(self, asset_id):
        """Get asset by ID"""
        return self.assets.get(doc_id=asset_id)
    
    def get_all_assets(self):
        """Get all assets"""
        return self.assets.all()
    
    def update_asset(self, asset_id, updates):
        """Update asset information"""
        self.assets.update(updates, doc_ids=[asset_id])
    
    # Encrypted File Operations
    def create_encrypted_file(self, file_data):
        """Store encrypted file metadata"""
        file_data['created_at'] = datetime.now().isoformat()
        file_data['downloaded_by'] = []
        return self.encrypted_files.insert(file_data)
    
    def get_file(self, file_id):
        """Get file by ID"""
        return self.encrypted_files.get(doc_id=file_id)
    
    def get_files_by_uploader(self, username):
        """Get files uploaded by specific user"""
        File = Query()
        return self.encrypted_files.search(File.uploader == username)
    
    def get_files_shared_with_role(self, role):
        """Get files shared with a specific role"""
        File = Query()
        return self.encrypted_files.search(File.shared_with.any([role]))
    
    def get_all_files(self):
        """Get all encrypted files"""
        return self.encrypted_files.all()
    
    def add_file_download_log(self, file_id, username, role):
        """Log file download"""
        File = Query()
        file = self.encrypted_files.get(doc_id=file_id)
        if file:
            downloads = file.get('downloaded_by', [])
            downloads.append({
                'username': username,
                'role': role,
                'timestamp': datetime.now().isoformat()
            })
            self.encrypted_files.update({'downloaded_by': downloads}, doc_ids=[file_id])
    
    # Shared Secret Operations
    def create_shared_secret(self, secret_data):
        """Store encrypted shared secret"""
        secret_data['timestamp'] = datetime.now().isoformat()
        secret_data['read'] = False
        return self.shared_secrets.insert(secret_data)
    
    def get_secrets_for_role(self, role):
        """Get secrets sent to a specific role"""
        Secret = Query()
        return self.shared_secrets.search(Secret.to_role == role)
    
    def mark_secret_read(self, secret_id):
        """Mark secret as read"""
        self.shared_secrets.update({'read': True}, doc_ids=[secret_id])
    
    # Handoff Log Operations
    def create_handoff_log(self, log_data):
        """Create handoff session log entry"""
        log_data['timestamp'] = datetime.now().isoformat()
        return self.handoff_logs.insert(log_data)
    
    def get_handoff_logs(self, limit=100):
        """Get recent handoff logs"""
        logs = self.handoff_logs.all()
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]

    def get_active_handoff_sessions(self, status=None):
        """Get active handoff sessions (last 24 hours), optionally filtered by status"""
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        Log = Query()
        if status:
            return self.handoff_logs.search((Log.timestamp > cutoff) & (Log.status == status))
        return self.handoff_logs.search(Log.timestamp > cutoff)

    def get_unresolved_handoffs(self):
        """Get handoffs that are unstable, failed, or pending validation"""
        Log = Query()
        return self.handoff_logs.search(
            (Log.status == 'unstable') | 
            (Log.status == 'failed') | 
            (Log.status == 'pending') |
            (Log.status == 'integrity_failed') |
            (Log.status == 'file_missing')
        )
    
    def update_handoff_status(self, session_id, status):
        """Update handoff session status"""
        Log = Query()
        self.handoff_logs.update({'status': status}, Log.session_id == session_id)
    
    # Statistics
    def get_statistics(self):
        """Get system-wide statistics"""
        return {
            'total_users': len(self.users.all()),
            'pending_users': len(self.get_pending_users()),
            'total_assets': len(self.assets.all()),
            'total_files': len(self.encrypted_files.all()),
            'active_handoffs': len(self.get_active_handoff_sessions()),
            'total_secrets': len(self.shared_secrets.all())
        }
    
    # Zone Management Operations
    def create_zone(self, zone_data):
        """Create a new optical zone"""
        zone_data['created_at'] = datetime.now().isoformat()
        zone_data['status'] = 'pending'  # pending, active, inactive
        zone_data['approved_by'] = None
        return self.zones.insert(zone_data)
    
    def get_all_zones(self):
        """Get all zones"""
        return self.zones.all()
    
    def get_active_zones(self):
        """Get all active zones"""
        Zone = Query()
        return self.zones.search(Zone.status == 'active')
    
    def get_pending_zones(self):
        """Get zones awaiting admin approval"""
        Zone = Query()
        return self.zones.search(Zone.status == 'pending')
    
    def approve_zone(self, zone_id, admin_username):
        """Admin approve zone activation"""
        self.zones.update({
            'status': 'active',
            'approved_by': admin_username,
            'approved_at': datetime.now().isoformat()
        }, doc_ids=[zone_id])
    
    def deactivate_zone(self, zone_id):
        """Deactivate a zone"""
        self.zones.update({'status': 'inactive'}, doc_ids=[zone_id])
    
    # Routing Log Operations
    def create_routing_log(self, routing_data):
        """Log routing protocol performance"""
        routing_data['timestamp'] = datetime.now().isoformat()
        return self.routing_logs.insert(routing_data)
    
    def get_routing_logs(self, limit=50):
        """Get recent routing logs"""
        logs = self.routing_logs.all()
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
    
    # --- Routing Protocol Methods ---
    def log_routing_metrics(self, data):
        """Store routing simulation results"""
        return self.routing_logs.insert(data)

    def get_routing_comparison(self, limit=10):
        """Get latest routing comparison logs"""
        return sorted(self.routing_logs.all(), key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]

    def close(self):
        """Close database connection"""
        self.db.close()

# Global database instance
db = HospitalDatabase()
