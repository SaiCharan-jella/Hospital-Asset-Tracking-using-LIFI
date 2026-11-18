"""
Main Flask Application for Hospital LiFi Handoff System
Handles all routes for authentication and role-specific pages
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from tinydb import where
import os
from datetime import datetime
from io import BytesIO

# Import local modules
import config
from config import Config, create_directories
from database import db
import routing_protocols
from routing_protocols import compare_routing_protocols
from security import security
from middleware import login_required, role_required, approved_required, check_file_access, get_current_user
from tasks import start_scheduler, log_secure_transfer
from utils import *

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Create necessary directories
create_directories()

# Start background scheduler
start_scheduler()

# ==================== Authentication Routes ====================

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        email = request.form.get('email')
        
        # Validate input
        if not username or not password or not role:
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if db.get_user(username):
            flash('Username already exists.', 'danger')
            return redirect(url_for('signup'))
        
        # Hash password and create user
        password_hash = security.hash_password(password)
        db.create_user(username, password_hash, role, email)
        
        flash('Account created successfully! Please wait for admin approval.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/signup.html', roles=Config.ROLES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.get_user(username)
        
        if user and security.verify_password(password, user['password_hash']):
            session['username'] = username
            session['role'] = user['role']
            session['approved'] = user.get('approved', False)
            
            if not user.get('approved', False) and user['role'] != 'admin':
                return redirect(url_for('pending_approval'))
            
            flash(f'Welcome, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/pending-approval')
@login_required
def pending_approval():
    """Pending approval page"""
    return render_template('auth/pending_approval.html')

# ==================== Dashboard Route ====================

@app.route('/dashboard')
@login_required
@approved_required
def dashboard():
    """Main dashboard - redirect to role-specific dashboard"""
    role = session.get('role')
    
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'asset_manager':
        return redirect(url_for('asset_manager_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

# ==================== Admin Routes ====================

@app.route('/admin/dashboard')
@role_required('admin')
@approved_required
def admin_dashboard():
    """Admin Dashboard - Page 1"""
    stats = db.get_statistics()
    active_sessions = db.get_active_handoff_sessions()
    all_assets = db.get_all_assets()
    optical_zones = db.get_all_zones()  # Get from database
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         active_sessions=active_sessions,
                         assets=all_assets,
                         optical_zones=optical_zones)

@app.route('/admin/user-control', methods=['GET', 'POST'])
@role_required('admin')
@approved_required
def admin_user_control():
    """User & Asset Manager Control - Page 2"""
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        
        if action == 'approve':
            db.approve_user(username)
            flash(f'User {username} approved successfully!', 'success')
        elif action == 'grant_secret':
            db.update_shared_secret_access(username, True)
            flash(f'Shared secret access granted to {username}.', 'success')
        elif action == 'revoke_secret':
            db.update_shared_secret_access(username, False)
            flash(f'Shared secret access revoked from {username}.', 'warning')
        
        return redirect(url_for('admin_user_control'))
    
    all_users = db.get_all_users()
    pending_users = db.get_pending_users()
    
    return render_template('admin/user_control.html',
                         all_users=all_users,
                         pending_users=pending_users)

@app.route('/admin/file-oversight')
@role_required('admin')
@approved_required
def admin_file_oversight():
    """Secure File Oversight - Page 3"""
    all_files = db.get_all_files()
    # Attach handoff status to each file
    for file in all_files:
        if 'handoff_session_id' in file:
            log = db.handoff_logs.get(where('session_id') == file['handoff_session_id'])
            file['handoff_status'] = log.get('status') if log else 'unknown'
        else:
            file['handoff_status'] = 'unknown'
    return render_template('admin/file_oversight.html', files=all_files)

@app.route('/admin/handoff-logs')
@role_required('admin')
@approved_required
def admin_handoff_logs():
    """LiFi Handoff Logs - Page 4"""
    # Only show unresolved handoffs (pending, unstable, failed, etc.)
    logs = db.get_unresolved_handoffs()
    # Sort by timestamp
    logs = sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template('admin/handoff_logs.html', logs=logs)

@app.route('/admin/key-management')
@role_required('admin')
@approved_required
def admin_key_management():
    """Key & Policy Management - Page 5"""
    masked_key = security.get_static_key_display()
    return render_template('admin/key_management.html',
                         masked_key=masked_key,
                         roles=Config.ROLES)

# ==================== Asset Manager Routes ====================

@app.route('/asset-manager/dashboard')
@role_required('asset_manager')
@approved_required
def asset_manager_dashboard():
    """Asset Dashboard - Page 1"""
    all_assets = db.get_all_assets()
    stats = db.get_statistics()
    optical_zones = db.get_all_zones()  # Get from database instead of Config
    
    return render_template('asset_manager/dashboard.html',
                         assets=all_assets,
                         stats=stats,
                         optical_zones=optical_zones)

@app.route('/asset-manager/file-reception')
@role_required('asset_manager')
@approved_required
def asset_manager_file_reception():
    """Encrypted File Reception - Page 2"""
    shared_files = db.get_files_shared_with_role('asset_manager')
    # Attach handoff status to each file
    for file in shared_files:
        if 'handoff_session_id' in file:
            log = db.handoff_logs.get(where('session_id') == file['handoff_session_id'])
            file['handoff_status'] = log.get('status') if log else 'unknown'
        else:
            file['handoff_status'] = 'unknown'
    return render_template('asset_manager/file_reception.html', files=shared_files)

@app.route('/asset-manager/reports-upload', methods=['GET', 'POST'])
@role_required('asset_manager')
@approved_required
def asset_manager_reports_upload():
    """Secure Asset Reports Upload - Page 3"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        is_valid, error = validate_upload_file(file)
        
        if not is_valid:
            flash(error, 'danger')
            return redirect(request.url)
        
        # Save and encrypt file
        filename = secure_filename(file.filename)
        temp_path = os.path.join(Config.UPLOAD_FOLDER, f'temp_{filename}')
        file.save(temp_path)
        
        encrypted_info = security.encrypt_file(temp_path, filename)
        
        # Create handoff session
        session_id = security.generate_handoff_session_id()
        
        # Store file metadata
        file_data = {
            'file_id': encrypted_info['file_id'],
            'original_filename': filename,
            'encrypted_path': encrypted_info['encrypted_path'],
            'uploader': session['username'],
            'uploader_role': 'asset_manager',
            'shared_with': ['admin', 'user'],
            'encryption_metadata': {
                'algorithm': Config.ENCRYPTION_ALGORITHM,
                'integrity_hash': encrypted_info['integrity_hash'],
                'file_size': encrypted_info['file_size']
            },
            'handoff_session_id': session_id
        }
        
        db.create_encrypted_file(file_data)
        
        # Log handoff as pending (Universal Handoff Logging)
        db.create_handoff_log({
            'session_id': session_id,
            'from_role': 'asset_manager',
            'to_role': 'admin,user',
            'status': 'pending', # Changed from 'stable' to 'pending'
            'integrity_verified': True,
            'details': f'Asset Management Report: {filename}'
        })
        
        flash(f'File "{filename}" encrypted and uploaded successfully!', 'success')
        return redirect(url_for('asset_manager_reports_upload'))
    
    my_uploads = db.get_files_by_uploader(session['username'])
    return render_template('asset_manager/reports_upload.html', uploads=my_uploads)

