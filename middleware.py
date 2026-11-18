"""
Middleware and decorators for role-based access control
"""

from functools import wraps
from flask import session, redirect, url_for, flash, abort
from database import db
from tinydb import where

def login_required(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """
    Decorator to require specific role
    Args:
        required_role: Role name required ('admin', 'asset_manager', 'user')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            if session.get('role') != required_role:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def approved_required(f):
    """Decorator to require user account to be approved"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        user = db.get_user(session['username'])
        if not user or not user.get('approved', False):
            flash('Your account is pending approval by an administrator.', 'warning')
            return redirect(url_for('pending_approval'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_file_access(username, role, file_id):
    """
    Check if user has access to a specific file
    Args:
        username: Username requesting access
        role: User's role
        file_id: File ID to access
    Returns:
        Boolean indicating if access is granted
    """
    file_data = db.get_file(file_id)
    if not file_data:
        return False
    
    # Admin can access all files
    if role == 'admin':
        return True
    
    # Check if user uploaded the file
    if file_data.get('uploader') == username:
        return True
    
    # Check if file is shared with user's role
    if role in file_data.get('shared_with', []):
        return True
    
    return False

def check_shared_secret_access(username):
    """
    Check if user has shared secret access permission
    Args:
        username: Username to check
    Returns:
        Boolean indicating if access is granted
    """
    user = db.get_user(username)
    if not user:
        return False
    
    # Admin always has access
    if user.get('role') == 'admin':
        return True
    
    return user.get('shared_secret_access', False)

def get_current_user():
    """
    Get current logged-in user data
    Returns:
        User dictionary or None
    """
    if 'username' in session:
        return db.get_user(session['username'])
    return None

def has_permission(permission):
    """
    Check if current user has a specific permission
    Args:
        permission: Permission name to check
    Returns:
        Boolean indicating if user has permission
    """
    if 'username' not in session:
        return False
    
    user = get_current_user()
    if not user:
        return False
    
    role = user.get('role')
    role_data = db.roles.get(where('role_name') == role)
    
    if not role_data:
        return False
    
    return permission in role_data.get('permissions', [])
