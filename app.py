"""
Main Flask application for Lala Panel
"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

from config import Config
from database import Database
from site_manager import SiteManager, DatabaseManager

app = Flask(__name__)
app.config.from_object(Config)

# Initialize components lazily to allow testing
db = None
site_manager = None
db_manager = None

def init_components():
    """Initialize application components"""
    global db, site_manager, db_manager
    if db is None:
        db = Database(app.config['DATABASE_PATH'])
        site_manager = SiteManager(app.config)
        db_manager = DatabaseManager(app.config)
    return db, site_manager, db_manager

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
                import hashlib
                import time
                
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

if __name__ == '__main__':
    # Ensure directories exist
    try:
        os.makedirs(app.config['CONFIG_DIR'], exist_ok=True)
        os.makedirs(app.config['LOG_DIR'], exist_ok=True)
    except PermissionError:
        print("Warning: Cannot create system directories. Make sure you have proper permissions.")
    
    # Initialize components
    init_components()
    
    # Clean old login attempts on startup
    db.clear_old_login_attempts()
    
    app.run(host=app.config['PANEL_HOST'], 
            port=app.config['PANEL_PORT'], 
            debug=False)