@app.route('/asset-manager/handoff-validation', methods=['GET', 'POST'])
@role_required('asset_manager')
@approved_required
def asset_manager_handoff_validation():
    """Optical Handoff Validation - Page 4"""
    if request.method == 'POST':
        session_id = request.form.get('session_id')
        action = request.form.get('action')
        
        if action == 'approve':
            db.update_handoff_status(session_id, 'completed') # Changed from 'stable' to 'completed'
            flash('Handoff validated and completed successfully!', 'success')
        elif action == 'reject':
            db.update_handoff_status(session_id, 'failed') # Changed from 'unstable' to 'failed'
            flash('Handoff rejected and marked as failed.', 'danger')
        
        return redirect(url_for('asset_manager_handoff_validation'))
    
    # Only show pending handoffs for validation
    pending_sessions = db.get_active_handoff_sessions(status='pending')
    return render_template('asset_manager/handoff_validation.html', sessions=pending_sessions)

@app.route('/asset-manager/secret-exchange', methods=['GET', 'POST'])
@role_required('asset_manager')
@approved_required
def asset_manager_secret_exchange():
    """Shared Secret Exchange Panel - Page 5"""
    if request.method == 'POST':
        to_role = request.form.get('to_role')
        message = request.form.get('message')
        
        encrypted_msg = security.encrypt_message(message)
        
        session_id = security.generate_handoff_session_id()
        db.create_shared_secret({
            'from_role': 'asset_manager',
            'from_user': session['username'],
            'to_role': to_role,
            'encrypted_message': encrypted_msg['encrypted_message'],
            'integrity_hash': encrypted_msg['integrity_hash'],
            'handoff_session_id': session_id
        })

        # Create handoff log for secret exchange
        db.create_handoff_log({
            'session_id': session_id,
            'from_role': 'asset_manager',
            'to_role': to_role,
            'status': 'pending',
            'integrity_verified': True,
            'details': f'Encrypted message sent to {to_role}'
        })
        
        flash('Encrypted message sent successfully!', 'success')
        return redirect(url_for('asset_manager_secret_exchange'))
    
    received_secrets = db.get_secrets_for_role('asset_manager')
    return render_template('asset_manager/secret_exchange.html',
                         secrets=received_secrets,
                         roles=Config.ROLES)

