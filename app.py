"""
Main Flask application for Lala Panel
"""
import os
import hashlib
import time
import subprocess
import shutil
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

from config import Config
from database import Database
from site_manager import SiteManager, DatabaseManager, UserManager

app = Flask(__name__)
app.config.from_object(Config)

# Template filters
@app.template_filter('os_info')
def os_info_filter(value):
    """Template filter to display OS information. The value parameter is required by Jinja2 but not used."""
    import platform
    return f"{platform.system()} {platform.release()}"

@app.template_filter('python_version')
def python_version_filter(value):
    """Template filter to display Python version. The value parameter is required by Jinja2 but not used."""
    import sys
    return f"{sys.version.split()[0]}"

@app.template_filter('uptime')
def uptime_filter(value):
    """Template filter to display system uptime. The value parameter is required by Jinja2 but not used."""
    try:
        import psutil
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except:
        return "Unknown"

# Template context processor
@app.context_processor
def inject_now():
    """Inject current datetime into all templates"""
    return {'now': datetime.now}

# Initialize components lazily to allow testing
db = None
site_manager = None
db_manager = None
user_manager = None

def init_components():
    """Initialize application components"""
    global db, site_manager, db_manager, user_manager
    if db is None:
        db = Database(app.config['DATABASE_PATH'])
        site_manager = SiteManager(app.config, db)
        db_manager = DatabaseManager(app.config)
        user_manager = UserManager(app.config)
    return db, site_manager, db_manager, user_manager

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    init_components()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (int(user_id),))
        user_data = cursor.fetchone()
    if user_data:
        return User(user_data['id'], user_data['username'])
    return None

# Rate limiting decorator
def check_rate_limit(ip_address, max_attempts=5):
    """Check if IP has exceeded login attempts"""
    attempts = db.get_recent_login_attempts(ip_address, minutes=15)
    return attempts < max_attempts

