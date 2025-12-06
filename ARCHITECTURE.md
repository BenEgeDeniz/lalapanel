# Lala Panel Architecture

## System Overview

Lala Panel is a lightweight hosting control panel built with simplicity and efficiency in mind. It follows a modular architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│              (HTML/CSS/JS - No CDN)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               Flask Application                          │
│           (Python Web Framework)                         │
├─────────────────────────────────────────────────────────┤
│  • Routes & Controllers                                  │
│  • Authentication & Session Management                   │
│  • Request Validation                                    │
│  • Rate Limiting                                         │
└────────────────────┬────────────────────────────────────┘
                     │
           ┌─────────┴──────────┐
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│  Site Manager    │  │ Database Manager │
├──────────────────┤  ├──────────────────┤
│ • Create sites   │  │ • Create DB      │
│ • Delete sites   │  │ • Delete DB      │
│ • Nginx config   │  │ • User mgmt      │
│ • SSL setup      │  │ • Credentials    │
│ • PHP switching  │  └──────────────────┘
└──────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                  Database Layer                          │
│                 (SQLite + MariaDB)                       │
├─────────────────────────────────────────────────────────┤
│  SQLite:                      MariaDB:                   │
│  • Panel data                 • Site databases           │
│  • Users                      • User data                │
│  • Sites metadata             • Application data         │
│  • Login attempts                                        │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│              System Components                           │
├─────────────────────────────────────────────────────────┤
│  Nginx:           PHP-FPM:          Let's Encrypt:      │
│  • Web server     • PHP runtime      • SSL certs         │
│  • Reverse proxy  • Multi-version    • Auto-renewal      │
│  • SSL handling   • FastCGI          • Domain validation │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Flask Application (`app.py`)

The main application entry point.

**Responsibilities:**
- Route handling
- User authentication
- Session management
- Request/response processing
- Template rendering

**Key Features:**
- Flask-Login for authentication
- Rate limiting on login
- Flash messages for user feedback
- RESTful route design

### 2. Database Layer (`database.py`)

Manages all database operations using SQLite.

**Tables:**
- `users`: Admin users
- `sites`: Hosted websites
- `databases`: MariaDB databases
- `login_attempts`: Rate limiting data

**Features:**
- Context manager for safe connections
- Transaction management
- Row factory for dict-like results
- Automatic schema initialization

### 3. Site Manager (`site_manager.py`)

Handles all site-related operations.

**Key Functions:**

- **create_site_directories()**: Creates file structure
- **create_nginx_config()**: Generates Nginx vhost
- **enable_site()**: Activates site in Nginx
- **disable_site()**: Deactivates site
- **request_ssl_certificate()**: Gets Let's Encrypt cert
- **update_php_version()**: Switches PHP version
- **delete_site_files()**: Removes all site files

### 4. Database Manager (`site_manager.py`)

Manages MariaDB databases for sites.

**Key Functions:**

- **create_database()**: Creates DB and user
- **delete_database()**: Removes DB and user
- **generate_password()**: Creates secure passwords

### 5. Configuration (`config.py`)

Centralized configuration management.

**Configurable Items:**
- Directory paths
- Database settings
- PHP versions
- Security settings
- SSL email

### 6. Templates

Clean, responsive HTML templates.

**Pages:**
- `login.html`: Authentication
- `dashboard.html`: Sites overview
- `create_site.html`: New site form
- `site_detail.html`: Site management
- `databases.html`: DB management

### 7. Static Assets

Self-hosted, no CDN dependencies.

- `style.css`: All styling
- `main.js`: Client-side interactions

## Data Flow

### Creating a Site

```
User Request
    │
    ▼
Flask Route (/sites/create)
    │
    ├─ Validate input
    ├─ Check if site exists
    │
    ▼
Site Manager
    │
    ├─ Create directories
    ├─ Generate Nginx config
    ├─ Enable site
    ├─ Request SSL (optional)
    │
    ▼
Database
    │
    ├─ Store site metadata
    ├─ Store database info (optional)
    │
    ▼
Database Manager (if DB requested)
    │
    ├─ Create MariaDB database
    ├─ Create DB user
    ├─ Grant privileges
    │
    ▼
System
    │
    ├─ Reload Nginx
    └─ Return success
```

### PHP Version Switching

```
User Request
    │
    ▼
Flask Route (/sites/<id>/update-php)
    │
    ▼
Site Manager
    │
    ├─ Get current site config
    ├─ Regenerate Nginx config with new PHP socket
    ├─ Reload Nginx
    │
    ▼
Database
    │
    ├─ Update site metadata
    └─ Return success
```