# ==================== Hospital User Routes ====================

@app.route('/user/dashboard')
@role_required('user')
@approved_required
def user_dashboard():
    """User Dashboard - Page 1"""
    my_files = db.get_files_by_uploader(session['username'])
    shared_files = db.get_files_shared_with_role('user')
    stats = db.get_statistics()
    
    return render_template('user/dashboard.html',
                         my_files=my_files,
                         shared_files=shared_files,
                         stats=stats)

@app.route('/user/file-upload', methods=['GET', 'POST'])
@role_required('user')
@approved_required
def user_file_upload():
    """Secure File Upload - Page 2"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        is_valid, error = validate_upload_file(file)
        
        if not is_valid:
            flash(error, 'danger')
            return redirect(request.url)
        
        # Save and encrypt file
        filename = secure_filename(file.filename)
        temp_path = os.path.join(Config.UPLOAD_FOLDER, f'temp_{filename}')
        file.save(temp_path)
        
        encrypted_info = security.encrypt_file(temp_path, filename)
        
        # Create handoff session
        session_id = security.generate_handoff_session_id()
        
        # Store file metadata
        file_data = {
            'file_id': encrypted_info['file_id'],
            'original_filename': filename,
            'encrypted_path': encrypted_info['encrypted_path'],
            'uploader': session['username'],
            'uploader_role': 'user',
            'shared_with': ['admin', 'asset_manager'],
            'encryption_metadata': {
                'algorithm': Config.ENCRYPTION_ALGORITHM,
                'integrity_hash': encrypted_info['integrity_hash'],
                'file_size': encrypted_info['file_size']
            },
            'handoff_session_id': session_id
        }
        
        db.create_encrypted_file(file_data)
        
        # Log handoff as pending (Universal Handoff Logging)
        db.create_handoff_log({
            'session_id': session_id,
            'from_role': 'user',
            'to_role': 'admin,asset_manager',
            'status': 'pending', # Changed from 'stable' to 'pending'
            'integrity_verified': True,
            'details': f'File uploaded: {filename}'
        })
        
        flash(f'File "{filename}" encrypted and uploaded successfully!', 'success')
        flash(f'Handoff Session ID: {session_id}', 'info')
        return redirect(url_for('user_file_upload'))
    
    my_uploads = db.get_files_by_uploader(session['username'])
    return render_template('user/file_upload.html', uploads=my_uploads)

@app.route('/user/file-download')
@role_required('user')
@approved_required
def user_file_download():
    """Encrypted File Download - Page 3"""
    my_files = db.get_files_by_uploader(session['username'])
    # Attach handoff status to each file
    for file in my_files:
        if 'handoff_session_id' in file:
            log = db.handoff_logs.get(where('session_id') == file['handoff_session_id'])
            file['handoff_status'] = log.get('status') if log else 'unknown'
        else:
            file['handoff_status'] = 'unknown'
    return render_template('user/file_download.html', files=my_files)

@app.route('/user/asset-manager-access')
@role_required('user')
@approved_required
def user_asset_manager_access():
    """Asset Manager File Access - Page 4"""
    my_files = db.get_files_by_uploader(session['username'])
    return render_template('user/asset_manager_access.html', files=my_files)

@app.route('/user/confidential-data', methods=['GET', 'POST'])
@role_required('user')
@approved_required
def user_confidential_data():
    """Shared Confidential Data - Page 5"""
    if request.method == 'POST':
        to_role = request.form.get('to_role')
        message = request.form.get('message')
        
        encrypted_msg = security.encrypt_message(message)
        
        session_id = security.generate_handoff_session_id()
        db.create_shared_secret({
            'from_role': 'user',
            'from_user': session['username'],
            'to_role': to_role,
            'encrypted_message': encrypted_msg['encrypted_message'],
            'integrity_hash': encrypted_msg['integrity_hash'],
            'handoff_session_id': session_id
        })

        # Create handoff log for secret exchange
        db.create_handoff_log({
            'session_id': session_id,
            'from_role': 'user',
            'to_role': to_role,
            'status': 'pending',
            'integrity_verified': True,
            'details': f'Confidential message sent to {to_role}'
        })
        
        flash('Encrypted message sent successfully!', 'success')
        return redirect(url_for('user_confidential_data'))
    
    received_secrets = db.get_secrets_for_role('user')
    return render_template('user/confidential_data.html',
                         secrets=received_secrets,
                         roles=Config.ROLES)

# ==================== File Operations ====================

@app.route('/download-file/<int:file_id>')
@login_required
@approved_required
def download_file(file_id):
    """Download encrypted file"""
    username = session['username']
    role = session['role']
    
    # Check access
    if not check_file_access(username, role, file_id):
        flash('You do not have permission to download this file.', 'danger')
        return redirect(url_for('dashboard'))
    
    file_data = db.get_file(file_id)
    if not file_data:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Log download
    db.add_file_download_log(file_id, username, role)
    
    # Create handoff log
    db.create_handoff_log({
        'session_id': file_data.get('handoff_session_id', 'UNKNOWN'),
        'from_role': file_data.get('uploader_role'),
        'to_role': role,
        'status': 'download_completed',
        'integrity_verified': True,
        'details': f'File downloaded by {username}'
    })
    
    # Send encrypted file
    return send_file(
        file_data['encrypted_path'],
        as_attachment=True,
        download_name=f"{file_data['original_filename']}.encrypted"
    )

@app.route('/decrypt-file/<int:file_id>')
@login_required
@approved_required
def decrypt_file(file_id):
    """Decrypt and download file (admin privilege)"""
    username = session['username']
    role = session['role']
    
    # Only admin and asset_manager can decrypt files
    if role not in ['admin', 'asset_manager'] and not check_file_access(username, role, file_id):
        flash('You do not have permission to decrypt this file.', 'danger')
        return redirect(url_for('dashboard'))
    
    file_data = db.get_file(file_id)
    if not file_data:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if handoff is approved (Universal Handoff Validation)
    session_id = file_data.get('handoff_session_id')
    if session_id:
        log = db.handoff_logs.get(where('session_id') == session_id)
        if log and log.get('status') != 'completed':
            flash('This file transfer is still pending Asset Manager approval.', 'warning')
            return redirect(url_for('dashboard'))
    
    try:
        # Decrypt file
        decrypted_data = security.decrypt_file(file_data['encrypted_path'])
        
        # Log decryption
        db.create_handoff_log({
            'session_id': file_data.get('handoff_session_id', 'UNKNOWN'),
            'from_role': file_data.get('uploader_role'),
            'to_role': role,
            'status': 'decrypted',
            'integrity_verified': True,
            'details': f'File decrypted by {username} ({role})'
        })
        
        # Send decrypted file
        return send_file(
            BytesIO(decrypted_data),
            as_attachment=True,
            download_name=file_data['original_filename']
        )
    except Exception as e:
        flash(f'Decryption failed: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/decrypt-message/<int:secret_id>')
@login_required
@approved_required
def decrypt_message(secret_id):
    """Decrypt shared secret message"""
    secret = db.shared_secrets.get(doc_id=secret_id)
    
    if not secret:
        return jsonify({'error': 'Message not found'}), 404
    
    # Check if handoff is approved (Universal Handoff Validation)
    session_id = secret.get('handoff_session_id')
    if session_id:
        log = db.handoff_logs.get(where('session_id') == session_id)
        if log and log.get('status') != 'completed':
            return jsonify({'error': 'This message transfer is still pending Asset Manager approval.'}), 403
    
    # Check if user's role matches recipient
    if session['role'] != secret.get('to_role'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    encrypted_msg_dict = {
        'encrypted_message': secret.get('encrypted_message'),
        'integrity_hash': secret.get('integrity_hash')
    }
    
    decrypted = security.decrypt_message(encrypted_msg_dict)
    
    if decrypted is None:
        return jsonify({'error': 'Integrity verification failed'}), 400
    
    # Mark as read
    db.mark_secret_read(secret_id)
    
    return jsonify({
        'success': True,
        'message': decrypted,
        'from': secret.get('from_user', 'System'),
        'timestamp': secret.get('timestamp')
    })

# ==================== API Endpoints ====================

@app.route('/api/statistics')
@login_required
@approved_required
def api_statistics():
    """Get real-time statistics"""
    stats = db.get_statistics()
    return jsonify(stats)

@app.route('/api/active-sessions')
@login_required
@approved_required
def api_active_sessions():
    """Get active handoff sessions"""
    sessions = db.get_active_handoff_sessions()
    return jsonify(sessions)

# ==================== Template Filters ====================

@app.template_filter('format_timestamp')
def template_format_timestamp(iso_timestamp):
    return format_timestamp(iso_timestamp)

@app.template_filter('format_file_size')
def template_format_file_size(size_bytes):
    return format_file_size(size_bytes)

@app.template_filter('role_display')
def template_role_display(role_code):
    return get_role_display_name(role_code)

@app.template_filter('time_ago')
def template_time_ago(iso_timestamp):
    return time_ago(iso_timestamp)

@app.template_filter('zone_color')
def template_zone_color(zone):
    return get_optical_zone_color(zone)

@app.template_filter('status_class')
def template_status_class(status):
    return get_handoff_status_class(status)

@app.template_filter('datetime_format')
def template_datetime_format(iso_timestamp):
    if not iso_timestamp: return ""
    try:
        dt = datetime.fromisoformat(str(iso_timestamp))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(iso_timestamp)

# ==================== Zone Management Routes ====================

# Routing Protocol Imports fixed at top
pass

@app.route('/asset-manager/zone-activation', methods=['GET', 'POST'])
@role_required('asset_manager')
@approved_required
def asset_manager_activate_zone():
    """Zone Activation Request"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            # Create new zone
            zone_data = {
                'name': request.form.get('zone_name'),
                'location': request.form.get('zone_location'),
                'description': request.form.get('zone_description'),
                'requested_by': session['username']
            }
            db.create_zone(zone_data)
            flash('New zone creation requested! Awaiting admin approval.', 'success')
        
        elif action == 'toggle':
            # Request to activate/deactivate existing zone
            zone_id = int(request.form.get('zone_id'))
            zone = db.zones.get(doc_id=zone_id)
            
            if zone:
                current_status = zone.get('status')
                if current_status == 'active':
                    # Request deactivation
                    db.zones.update({'status': 'pending_deactivation', 'change_requested_by': session['username']}, doc_ids=[zone_id])
                    flash(f'Zone {zone["name"]} deactivation requested! Awaiting admin approval.', 'warning')
                elif current_status == 'inactive':
                    # Request activation
                    db.zones.update({'status': 'pending', 'change_requested_by': session['username']}, doc_ids=[zone_id])
                    flash(f'Zone {zone["name"]} activation requested! Awaiting admin approval.', 'info')
        
        return redirect(url_for('asset_manager_activate_zone'))
    
    all_zones = db.get_all_zones()
    active_zones = [z for z in all_zones if z.get('status') == 'active']
    pending_zones = [z for z in all_zones if z.get('status') in ['pending', 'pending_deactivation']]
    
    return render_template('asset_manager/zone_activation.html',
                         all_zones=all_zones,
                         active_zones=active_zones,
                         pending_zones=pending_zones)