# Routes
@app.route('/')
def index():
    """Redirect to dashboard or login"""
    init_components()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    init_components()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        ip_address = request.remote_addr
        
        # Check rate limit
        if not check_rate_limit(ip_address):
            flash('Too many login attempts. Please try again later.', 'error')
            return render_template('login.html')
        
        # Record login attempt
        db.record_login_attempt(ip_address)
        
        # Verify credentials
        user_data = db.get_user(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard showing all sites"""
    init_components()
    sites = db.get_all_sites()
    return render_template('dashboard.html', sites=sites)

@app.route('/sites/create', methods=['GET', 'POST'])
@login_required
def create_site():
    """Create a new site"""
    init_components()
    if request.method == 'POST':
        domain = request.form.get('domain')
        php_version = request.form.get('php_version')
        ssl_mode = request.form.get('ssl_mode', 'none')
        create_db = request.form.get('create_database') == 'on'
        
        # Get PHP settings
        php_settings = {
            'upload_max_filesize': request.form.get('upload_max_filesize', '100M'),
            'memory_limit': request.form.get('memory_limit', '256M'),
            'max_execution_time': request.form.get('max_execution_time', '60'),
            'max_input_time': request.form.get('max_input_time', '60')
        }
        
        try:
            # Check if site already exists
            if db.get_site_by_domain(domain):
                flash(f'Site {domain} already exists', 'error')
                return render_template('create_site.html', 
                                     php_versions=app.config['AVAILABLE_PHP_VERSIONS'])
            
            # Create site directories
            site_manager.create_site_directories(domain)
            
            # Create nginx config (without SSL initially)
            site_manager.create_nginx_config(domain, php_version, ssl_enabled=False, php_settings=php_settings)
            
            # Enable site
            site_manager.enable_site(domain)
            
            # Handle SSL based on mode
            ssl_enabled = False
            if ssl_mode == 'auto':
                try:
                    site_manager.request_ssl_certificate(domain, include_www=True)
                    # Recreate nginx config with SSL
                    site_manager.create_nginx_config(domain, php_version, ssl_enabled=True, php_settings=php_settings)
                    site_manager.enable_site(domain)
                    ssl_enabled = True
                    flash(f'SSL certificate obtained successfully for {domain} and www.{domain}', 'success')
                except Exception as e:
                    flash(f'Warning: SSL certificate request failed: {str(e)}. You can configure SSL manually later.', 'warning')
            elif ssl_mode == 'domain_only':
                try:
                    site_manager.request_ssl_certificate(domain, include_www=False)
                    # Recreate nginx config with SSL
                    site_manager.create_nginx_config(domain, php_version, ssl_enabled=True, php_settings=php_settings)
                    site_manager.enable_site(domain)
                    ssl_enabled = True
                    flash(f'SSL certificate obtained successfully for {domain} (without www)', 'success')
                except Exception as e:
                    flash(f'Warning: SSL certificate request failed: {str(e)}. You can configure SSL manually later.', 'warning')
            elif ssl_mode == 'manual':
                flash('Site created. Configure SSL manually via the site management page.', 'info')
            
            # Create database record
            site_id = db.create_site(domain, php_version, ssl_enabled=ssl_enabled)
            
            # Create database if requested
            if create_db:
                # Generate unique database name with hash to avoid conflicts
                domain_base = domain.replace('.', '_').replace('-', '_')
                hash_suffix = hashlib.md5(f"{domain}{time.time()}".encode()).hexdigest()[:6]
                db_name = f"{domain_base}_{hash_suffix}"[:64]  # MySQL max identifier length
                db_user = f"user_{hash_suffix}"
                db_password = db_manager.generate_password()
                
                try:
                    db_manager.create_database(db_name, db_user, db_password)
                    db.create_database(site_id, db_name, db_user, db_password)
                    flash(f'Database created: {db_name} (User: {db_user}, Password: {db_password})', 'success')
                except Exception as e:
                    flash(f'Warning: Database creation failed: {str(e)}', 'warning')
            
            # Create SSH/FTP user if requested
            create_ftp = request.form.get('create_ftp_user') == 'on'
            if create_ftp:
                ftp_username = request.form.get('ftp_username', '')
                ftp_password = request.form.get('ftp_password', '')
                access_type = request.form.get('access_type', 'ftp')
                
                # Auto-generate username if not provided
                if not ftp_username:
                    domain_base = domain.replace('.', '').replace('-', '')[:10]
                    hash_suffix = hashlib.md5(f"{domain}{time.time()}".encode()).hexdigest()[:4]
                    ftp_username = f"ftp_{domain_base}_{hash_suffix}"[:32]
                
                # Auto-generate password if not provided
                if not ftp_password:
                    ftp_password = user_manager.generate_password()
                
                try:
                    user_manager.create_ftp_user(ftp_username, ftp_password, domain, access_type)
                    db.create_ftp_user(site_id, ftp_username, access_type)
                    flash(f'SSH/FTP User created: {ftp_username} (Password: {ftp_password})', 'success')
                except Exception as e:
                    flash(f'Warning: SSH/FTP user creation failed: {str(e)}', 'warning')
            
            flash(f'Site {domain} created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error creating site: {str(e)}', 'error')
            return render_template('create_site.html', 
                                 php_versions=app.config['AVAILABLE_PHP_VERSIONS'])
    
    return render_template('create_site.html', 
                         php_versions=app.config['AVAILABLE_PHP_VERSIONS'])

@app.route('/sites/<int:site_id>')
@login_required
def site_detail(site_id):
    """Site detail and management"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    databases = db.get_databases_for_site(site_id)
    return render_template('site_detail.html', 
                         site=site, 
                         databases=databases,
                         php_versions=app.config['AVAILABLE_PHP_VERSIONS'])

@app.route('/sites/<int:site_id>/update-php', methods=['POST'])
@login_required
def update_site_php(site_id):
    """Update PHP version for a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    new_php_version = request.form.get('php_version')
    
    try:
        site_manager.update_php_version(site['domain'], new_php_version)
        db.update_site(site_id, php_version=new_php_version)
        flash(f'PHP version updated to {new_php_version}', 'success')
    except Exception as e:
        flash(f'Error updating PHP version: {str(e)}', 'error')
    
    return redirect(url_for('site_detail', site_id=site_id))

@app.route('/sites/<int:site_id>/request-ssl', methods=['POST'])
@login_required
def request_ssl(site_id):
    """Request SSL certificate for a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    ssl_mode = request.form.get('ssl_mode', 'auto')
    
    try:
        # Request SSL certificate
        include_www = ssl_mode == 'auto'
        site_manager.request_ssl_certificate(site['domain'], include_www=include_www)
        
        # Update nginx config with SSL
        site_manager.create_nginx_config(site['domain'], site['php_version'], ssl_enabled=True)
        site_manager.enable_site(site['domain'])
        
        # Update database
        db.update_site(site_id, ssl_enabled=True)
        
        flash(f'SSL certificate obtained successfully for {site["domain"]}', 'success')
    except Exception as e:
        flash(f'Error requesting SSL certificate: {str(e)}', 'error')
    
    return redirect(url_for('site_detail', site_id=site_id))

@app.route('/sites/<int:site_id>/upload-ssl', methods=['POST'])
@login_required
def upload_ssl(site_id):
    """Upload manual SSL certificates"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    cert_file = request.files.get('cert_file')
    key_file = request.files.get('key_file')
    
    if not cert_file or not key_file:
        flash('Both certificate and key files are required', 'error')
        return redirect(url_for('site_detail', site_id=site_id))
    
    try:
        import os
        
        # Create SSL directory for manual certs
        ssl_dir = f"/etc/letsencrypt/live/{site['domain']}"
        os.makedirs(ssl_dir, exist_ok=True)
        
        # Save certificate files
        cert_path = os.path.join(ssl_dir, 'fullchain.pem')
        key_path = os.path.join(ssl_dir, 'privkey.pem')
        
        cert_file.save(cert_path)
        key_file.save(key_path)
        
        # Set proper permissions
        os.chmod(cert_path, 0o644)
        os.chmod(key_path, 0o600)
        
        # Update nginx config with SSL
        site_manager.create_nginx_config(site['domain'], site['php_version'], ssl_enabled=True)
        site_manager.enable_site(site['domain'])
        
        # Update database
        db.update_site(site_id, ssl_enabled=True)
        
        flash('SSL certificates uploaded and configured successfully', 'success')
    except Exception as e:
        flash(f'Error uploading SSL certificates: {str(e)}', 'error')
    
    return redirect(url_for('site_detail', site_id=site_id))

@app.route('/sites/<int:site_id>/delete', methods=['POST'])
@login_required
def delete_site(site_id):
    """Delete a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get associated databases
        databases = db.get_databases_for_site(site_id)
        
        # Disable site
        site_manager.disable_site(site['domain'])
        
        # Delete databases
        for database in databases:
            try:
                db_manager.delete_database(database['db_name'], database['db_user'])
            except:
                pass  # Continue even if database deletion fails
        
        # Delete site files
        site_manager.delete_site_files(site['domain'])
        
        # Delete from database
        db.delete_site(site_id)
        
        flash(f'Site {site["domain"]} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting site: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/sites/<int:site_id>/vhost')
@login_required
def edit_vhost(site_id):
    """Edit nginx vhost configuration"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Read current nginx config
    config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], site['domain'])
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()
    except FileNotFoundError:
        flash('Nginx configuration file not found', 'error')
        return redirect(url_for('site_detail', site_id=site_id))
    except Exception as e:
        flash(f'Error reading configuration: {str(e)}', 'error')
        return redirect(url_for('site_detail', site_id=site_id))
    
    return render_template('edit_vhost.html', site=site, config_content=config_content)

@app.route('/sites/<int:site_id>/vhost/save', methods=['POST'])
@login_required
def save_vhost(site_id):
    """Save nginx vhost configuration"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    config_content = request.form.get('config_content', '')
    config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], site['domain'])
    
    try:
        # Write configuration to file
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Test nginx configuration
        result = subprocess.run(
            ['/usr/sbin/nginx', '-t'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            flash(f'Configuration saved but nginx test failed: {result.stderr}', 'warning')
        else:
            # Reload nginx
            subprocess.run(['/usr/bin/systemctl', 'reload', 'nginx'], check=False)
            flash('Nginx configuration updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
    
    return redirect(url_for('edit_vhost', site_id=site_id))

@app.route('/sites/<int:site_id>/vhost/test', methods=['POST'])
@login_required
def test_nginx_config(site_id):
    """Test nginx configuration"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    config_content = request.form.get('config_content', '')
    config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], site['domain'])
    
    # Save to temporary file
    temp_path = config_path + '.tmp'
    try:
        with open(temp_path, 'w') as f:
            f.write(config_content)
        
        # Backup original
        backup_path = config_path + '.backup'
        shutil.copy2(config_path, backup_path)
        
        # Replace with new config
        shutil.move(temp_path, config_path)
        
        # Test
        result = subprocess.run(
            ['/usr/sbin/nginx', '-t'],
            capture_output=True,
            text=True
        )
        
        # Restore original
        shutil.move(backup_path, config_path)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'output': result.stderr})
        else:
            return jsonify({'success': False, 'error': result.stderr})
    
    except Exception as e:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(backup_path):
            shutil.move(backup_path, config_path)
        
        return jsonify({'success': False, 'error': str(e)})

@app.route('/sites/<int:site_id>/php-ini')
@login_required
def edit_php_ini(site_id):
    """Edit PHP settings for a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Parse current PHP settings from nginx config
    config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], site['domain'])
    php_settings = {
        'upload_max_filesize': '100M',
        'post_max_size': '100M',
        'memory_limit': '256M',
        'max_execution_time': '60',
        'max_input_time': '60',
        'max_input_vars': '1000'
    }
    
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()
            
        # Extract PHP_VALUE settings
        import re
        php_value_match = re.search(r'fastcgi_param PHP_VALUE "([^"]+)"', config_content)
        if php_value_match:
            php_value_str = php_value_match.group(1)
            for setting in php_value_str.split('\\n'):
                setting = setting.strip()
                if '=' in setting:
                    key, value = setting.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in php_settings:
                        php_settings[key] = value
    
    except Exception as e:
        flash(f'Warning: Could not read current PHP settings: {str(e)}', 'warning')
    
    return render_template('edit_php_ini.html', site=site, php_settings=php_settings)

@app.route('/sites/<int:site_id>/php-ini/save', methods=['POST'])
@login_required
def save_php_ini(site_id):
    """Save PHP settings for a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Get PHP settings from form
    php_settings = {
        'upload_max_filesize': request.form.get('upload_max_filesize', '100M'),
        'post_max_size': request.form.get('post_max_size', '100M'),
        'memory_limit': request.form.get('memory_limit', '256M'),
        'max_execution_time': request.form.get('max_execution_time', '60'),
        'max_input_time': request.form.get('max_input_time', '60'),
        'max_input_vars': request.form.get('max_input_vars', '1000')
    }
    
    try:
        # Recreate nginx config with new PHP settings
        site_manager.create_nginx_config(
            site['domain'], 
            site['php_version'], 
            ssl_enabled=site['ssl_enabled'],
            php_settings=php_settings
        )
        
        # Enable site
        site_manager.enable_site(site['domain'])
        
        flash('PHP settings updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating PHP settings: {str(e)}', 'error')
    
    return redirect(url_for('edit_php_ini', site_id=site_id))

@app.route('/databases')
@login_required
def databases():
    """Database management page"""
    init_components()
    all_databases = db.get_all_databases()
    sites = db.get_all_sites()
    return render_template('databases.html', databases=all_databases, sites=sites)

@app.route('/databases/create', methods=['POST'])
@login_required
def create_database():
    """Create a new database"""
    init_components()
    site_id = request.form.get('site_id')
    db_name = request.form.get('db_name')
    
    if not site_id or not db_name:
        flash('Site and database name are required', 'error')
        return redirect(url_for('databases'))
    
    site = db.get_site(int(site_id))
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('databases'))
    
    try:
        db_user = f"user_{db_name[:10]}"
        db_password = db_manager.generate_password()
        
        db_manager.create_database(db_name, db_user, db_password)
        db.create_database(int(site_id), db_name, db_user, db_password)
        
        flash(f'Database created: {db_name} (User: {db_user}, Password: {db_password})', 'success')
    except Exception as e:
        flash(f'Error creating database: {str(e)}', 'error')
    
    return redirect(url_for('databases'))

@app.route('/databases/<int:db_id>/delete', methods=['POST'])
@login_required
def delete_database(db_id):
    """Delete a database"""
    init_components()
    database = None
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM databases WHERE id = ?', (db_id,))
        database = cursor.fetchone()
    
    if not database:
        flash('Database not found', 'error')
        return redirect(url_for('databases'))
    
    try:
        db_manager.delete_database(database['db_name'], database['db_user'])
        db.delete_database(db_id)
        flash(f'Database {database["db_name"]} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting database: {str(e)}', 'error')
    
    return redirect(url_for('databases'))

@app.route('/users')
@login_required
def users():
    """SSH/FTP user management page"""
    init_components()
    all_users = db.get_all_ftp_users()
    sites = db.get_all_sites()
    return render_template('users.html', ftp_users=all_users, sites=sites)

@app.route('/users/create', methods=['POST'])
@login_required
def create_ftp_user():
    """Create a new SSH/FTP user"""
    init_components()
    site_id = request.form.get('site_id')
    username = request.form.get('username')
    password = request.form.get('password')
    access_type = request.form.get('access_type', 'ftp')
    
    if not site_id or not username or not password:
        flash('All fields are required', 'error')
        return redirect(url_for('users'))
    
    site = db.get_site(int(site_id))
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('users'))
    
    try:
        # Create system user
        user_manager.create_ftp_user(username, password, site['domain'], access_type)
        
        # Create database record
        db.create_ftp_user(int(site_id), username, access_type)
        
        flash(f'User {username} created successfully', 'success')
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'error')
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_ftp_user(user_id):
    """Delete a SSH/FTP user"""
    init_components()
    user = None
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ftp_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users'))
    
    try:
        # Delete system user
        user_manager.delete_ftp_user(user['username'])
        
        # Delete database record
        db.delete_ftp_user(user_id)
        
        flash(f'User {user["username"]} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('users'))

@app.route('/files')
@login_required
def file_manager():
    """File manager page"""
    init_components()
    sites = db.get_all_sites()
    return render_template('file_manager.html', sites=sites)

@app.route('/files/browse/<int:site_id>')
@login_required
def browse_files(site_id):
    """Browse files for a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get path from query parameter (relative to site htdocs)
    rel_path = request.args.get('path', '')
    
    # Security check: prevent directory traversal
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_path = os.path.join(base_path, rel_path) if rel_path else base_path
    
    # Ensure we're still within the site directory
    try:
        full_path = os.path.realpath(full_path)
        base_path = os.path.realpath(base_path)
        if not full_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Path not found'}), 404
    
    if not os.path.isdir(full_path):
        return jsonify({'error': 'Not a directory'}), 400
    
    # List directory contents
    items = []
    try:
        for item in sorted(os.listdir(full_path)):
            item_path = os.path.join(full_path, item)
            rel_item_path = os.path.join(rel_path, item) if rel_path else item
            
            stat_info = os.stat(item_path)
            items.append({
                'name': item,
                'path': rel_item_path,
                'is_dir': os.path.isdir(item_path),
                'size': stat_info.st_size if not os.path.isdir(item_path) else 0,
                'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_mtime))
            })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'path': rel_path,
        'items': items,
        'site': site['domain']
    })

