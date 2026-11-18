"""
Background tasks using APScheduler and Celery
For LiFi handoff session management and encryption validation
"""

from apscheduler.schedulers.background import BackgroundScheduler
from celery import Celery
from datetime import datetime, timedelta
from database import db
from security import security
from config import Config
import os

# Initialize Celery (filesystem-based, no external broker)
celery_app = Celery('hospital_tasks')
celery_app.config_from_object(Config, namespace='CELERY')

# APScheduler instance
scheduler = BackgroundScheduler(timezone=Config.SCHEDULER_TIMEZONE)

# ==================== APScheduler Tasks ====================

def clean_expired_handoff_sessions():
    """
    Remove handoff sessions older than 24 hours
    Runs every hour
    """
    try:
        cutoff = (datetime.now() - timedelta(seconds=Config.HANDOFF_SESSION_TIMEOUT)).isoformat()
        all_logs = db.handoff_logs.all()
        
        expired_count = 0
        for log in all_logs:
            if log.get('timestamp', '') < cutoff:
                db.handoff_logs.remove(doc_ids=[log.doc_id])
                expired_count += 1
        
        print(f"[APScheduler] Cleaned {expired_count} expired handoff sessions")
        
        # Log cleanup action
        db.create_handoff_log({
            'session_id': 'CLEANUP',
            'from_role': 'system',
            'to_role': 'system',
            'status': 'cleanup_completed',
            'integrity_verified': True,
            'details': f'Removed {expired_count} expired sessions'
        })
    except Exception as e:
        print(f"[APScheduler] Error cleaning sessions: {e}")

def validate_encryption_integrity():
    """
    Validate integrity of all encrypted files
    Runs every 6 hours
    """
    try:
        all_files = db.get_all_files()
        validated = 0
        corrupted = 0
        
        for file_data in all_files:
            file_id = file_data.doc_id
            encrypted_path = file_data.get('encrypted_path')
            expected_hash = file_data.get('encryption_metadata', {}).get('integrity_hash')
            
            if not encrypted_path or not expected_hash:
                continue
            
            if not os.path.exists(encrypted_path):
                corrupted += 1
                # Log corrupted file
                db.create_handoff_log({
                    'session_id': f'INTEGRITY-{file_id}',
                    'from_role': 'system',
                    'to_role': 'admin',
                    'status': 'file_missing',
                    'integrity_verified': False,
                    'details': f'File not found: {file_data.get("original_filename")}'
                })
                continue
            
            if security.verify_file_integrity(encrypted_path, expected_hash):
                validated += 1
            else:
                corrupted += 1
                db.create_handoff_log({
                    'session_id': f'INTEGRITY-{file_id}',
                    'from_role': 'system',
                    'to_role': 'admin',
                    'status': 'integrity_failed',
                    'integrity_verified': False,
                    'details': f'Integrity check failed: {file_data.get("original_filename")}'
                })
        
        print(f"[APScheduler] Encryption validation: {validated} valid, {corrupted} corrupted")
        
        # Log validation action
        db.create_handoff_log({
            'session_id': 'VALIDATION',
            'from_role': 'system',
            'to_role': 'system',
            'status': 'validation_completed',
            'integrity_verified': True,
            'details': f'Validated {validated} files, found {corrupted} corrupted'
        })
    except Exception as e:
        print(f"[APScheduler] Error validating encryption: {e}")

def generate_handoff_statistics():
    """
    Generate and update handoff statistics
    Runs every 30 minutes
    """
    try:
        stats = db.get_statistics()
        active_sessions = db.get_active_handoff_sessions()
        
        # Calculate handoff success rate
        successful = sum(1 for log in active_sessions if log.get('status') == 'stable')
        total = len(active_sessions)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"[APScheduler] Statistics updated: {total} active sessions, {success_rate:.1f}% success rate")
    except Exception as e:
        print(f"[APScheduler] Error generating statistics: {e}")

# ==================== Celery Tasks ====================

@celery_app.task(name='tasks.encrypt_file_async')
def encrypt_file_async(file_id):
    """
    Background file encryption task
    Args:
        file_id: ID of file to encrypt
    """
    try:
        file_data = db.get_file(file_id)
        if not file_data:
            return {'status': 'error', 'message': 'File not found'}
        
        # File should already be encrypted by upload handler
        # This task is for additional processing if needed
        
        return {'status': 'success', 'file_id': file_id}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@celery_app.task(name='tasks.decrypt_file_async')
def decrypt_file_async(file_id, user_id):
    """
    Background file decryption task
    Args:
        file_id: ID of file to decrypt
        user_id: User requesting decryption
    """
    try:
        file_data = db.get_file(file_id)
        if not file_data:
            return {'status': 'error', 'message': 'File not found'}
        
        encrypted_path = file_data.get('encrypted_path')
        decrypted_data = security.decrypt_file(encrypted_path)
        
        return {
            'status': 'success',
            'file_id': file_id,
            'size': len(decrypted_data)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@celery_app.task(name='tasks.log_secure_transfer')
def log_secure_transfer(handoff_data):
    """
    Log secure transfer event
    Args:
        handoff_data: Dictionary with transfer details
    """
    try:
        db.create_handoff_log(handoff_data)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@celery_app.task(name='tasks.send_encrypted_notification')
def send_encrypted_notification(user_id, message):
    """
    Send encrypted notification to user
    Args:
        user_id: User ID to notify
        message: Message to encrypt and send
    """
    try:
        encrypted_msg = security.encrypt_message(message)
        
        # Store as shared secret notification
        db.create_shared_secret({
            'from_role': 'system',
            'to_role': 'notification',
            'encrypted_message': encrypted_msg['encrypted_message'],
            'integrity_hash': encrypted_msg['integrity_hash'],
            'recipient': user_id
        })
        
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# ==================== Scheduler Initialization ====================

def start_scheduler():
    """Start APScheduler with all jobs"""
    if not scheduler.running:
        # Add jobs
        scheduler.add_job(
            func=clean_expired_handoff_sessions,
            trigger='interval',
            hours=1,
            id='clean_sessions',
            name='Clean expired handoff sessions',
            replace_existing=True
        )
        
        scheduler.add_job(
            func=validate_encryption_integrity,
            trigger='interval',
            hours=6,
            id='validate_encryption',
            name='Validate encryption integrity',
            replace_existing=True
        )
        
        scheduler.add_job(
            func=generate_handoff_statistics,
            trigger='interval',
            minutes=30,
            id='generate_stats',
            name='Generate handoff statistics',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        print("[APScheduler] Background scheduler started successfully")

def stop_scheduler():
    """Stop APScheduler"""
    if scheduler.running:
        scheduler.shutdown()
        print("[APScheduler] Background scheduler stopped")