@app.route('/admin/zone-approvals', methods=['GET', 'POST'])
@role_required('admin')
@approved_required
def admin_zone_approvals():
    """Zone Approval Management"""
    if request.method == 'POST':
        zone_id = int(request.form.get('zone_id'))
        action = request.form.get('action')
        
        if action == 'approve':
            zone = db.zones.get(doc_id=zone_id)
            if zone and zone.get('status') == 'pending_deactivation':
                # Approve deactivation
                db.deactivate_zone(zone_id)
                flash(f'Zone {zone["name"]} deactivated successfully!', 'warning')
            else:
                # Approve activation
                db.approve_zone(zone_id, session['username'])
                flash('Zone activated successfully!', 'success')
        
        elif action == 'reject':
            # Reject the change request
            zone = db.zones.get(doc_id=zone_id)
            if zone:
                original_status = 'active' if zone.get('status') == 'pending_deactivation' else 'inactive'
                db.zones.update({'status': original_status}, doc_ids=[zone_id])
                flash(f'Zone change request rejected. Reverted to {original_status}.', 'info')
        
        elif action == 'deactivate':
            db.deactivate_zone(zone_id)
            flash('Zone deactivated.', 'warning')
        
        return redirect(url_for('admin_zone_approvals'))
    
    all_zones = db.get_all_zones()
    pending_zones = [z for z in all_zones if z.get('status') in ['pending', 'pending_deactivation']]
    
    return render_template('admin/zone_approvals.html',
                         pending_zones=pending_zones,
                         all_zones=all_zones)