## File System Structure

```
/var/www/
├── example.com/
│   ├── htdocs/              # Web root
│   │   └── index.php        # Default file
│   └── tmp/                 # Temporary files

/var/log/lalapanel/
├── example.com/
│   ├── access.log
│   └── error.log

/etc/lalapanel/
└── lalapanel.db             # SQLite database

/etc/nginx/
├── sites-available/
│   └── example.com          # Nginx config
└── sites-enabled/
    └── example.com -> ../sites-available/example.com

/run/php/
├── php8.3-fpm.sock          # PHP 8.3 socket
├── php8.2-fpm.sock          # PHP 8.2 socket
└── php8.1-fpm.sock          # PHP 8.1 socket

/opt/lalapanel/
├── app.py                   # Main application
├── config.py
├── database.py
├── site_manager.py
├── requirements.txt
├── templates/
├── static/
└── venv/                    # Python virtual env
```

## Security Architecture

### Authentication Flow

```
Login Request
    │
    ├─ Check rate limit (IP-based)
    │   └─ Reject if exceeded
    │
    ├─ Validate credentials
    │   └─ Hash comparison
    │
    ├─ Create session
    │   └─ Secure cookie
    │
    └─ Redirect to dashboard
```

### Security Measures

1. **Password Security**
   - Werkzeug password hashing
   - Secure random generation
   - No plaintext storage

2. **Rate Limiting**
   - IP-based tracking
   - Configurable threshold
   - Time-based reset

3. **Session Security**
   - Secure cookies
   - Secret key encryption
   - Login required decorators

4. **HTTPS Enforcement**
   - Nginx redirects
   - HSTS headers
   - Let's Encrypt automation

5. **Input Validation**
   - Form validation
   - SQL injection prevention
   - XSS protection headers

6. **File Permissions**
   - Restricted directory access
   - Proper ownership
   - Secure defaults

## Nginx Configuration Strategy

### HTTP → HTTPS Redirect

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # PHP via PHP-FPM
    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        include fastcgi_params;
    }
}
```

## PHP-FPM Integration

### Multi-Version Support

Each PHP version runs as a separate PHP-FPM service:

```
PHP-FPM 8.3 → Socket: /run/php/php8.3-fpm.sock
PHP-FPM 8.2 → Socket: /run/php/php8.2-fpm.sock
PHP-FPM 8.1 → Socket: /run/php/php8.1-fpm.sock
```

### Version Switching

Site's Nginx config points to specific socket:

```nginx
fastcgi_pass unix:/run/php/php8.3-fpm.sock;
```

Switching versions = Update config + Reload Nginx

## Scalability Considerations

### Current Limits

- Single server
- SQLite for panel data
- Local file storage

### Future Enhancements

Possible (but not in scope):
- Multi-server support
- Distributed database
- Object storage
- Load balancing
- Caching layer
- CDN integration

## Error Handling

### Application Level

```python
try:
    # Operation
except SpecificException as e:
    flash('User-friendly message', 'error')
    log_error(e)
    return error_response()
```

### System Level

- Nginx error pages
- PHP error logging
- System journaling
- Database rollback

## Monitoring Points

1. **Application**
   - Login attempts
   - Site creation/deletion
   - Database operations

2. **System**
   - Nginx status
   - PHP-FPM processes
   - Disk usage
   - Memory usage

3. **Sites**
   - Access logs
   - Error logs
   - SSL expiry
   - Uptime

## Deployment

### Systemd Service

```ini
[Unit]
Description=Lala Panel
After=network.target mariadb.service nginx.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/lalapanel
ExecStart=/opt/lalapanel/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Startup Sequence

1. System boot
2. Network ready
3. MariaDB starts
4. Nginx starts
5. PHP-FPM services start
6. Lala Panel starts
7. Ready for requests

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | Python 3 + Flask | Web framework |
| Database (Panel) | SQLite | Metadata storage |
| Database (Sites) | MariaDB | Site databases |
| Web Server | Nginx | HTTP/HTTPS serving |
| PHP Runtime | PHP-FPM | PHP execution |
| SSL | Let's Encrypt | Certificate management |
| Auth | Flask-Login | User sessions |
| Frontend | HTML5/CSS3/JS | User interface |

## Design Principles

1. **Simplicity**: Minimal features, maximum utility
2. **Security**: Security-first approach
3. **Performance**: Lightweight and fast
4. **Modularity**: Clean separation of concerns
5. **Maintainability**: Clear code structure
6. **No External Dependencies**: Self-hosted assets
7. **Standards Compliance**: Follow best practices
