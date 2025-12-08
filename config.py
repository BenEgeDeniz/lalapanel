"""
Configuration settings for Lala Panel
"""
import os
import secrets

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.environ.get('CONFIG_DIR', '/etc/lalapanel')
SITES_DIR = os.environ.get('SITES_DIR', '/var/www')
LOG_DIR = os.environ.get('LOG_DIR', '/var/log/lalapanel')

class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Paths
    BASE_DIR = BASE_DIR
    CONFIG_DIR = CONFIG_DIR
    SITES_DIR = SITES_DIR
    LOG_DIR = LOG_DIR
    NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
    NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled'
    
    # PHP-FPM
    PHP_FPM_SOCKET_DIR = '/run/php'
    AVAILABLE_PHP_VERSIONS = ['8.5', '8.4', '8.3', '8.2', '8.1']
    
    # Database
    DATABASE_PATH = os.path.join(CONFIG_DIR, 'lalapanel.db')
    MARIADB_HOST = 'localhost'
    MARIADB_PORT = 3306
    MARIADB_ROOT_PASSWORD = os.environ.get('MARIADB_ROOT_PASSWORD', '')
    
    # Security
    MAX_LOGIN_ATTEMPTS = 5
    RATE_LIMIT_STORAGE_URL = 'memory://'
    
    # Session Security
    SESSION_COOKIE_SECURE = False  # Set dynamically based on request scheme (HTTP/HTTPS)
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour session timeout
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max file upload
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'tar', 'gz', 
                         'php', 'html', 'css', 'js', 'json', 'xml', 'svg', 'md', 'sql'}
    
    # SSL
    LETSENCRYPT_EMAIL = os.environ.get('LETSENCRYPT_EMAIL', 'admin@localhost')
    CERTBOT_PATH = '/usr/bin/certbot'
    
    # Modern SSL/TLS cipher suite (Mozilla Intermediate compatibility)
    # https://ssl-config.mozilla.org/
    SSL_CIPHERS = 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
    
    # Panel settings
    PANEL_PORT = 8080
    PANEL_HOST = '127.0.0.1'  # Listen only on localhost for security
