"""
Configuration file for Hospital LiFi Handoff System
Contains static encryption key and application settings
"""

from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Load local development settings from .env; environment variables take precedence.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

_fernet_key = os.getenv('FERNET_KEY')
_secret_key = os.getenv('SECRET_KEY')
if not _fernet_key or not _secret_key:
    raise RuntimeError('FERNET_KEY and SECRET_KEY must be set in the environment or .env file.')

STATIC_FERNET_KEY = _fernet_key.encode('ascii')

# Initialize Fernet cipher
fernet = Fernet(STATIC_FERNET_KEY)

# Application Configuration
class Config:
    # Flask Settings
    SECRET_KEY = _secret_key
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in {'1', 'true', 'yes'}
    
    # Database Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'data', 'hospital.json')
    
    # File Storage
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'encrypted')
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'csv'}
    
    # Session Settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # APScheduler Configuration
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Kolkata'
    
    # Celery Configuration (no external broker - filesystem based)
    CELERY_BROKER_URL = 'filesystem://'
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'data_folder_in': os.path.join(BASE_DIR, 'celery', 'out'),
        'data_folder_out': os.path.join(BASE_DIR, 'celery', 'out'),
        'data_folder_processed': os.path.join(BASE_DIR, 'celery', 'processed'),
    }
    CELERY_RESULT_BACKEND = f'file://{os.path.join(BASE_DIR, "celery", "results")}'
    
    # LiFi Handoff Simulation Settings
    HANDOFF_SESSION_TIMEOUT = 86400  # 24 hours
    OPTICAL_ZONES = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D', 'ER', 'ICU', 'OT', 'Reception']
    
    # Role Definitions
    ROLES = {
        'admin': 'Hospital Administrator',
        'asset_manager': 'Asset Management Officer',
        'user': 'Hospital User'
    }
    
    # Encryption Settings
    ENCRYPTION_ALGORITHM = 'Fernet-AES128'
    KEY_ROTATION_ENABLED = False  # Static key per requirements

# Create necessary directories
def create_directories():
    """Create required directories if they don't exist"""
    directories = [
        os.path.join(Config.BASE_DIR, 'data'),
        Config.UPLOAD_FOLDER,
        os.path.join(Config.BASE_DIR, 'celery', 'out'),
        os.path.join(Config.BASE_DIR, 'celery', 'processed'),
        os.path.join(Config.BASE_DIR, 'celery', 'results'),
        os.path.join(Config.BASE_DIR, 'static', 'css'),
        os.path.join(Config.BASE_DIR, 'static', 'js'),
        os.path.join(Config.BASE_DIR, 'templates', 'auth'),
        os.path.join(Config.BASE_DIR, 'templates', 'admin'),
        os.path.join(Config.BASE_DIR, 'templates', 'asset_manager'),
        os.path.join(Config.BASE_DIR, 'templates', 'user'),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

if __name__ == '__main__':
    create_directories()
    print("Directories created successfully!")
    print("Encryption key loaded from environment.")