@app.route('/files/download/<int:site_id>')
@login_required
def download_file(site_id):
    """Download a file from a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        flash('Site not found', 'error')
        return redirect(url_for('file_manager'))
    
    # Get path from query parameter
    rel_path = request.args.get('path', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/') or not rel_path:
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_path = os.path.join(base_path, rel_path)
    
    # Ensure we're still within the site directory
    try:
        full_path = os.path.realpath(full_path)
        base_path = os.path.realpath(base_path)
        if not full_path.startswith(base_path):
            flash('Access denied', 'error')
            return redirect(url_for('file_manager'))
    except:
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        flash('File not found', 'error')
        return redirect(url_for('file_manager'))
    
    from flask import send_file
    return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))

@app.route('/files/upload/<int:site_id>', methods=['POST'])
@login_required
def upload_file(site_id):
    """Upload a file to a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get path from form
    rel_path = request.form.get('path', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    # Get uploaded file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    upload_dir = os.path.join(base_path, rel_path) if rel_path else base_path
    
    # Ensure we're still within the site directory
    try:
        upload_dir = os.path.realpath(upload_dir)
        base_path = os.path.realpath(base_path)
        if not upload_dir.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(upload_dir) or not os.path.isdir(upload_dir):
        return jsonify({'error': 'Upload directory not found'}), 404
    
    # Save file
    try:
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        os.chmod(file_path, 0o644)
        return jsonify({'success': True, 'filename': file.filename})
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/files/delete/<int:site_id>', methods=['POST'])
@login_required
def delete_file(site_id):
    """Delete a file or directory from a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get path from form
    rel_path = request.form.get('path', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/') or not rel_path:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_path = os.path.join(base_path, rel_path)
    
    # Ensure we're still within the site directory
    try:
        full_path = os.path.realpath(full_path)
        base_path = os.path.realpath(base_path)
        if not full_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Delete file or directory
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

@app.route('/files/create-folder/<int:site_id>', methods=['POST'])
@login_required
def create_folder(site_id):
    """Create a new folder in a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get path and folder name from form
    rel_path = request.form.get('path', '')
    folder_name = request.form.get('folder_name', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not folder_name or '..' in folder_name or '/' in folder_name:
        return jsonify({'error': 'Invalid folder name'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    parent_dir = os.path.join(base_path, rel_path) if rel_path else base_path
    new_folder = os.path.join(parent_dir, folder_name)
    
    # Ensure we're still within the site directory
    try:
        new_folder = os.path.realpath(new_folder)
        base_path = os.path.realpath(base_path)
        if not new_folder.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if os.path.exists(new_folder):
        return jsonify({'error': 'Folder already exists'}), 400
    
    # Create folder
    try:
        os.makedirs(new_folder, mode=0o755)
        return jsonify({'success': True, 'folder_name': folder_name})
    except Exception as e:
        return jsonify({'error': f'Failed to create folder: {str(e)}'}), 500

@app.route('/files/create-file/<int:site_id>', methods=['POST'])
@login_required
def create_file(site_id):
    """Create a new file in a site"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get path and file name from form
    rel_path = request.form.get('path', '')
    file_name = request.form.get('file_name', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not file_name or '..' in file_name or '/' in file_name:
        return jsonify({'error': 'Invalid file name'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    parent_dir = os.path.join(base_path, rel_path) if rel_path else base_path
    new_file = os.path.join(parent_dir, file_name)
    
    # Ensure we're still within the site directory
    try:
        new_file = os.path.realpath(new_file)
        base_path = os.path.realpath(base_path)
        if not new_file.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except (OSError, ValueError) as e:
        return jsonify({'error': 'Invalid path'}), 400
    
    if os.path.exists(new_file):
        return jsonify({'error': 'File already exists'}), 400
    
    # Create file
    try:
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write('')  # Create empty file
        os.chmod(new_file, 0o644)
        return jsonify({'success': True, 'file_name': file_name})
    except Exception as e:
        return jsonify({'error': f'Failed to create file: {str(e)}'}), 500


@app.route('/files/rename/<int:site_id>', methods=['POST'])
@login_required
def rename_file(site_id):
    """Rename a file or folder"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    old_path = request.form.get('old_path', '')
    new_name = request.form.get('new_name', '')
    
    # Security checks
    if '..' in old_path or old_path.startswith('/') or not old_path:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not new_name or '..' in new_name or '/' in new_name:
        return jsonify({'error': 'Invalid new name'}), 400
    
    # Build paths
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    old_full_path = os.path.join(base_path, old_path)
    
    # Get parent directory and construct new path
    parent_dir = os.path.dirname(old_full_path)
    new_full_path = os.path.join(parent_dir, new_name)
    
    # Validate paths
    try:
        old_full_path = os.path.realpath(old_full_path)
        new_full_path = os.path.realpath(new_full_path)
        base_path = os.path.realpath(base_path)
        
        if not old_full_path.startswith(base_path) or not new_full_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(old_full_path):
        return jsonify({'error': 'File not found'}), 404
    
    if os.path.exists(new_full_path):
        return jsonify({'error': 'A file with that name already exists'}), 400
    
    # Rename
    try:
        os.rename(old_full_path, new_full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Rename failed: {str(e)}'}), 500

@app.route('/files/edit/<int:site_id>')
@login_required
def get_file_content(site_id):
    """Get file content for editing"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    rel_path = request.args.get('path', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/') or not rel_path:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_path = os.path.join(base_path, rel_path)
    
    # Validate path
    try:
        full_path = os.path.realpath(full_path)
        base_path = os.path.realpath(base_path)
        if not full_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Read file content
    try:
        # Check file size (limit to 5MB for editing)
        if os.path.getsize(full_path) > 5 * 1024 * 1024:
            return jsonify({'error': 'File too large to edit (max 5MB)'}), 400
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({'success': True, 'content': content, 'path': rel_path})
    except UnicodeDecodeError:
        return jsonify({'error': 'File is not a text file'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to read file: {str(e)}'}), 500

@app.route('/files/save/<int:site_id>', methods=['POST'])
@login_required
def save_file_content(site_id):
    """Save edited file content"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    rel_path = request.form.get('path', '')
    content = request.form.get('content', '')
    
    # Security check
    if '..' in rel_path or rel_path.startswith('/') or not rel_path:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Build full path
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_path = os.path.join(base_path, rel_path)
    
    # Validate path
    try:
        full_path = os.path.realpath(full_path)
        base_path = os.path.realpath(base_path)
        if not full_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Save file
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

@app.route('/files/compress/<int:site_id>', methods=['POST'])
@login_required
def compress_files(site_id):
    """Compress files/folders to a zip archive"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    import zipfile
    
    paths = request.form.getlist('paths[]')
    archive_name = request.form.get('archive_name', 'archive.zip')
    current_path = request.form.get('current_path', '')
    
    # Ensure archive name ends with .zip
    if not archive_name.endswith('.zip'):
        archive_name += '.zip'
    
    # Security checks
    for path in paths:
        if '..' in path or path.startswith('/'):
            return jsonify({'error': 'Invalid path'}), 400
    
    if '..' in current_path or current_path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    if '..' in archive_name or '/' in archive_name:
        return jsonify({'error': 'Invalid archive name'}), 400
    
    # Build paths
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    archive_path = os.path.join(base_path, current_path, archive_name) if current_path else os.path.join(base_path, archive_name)
    
    # Create zip file
    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for rel_path in paths:
                full_path = os.path.join(base_path, rel_path)
                
                # Validate path
                full_path = os.path.realpath(full_path)
                base_path_real = os.path.realpath(base_path)
                if not full_path.startswith(base_path_real):
                    return jsonify({'error': 'Access denied'}), 403
                
                if not os.path.exists(full_path):
                    continue
                
                # Add to zip
                if os.path.isfile(full_path):
                    zipf.write(full_path, os.path.basename(full_path))
                elif os.path.isdir(full_path):
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(full_path))
                            zipf.write(file_path, arcname)
        
        return jsonify({'success': True, 'archive_name': archive_name})
    except Exception as e:
        return jsonify({'error': f'Compression failed: {str(e)}'}), 500

@app.route('/files/extract/<int:site_id>', methods=['POST'])
@login_required
def extract_archive(site_id):
    """Extract a zip archive"""
    init_components()
    site = db.get_site(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    import zipfile
    
    archive_path = request.form.get('path', '')
    
    # Security check
    if '..' in archive_path or archive_path.startswith('/') or not archive_path:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Build paths
    base_path = os.path.join(app.config['SITES_DIR'], site['domain'], 'htdocs')
    full_archive_path = os.path.join(base_path, archive_path)
    
    # Validate path
    try:
        full_archive_path = os.path.realpath(full_archive_path)
        base_path = os.path.realpath(base_path)
        if not full_archive_path.startswith(base_path):
            return jsonify({'error': 'Access denied'}), 403
    except:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(full_archive_path) or not os.path.isfile(full_archive_path):
        return jsonify({'error': 'Archive not found'}), 404
    
    # Extract to same directory as archive
    extract_dir = os.path.dirname(full_archive_path)
    
    try:
        with zipfile.ZipFile(full_archive_path, 'r') as zipf:
            # Security check: validate all paths in archive
            for member in zipf.namelist():
                member_path = os.path.join(extract_dir, member)
                member_path = os.path.realpath(member_path)
                if not member_path.startswith(base_path):
                    return jsonify({'error': 'Archive contains invalid paths'}), 400
            
            # Extract
            zipf.extractall(extract_dir)
        
        return jsonify({'success': True})
    except zipfile.BadZipFile:
        return jsonify({'error': 'Invalid or corrupted zip file'}), 400
    except Exception as e:
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500

@app.route('/system/info')
@login_required
def system_info():
    """System information and statistics"""
    init_components()
    
    try:
        # Get system stats
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Load average
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        
        # Service status
        services = {
            'nginx': get_service_status('nginx'),
            'mariadb': get_service_status('mariadb'),
        }
        
        # Check PHP-FPM services
        php_services = {}
        for version in app.config['AVAILABLE_PHP_VERSIONS']:
            service_name = f'php{version}-fpm'
            php_services[version] = get_service_status(service_name)
        
        stats = {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'load_avg': load_avg
            },
            'memory': {
                'total': memory.total,
                'used': memory.used,
                'percent': memory.percent,
                'available': memory.available
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'percent': disk.percent,
                'free': disk.free
            },
            'services': services,
            'php_services': php_services
        }
        
        return render_template('system_info.html', stats=stats)
    except ImportError as e:
        flash('System monitoring module (psutil) is not installed. Please install it with: pip install psutil', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error loading system information: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/system/services')
@login_required
def service_manager():
    """Service management page"""
    init_components()
    return render_template('service_manager.html', 
                         php_versions=app.config['AVAILABLE_PHP_VERSIONS'])

@app.route('/system/services/restart', methods=['POST'])
@login_required
def restart_service():
    """Restart a service"""
    init_components()
    service_name = request.form.get('service')
    
    allowed_services = ['nginx', 'mariadb']
    for version in app.config['AVAILABLE_PHP_VERSIONS']:
        allowed_services.append(f'php{version}-fpm')
    
    if service_name not in allowed_services:
        flash('Invalid service name', 'error')
        return redirect(url_for('service_manager'))
    
    try:
        result = subprocess.run(
            ['/usr/bin/systemctl', 'restart', service_name],
            check=True,
            capture_output=True,
            text=True
        )
        flash(f'Service {service_name} restarted successfully', 'success')
    except subprocess.CalledProcessError as e:
        flash(f'Failed to restart {service_name}: {e.stderr}', 'error')
    except Exception as e:
        flash(f'Error restarting service: {str(e)}', 'error')
    
    return redirect(url_for('service_manager'))

def get_service_status(service_name):
    """Get the status of a systemd service"""
    try:
        result = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', service_name],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == 'active'
    except:
        return False

@app.route('/settings')
@login_required
def panel_settings():
    """Panel settings page"""
    init_components()
    settings = db.get_all_panel_settings()
    return render_template('panel_settings.html', settings=settings)

@app.route('/settings/save', methods=['POST'])
@login_required
def save_panel_settings():
    """Save panel settings"""
    init_components()
    
    panel_domain = request.form.get('panel_domain', '').strip()
    panel_port = request.form.get('panel_port', '8080')
    
    try:
        # Validate port
        port = int(panel_port)
        if port < 1 or port > 65535:
            flash('Invalid port number (must be between 1 and 65535)', 'error')
            return redirect(url_for('panel_settings'))
        
        # Save settings
        db.set_panel_setting('panel_domain', panel_domain)
        db.set_panel_setting('panel_port', str(port))
        
        # If a domain is set, create/update the nginx config for it
        if panel_domain:
            ssl_enabled = db.get_panel_setting('panel_ssl_enabled') == '1'
            site_manager.create_panel_nginx_config(panel_domain, ssl_enabled=ssl_enabled)
            flash('Panel settings saved and nginx configuration updated.', 'success')
        else:
            flash('Panel settings saved. Restart the panel service to apply changes.', 'success')
    except ValueError:
        flash('Invalid port number', 'error')
    except Exception as e:
        flash(f'Error saving settings: {str(e)}', 'error')
    
    return redirect(url_for('panel_settings'))

@app.route('/settings/ssl/request', methods=['POST'])
@login_required
def request_panel_ssl():
    """Request SSL certificate for panel domain"""
    init_components()
    
    panel_domain = db.get_panel_setting('panel_domain')
    if not panel_domain:
        flash('Panel domain not set', 'error')
        return redirect(url_for('panel_settings'))
    
    panel_webroot = None
    try:
        # First, update panel nginx config to serve ACME challenges
        panel_webroot = site_manager.create_panel_nginx_config(panel_domain, ssl_enabled=False)
        
        # Request SSL certificate using the panel webroot
        site_manager.request_ssl_certificate(panel_domain, include_www=False, webroot=panel_webroot)
        
        # Now update nginx config with SSL enabled
        site_manager.create_panel_nginx_config(panel_domain, ssl_enabled=True)
        
        # Mark SSL as enabled
        db.set_panel_setting('panel_ssl_enabled', '1')
        
        flash(f'SSL certificate obtained successfully for {panel_domain}', 'success')
    except Exception as e:
        # If SSL cert request failed, revert to non-SSL config
        if panel_webroot:
            try:
                site_manager.create_panel_nginx_config(panel_domain, ssl_enabled=False)
            except Exception as cleanup_error:
                # Log cleanup error but don't fail the overall operation
                app.logger.warning(f'Failed to revert nginx config during cleanup: {cleanup_error}')
        flash(f'Error requesting SSL certificate: {str(e)}', 'error')
    
    return redirect(url_for('panel_settings'))

@app.route('/settings/ssl/disable', methods=['POST'])
@login_required
def disable_panel_ssl():
    """Disable SSL for panel"""
    init_components()
    
    try:
        panel_domain = db.get_panel_setting('panel_domain')
        
        # Update nginx config to remove SSL
        site_manager.create_panel_nginx_config(panel_domain, ssl_enabled=False)
        
        # Mark SSL as disabled
        db.set_panel_setting('panel_ssl_enabled', '0')
        
        flash('SSL disabled for panel.', 'success')
    except Exception as e:
        flash(f'Error disabling SSL: {str(e)}', 'error')
    
    return redirect(url_for('panel_settings'))

@app.route('/settings/restart-panel', methods=['POST'])
@login_required
def restart_panel_service():
    """Restart the panel service"""
    init_components()
    
    try:
        # Restart lalapanel service
        subprocess.run(
            ['/usr/bin/systemctl', 'restart', 'lalapanel'],
            check=True,
            capture_output=True,
            text=True
        )
        flash('Panel service restarted successfully', 'success')
    except subprocess.CalledProcessError as e:
        flash(f'Failed to restart panel: {e.stderr}', 'error')
    except Exception as e:
        flash(f'Error restarting panel: {str(e)}', 'error')
    
    return redirect(url_for('panel_settings'))

if __name__ == '__main__':
    # Ensure directories exist
    try:
        os.makedirs(app.config['CONFIG_DIR'], exist_ok=True)
        os.makedirs(app.config['LOG_DIR'], exist_ok=True)
    except PermissionError:
        print("Warning: Cannot create system directories. Make sure you have proper permissions.")
    
    # Initialize components
    init_components()
    
    # Ensure default server config exists to reject unknown HTTPS domains
    try:
        default_config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], '000-default')
        if not os.path.exists(default_config_path):
            print("Creating default server configuration to reject unknown domains...")
            site_manager.create_default_server_config()
            # Reload nginx to apply changes
            subprocess.run(['/usr/bin/systemctl', 'reload', 'nginx'], check=False)
    except Exception as e:
        print(f"Warning: Could not create default server config: {e}")
    
    # Ensure panel nginx config exists to serve the panel on HTTP
    try:
        panel_config_path = os.path.join(app.config['NGINX_SITES_AVAILABLE'], 'lalapanel')
        if not os.path.exists(panel_config_path):
            print("Creating panel nginx configuration...")
            site_manager.create_panel_nginx_config()
            # Reload nginx to apply changes
            subprocess.run(['/usr/bin/systemctl', 'reload', 'nginx'], check=False)
    except Exception as e:
        print(f"Warning: Could not create panel nginx config: {e}")
    
    # Clean old login attempts on startup
    db.clear_old_login_attempts()
    
    # Get panel port from database settings if available, otherwise use config default
    panel_port = db.get_panel_port(app.config['PANEL_PORT'])
    
    print(f"Starting Lala Panel on {app.config['PANEL_HOST']}:{panel_port}")
    app.run(host=app.config['PANEL_HOST'], 
            port=panel_port, 
            debug=False)
