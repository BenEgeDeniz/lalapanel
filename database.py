"""
Database models for Lala Panel
"""
import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """Database handler for Lala Panel"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Sites table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE NOT NULL,
                    php_version TEXT NOT NULL,
                    ssl_enabled INTEGER DEFAULT 0,
                    ssl_expires TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Databases table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS databases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER,
                    db_name TEXT UNIQUE NOT NULL,
                    db_user TEXT NOT NULL,
                    db_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE
                )
            ''')
            
            # FTP/SSH users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ftp_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER,
                    username TEXT UNIQUE NOT NULL,
                    access_type TEXT DEFAULT 'ftp',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE
                )
            ''')
            
            # Login attempts table for rate limiting
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Panel settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS panel_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Initialize default settings if not exists
            cursor.execute('SELECT COUNT(*) FROM panel_settings WHERE setting_key = ?', ('panel_domain',))
            if cursor.fetchone()[0] == 0:
                cursor.execute('INSERT INTO panel_settings (setting_key, setting_value) VALUES (?, ?)', 
                              ('panel_domain', ''))
                cursor.execute('INSERT INTO panel_settings (setting_key, setting_value) VALUES (?, ?)', 
                              ('panel_port', '8080'))
                cursor.execute('INSERT INTO panel_settings (setting_key, setting_value) VALUES (?, ?)', 
                              ('panel_ssl_enabled', '0'))
    
    def create_user(self, username, password_hash):
        """Create a new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            return cursor.lastrowid
    
    def get_user(self, username):
        """Get user by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            return cursor.fetchone()
    
    def create_site(self, domain, php_version, ssl_enabled=False):
        """Create a new site"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sites (domain, php_version, ssl_enabled) VALUES (?, ?, ?)',
                (domain, php_version, ssl_enabled)
            )
            return cursor.lastrowid
    
    def get_site(self, site_id):
        """Get site by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sites WHERE id = ?', (site_id,))
            return cursor.fetchone()
    
    def get_site_by_domain(self, domain):
        """Get site by domain"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sites WHERE domain = ?', (domain,))
            return cursor.fetchone()
    
    def get_all_sites(self):
        """Get all sites"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sites ORDER BY created_at DESC')
            return cursor.fetchall()
    
    def update_site(self, site_id, **kwargs):
        """Update site attributes"""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(site_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE sites SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                values
            )
    
    def delete_site(self, site_id):
        """Delete a site"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sites WHERE id = ?', (site_id,))
    
    def create_database(self, site_id, db_name, db_user, db_password):
        """Create a database record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO databases (site_id, db_name, db_user, db_password) VALUES (?, ?, ?, ?)',
                (site_id, db_name, db_user, db_password)
            )
            return cursor.lastrowid
    
    def get_databases_for_site(self, site_id):
        """Get all databases for a site"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM databases WHERE site_id = ?', (site_id,))
            return cursor.fetchall()
    
    def get_all_databases(self):
        """Get all databases"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.*, s.domain 
                FROM databases d
                LEFT JOIN sites s ON d.site_id = s.id
                ORDER BY d.created_at DESC
            ''')
            return cursor.fetchall()
    
    def delete_database(self, db_id):
        """Delete a database record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM databases WHERE id = ?', (db_id,))
    
    def record_login_attempt(self, ip_address):
        """Record a login attempt"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO login_attempts (ip_address) VALUES (?)',
                (ip_address,)
            )
    
    def get_recent_login_attempts(self, ip_address, minutes=15):
        """Get recent login attempts for an IP"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM login_attempts 
                WHERE ip_address = ? 
                AND attempted_at > datetime('now', '-' || ? || ' minutes')
            ''', (ip_address, minutes))
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def clear_old_login_attempts(self, hours=24):
        """Clear old login attempts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM login_attempts 
                WHERE attempted_at < datetime('now', '-' || ? || ' hours')
            ''', (hours,))
    
    def create_ftp_user(self, site_id, username, access_type='ftp'):
        """Create a FTP/SSH user record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO ftp_users (site_id, username, access_type) VALUES (?, ?, ?)',
                (site_id, username, access_type)
            )
            return cursor.lastrowid
    
    def get_all_ftp_users(self):
        """Get all FTP/SSH users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.*, s.domain 
                FROM ftp_users f
                LEFT JOIN sites s ON f.site_id = s.id
                ORDER BY f.created_at DESC
            ''')
            return cursor.fetchall()
    
    def get_ftp_users_for_site(self, site_id):
        """Get all FTP/SSH users for a site"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ftp_users WHERE site_id = ?', (site_id,))
            return cursor.fetchall()
    
    def delete_ftp_user(self, user_id):
        """Delete a FTP/SSH user record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ftp_users WHERE id = ?', (user_id,))
    
    def get_panel_setting(self, key):
        """Get a panel setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT setting_value FROM panel_settings WHERE setting_key = ?', (key,))
            result = cursor.fetchone()
            return result['setting_value'] if result else None
    
    def set_panel_setting(self, key, value):
        """Set a panel setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO panel_settings (setting_key, setting_value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) 
                DO UPDATE SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
            ''', (key, value, value))
    
    def get_all_panel_settings(self):
        """Get all panel settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT setting_key, setting_value FROM panel_settings')
            rows = cursor.fetchall()
            return {row['setting_key']: row['setting_value'] for row in rows}
    
    def get_panel_port(self, default_port=8080):
        """Get panel port from settings with fallback to default
        
        Args:
            default_port (int): Default port to use if no setting exists or conversion fails
            
        Returns:
            int: The panel port from settings or the default
        """
        db_port = self.get_panel_setting('panel_port')
        if db_port:
            try:
                return int(db_port)
            except (ValueError, TypeError):
                # If conversion fails, log a warning and use the default
                logger.warning(f"Invalid panel port value in database: '{db_port}'. Using default port {default_port}")
        return default_port

