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
    
    # FrankenPHP
    FRANKENPHP_DIR = '/opt/frankenphp'
    AVAILABLE_PHP_VERSIONS = ['8.3', '8.2', '8.1']
    
    # Database
    DATABASE_PATH = os.path.join(CONFIG_DIR, 'lalapanel.db')
    MARIADB_HOST = 'localhost'
    MARIADB_PORT = 3306
    MARIADB_ROOT_PASSWORD = os.environ.get('MARIADB_ROOT_PASSWORD', '')
    
    # Security
    MAX_LOGIN_ATTEMPTS = 5
    RATE_LIMIT_STORAGE_URL = 'memory://'
    
    # SSL
    LETSENCRYPT_EMAIL = os.environ.get('LETSENCRYPT_EMAIL', 'admin@localhost')
    CERTBOT_PATH = '/usr/bin/certbot'
    
    # Panel settings
    PANEL_PORT = 8080
    PANEL_HOST = '0.0.0.0'