@app.route('/api/routing-comparison')
@login_required
@approved_required
def api_routing_comparison():
    """Compare DSDV vs GPSR routing protocols"""
    active_zones = db.get_active_zones()
    
    # Run comparison
    result = compare_routing_protocols('User-Zone', 'Server-Zone', active_zones)
    
    # Log routing data
    db.create_routing_log({
        'dsdv_metrics': result['dsdv']['metrics'],
        'gpsr_metrics': result['gpsr']['metrics'],
        'comparison': result['comparison']
    })
    
    return jsonify(result)

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

# ==================== Main ====================

@app.route('/admin/routing-performance')
@role_required('admin')
@approved_required
def admin_routing_performance():
    """Routing Protocol Comparison - Page 6"""
    # Trigger fresh simulation
    comparison_data = routing_protocols.routing_sim.get_comparison()
    
    # Log to database for history
    db.log_routing_metrics(comparison_data)
    
    # Get history
    history = db.get_routing_comparison(limit=5)
    
    return render_template('admin/routing_performance.html',
                         current=comparison_data,
                         history=history,
                         now_format=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    print("=" * 60)
    print("Hospital LiFi Handoff System Starting...")
    print("=" * 60)
    print(f"Database Path: {Config.DB_PATH}")
    print(f"Upload Folder: {Config.UPLOAD_FOLDER}")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5000, debug=Config.DEBUG)
