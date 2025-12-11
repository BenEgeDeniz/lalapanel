# 🚀 Lala Panel - Fully Vibecoded!

### This project was generated entirely by automated Copilot agents. No manual review, verification, or quality assurance has been performed. The code may contain errors, omissions, security vulnerabilities, or incorrect behavior. It should not be relied upon for any production use, safety-critical tasks, or decision-making. Use this project strictly for testing and experimentation purposes and at your own risk.

A minimal, lightweight hosting control panel designed specifically for PHP-based websites with modern Bootstrap UI.

## Features

- **Site Management**: Create, manage, and delete websites with ease
- **PHP-FPM Support**: Multiple PHP version support (8.5, 8.4, 8.3, 8.2, 8.1) with hot-switching capability
- **Passkey Authentication**: Modern passwordless login using WebAuthn
  - Support for all authenticator types (platform, cross-platform, security keys)
  - Biometric authentication (Face ID, Touch ID, Windows Hello)
  - USB security key support (YubiKey, etc.)
  - Full credential management (register, rename, delete)
- **Flexible SSL Options**: 
  - Automatic Let's Encrypt certificate generation for sites and panel
  - Manual SSL certificate upload
  - Domain-only SSL (skip www subdomain)
- **File Manager**: Full-featured web-based file manager with:
  - Browse, upload, download, delete files and folders
  - Create, rename, edit files directly in browser
  - Compress/extract archives (zip, tar, tar.gz, tar.bz2)
  - Syntax highlighting for code files
- **Configuration Editors**: 
  - Direct Nginx vhost editing with syntax validation
  - PHP.ini customization per site
- **Database Management**: Complete MariaDB database operations
- **SSH/FTP User Management**: Create secure SFTP/SSH users with site-specific access
- **System Information**: Real-time monitoring of system resources, services, and processes
- **Service Manager**: Start, stop, restart system services (Nginx, PHP-FPM, MariaDB, etc.)
- **Panel Settings**: Configure panel port, enable SSL for the panel itself
- **Modern UI**: Professional Bootstrap 5 interface with responsive design
- **Security-First**: HTTPS enforcement, rate-limited login, isolated site configurations, path traversal protection

## Tech Stack

- **OS**: Ubuntu (Latest LTS)
- **Web Server**: Nginx
- **PHP Runtime**: PHP-FPM (with version switching)
- **Database**: MariaDB
- **SSL**: Let's Encrypt (certbot) + Manual certificates
- **Backend**: Python 3 + Flask
- **Frontend**: Bootstrap 5 + Bootstrap Icons

## Directory Structure

```
/var/www/<site>/           # Site files
  ├── htdocs/              # Web root
  └── tmp/                 # Temporary files

/var/log/lalapanel/<site>/ # Site logs
  ├── access.log
  └── error.log

/etc/lalapanel/            # Panel configuration
  └── lalapanel.db         # SQLite database

/etc/nginx/sites-available/ # Nginx configs
/etc/nginx/sites-enabled/   # Enabled sites

/run/php/                  # PHP-FPM sockets
  ├── php8.5-fpm.sock
  ├── php8.4-fpm.sock
  ├── php8.3-fpm.sock
  ├── php8.2-fpm.sock
  └── php8.1-fpm.sock

/opt/lalapanel/            # Panel application
```

## Installation

### Prerequisites

- Fresh Ubuntu 20.04 LTS or 22.04 LTS installation
- Root access
- Domain name (optional, for SSL)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/BenEgeDeniz/lalapanel.git
cd lalapanel

# Run the installation script
sudo bash install.sh
```

The installation script will:
1. Install Nginx, MariaDB, certbot, and system dependencies
2. Install PHP-FPM for PHP 8.5, 8.4, 8.3, 8.2, and 8.1
3. Install Lala Panel application
4. Create systemd service
5. Prompt for admin credentials

### Manual Installation

If you prefer manual installation:

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y nginx mariadb-server certbot python3 python3-pip python3-venv

# Create directories
sudo mkdir -p /opt/lalapanel /etc/lalapanel /var/log/lalapanel /var/www

# Copy application files
sudo cp -r . /opt/lalapanel/

# Create Python virtual environment
cd /opt/lalapanel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create admin user
python3 -c "
from database import Database
from werkzeug.security import generate_password_hash
db = Database('/etc/lalapanel/lalapanel.db')
db.create_user('admin', generate_password_hash('your_password_here'))
"

# Create systemd service
sudo cp lalapanel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lalapanel
sudo systemctl start lalapanel
```

## Configuration

### Environment Variables

Create `/opt/lalapanel/.env` file:

```bash
SECRET_KEY=your_secret_key_here
MARIADB_ROOT_PASSWORD=your_mariadb_root_password
LETSENCRYPT_EMAIL=your_email@example.com
```

### PHP-FPM Setup

PHP-FPM is automatically installed by the install.sh script. For manual setup:

```bash
# Add ondrej/php PPA for multiple PHP versions
sudo add-apt-repository -y ppa:ondrej/php
sudo apt-get update

# Install PHP-FPM for each version
for version in 8.5 8.4 8.3 8.2 8.1; do
    sudo apt-get install -y \
        php${version}-fpm \
        php${version}-cli \
        php${version}-common \
        php${version}-mysql \
        php${version}-xml \
        php${version}-curl \
        php${version}-gd \
        php${version}-mbstring \
        php${version}-zip
    
    sudo systemctl enable php${version}-fpm
    sudo systemctl start php${version}-fpm
done
```

## Usage

### Starting the Panel

```bash
# Start the service
sudo systemctl start lalapanel

# Check status
sudo systemctl status lalapanel

# View logs
sudo journalctl -u lalapanel -f
```

### Accessing the Panel

Open your browser and navigate to:
```
http://YOUR_SERVER_IP
```

The panel runs on `localhost:8080` and is served through an Nginx reverse proxy on port 80. This ensures secure access and prevents direct connections to the Flask application.

Login with the admin credentials you created during installation.

### Passkey Authentication

Lala Panel supports modern passwordless authentication using passkeys (WebAuthn):

**What are Passkeys?**
- Passwordless login using biometrics (Face ID, Touch ID, Windows Hello)
- USB security keys (YubiKey, Titan Key, etc.)
- More secure than passwords - resistant to phishing and credential theft
- Works across devices and platforms

**Setting Up Passkeys:**

1. Log in to the panel with your username and password
2. Navigate to "Passkeys" in the menu
3. Click "Register New Passkey"
4. Follow the prompts on your device to create the passkey
5. Give your passkey a memorable name (e.g., "My iPhone", "YubiKey")

**Logging In with Passkeys:**

1. On the login page, click the "Passkey" tab
2. Enter your username
3. Click "Login with Passkey"
4. Use your authenticator (biometric, PIN, or security key)
5. You'll be logged in instantly!

**Managing Passkeys:**

From the Passkeys page, you can:
- View all your registered passkeys
- Rename passkeys for easier identification
- Delete passkeys you no longer use
- See when each passkey was last used

**Supported Authenticators:**
- **Platform authenticators**: Built-in biometrics on your device
  - Apple: Face ID, Touch ID (iPhone, iPad, Mac)
  - Windows: Windows Hello (fingerprint, face recognition)
  - Android: Fingerprint, face unlock
- **Cross-platform authenticators**: USB security keys
  - YubiKey 5 Series
  - Google Titan Security Key
  - Any FIDO2-compliant security key
- **Browser support**: Chrome 108+, Safari 16+, Firefox 119+, Edge 108+

**Security Notes:**
- Passkeys use public-key cryptography - your biometric data never leaves your device
- Each passkey is unique and bound to your domain
- Passkeys cannot be stolen or phished like passwords
- You can use both passkeys and passwords - they work together

### Creating a Site

1. Log in to the panel
2. Click "Create New Site"
3. Enter domain name (e.g., example.com)
4. Select PHP version (8.5, 8.4, 8.3, 8.2, or 8.1)
5. Choose SSL configuration:
   - **Automatic SSL**: Request Let's Encrypt certificate for domain and www subdomain
   - **Domain Only SSL**: Skip www subdomain (useful when DNS is not configured for www)
   - **Manual SSL**: Upload your own SSL certificates later
   - **No SSL**: HTTP only (not recommended)
6. Configure PHP settings (upload limits, memory, execution time)
7. Create database (optional)
8. Click "Create Site"

The panel will:
- Create site directory structure
- Generate Nginx configuration with custom PHP settings
- Request SSL certificate (if auto mode selected)
- Create database and user (if requested)
- Reload Nginx

### Managing Sites

- **View Sites**: Dashboard shows all sites with SSL status and PHP version
- **Update PHP Version**: Change PHP version from site detail page
- **Edit Configuration**: 
  - Edit Nginx vhost configuration directly with syntax testing
  - Customize PHP.ini settings per site
- **File Management**: Web-based file manager with full CRUD operations
- **SSL Management**: 
  - Request Let's Encrypt SSL for existing sites
  - Upload manual SSL certificates
  - View certificate information
- **Delete Site**: Removes all site files, configs, and databases

### SSL Configuration

#### Automatic SSL (Let's Encrypt)
- Automatically requests and configures SSL certificates
- Supports both domain and www subdomain
- Option to skip www subdomain if DNS is not configured
- Free certificates valid for 90 days (auto-renewal recommended via cron)

#### Manual SSL Upload
1. Navigate to site details
2. Click "Upload SSL Certificates"
3. Upload your certificate (fullchain.pem) and private key (privkey.pem)
4. Nginx configuration will be automatically updated

### Database Management

- Create databases for specific sites
- View all databases with credentials in secure modals
- Delete databases when no longer needed
- Automatic database name generation to avoid conflicts

### SSH/FTP User Management

Create secure users for file access:

1. Navigate to "SSH/FTP Users" from the menu
2. Click "Create SSH/FTP User"
3. Select a site
4. Enter username (lowercase, numbers, underscores only)
5. Enter strong password (min 8 characters)
6. Choose access type:
   - **FTP Only**: SFTP access with restricted shell
   - **SSH + FTP**: Full SSH terminal access plus SFTP

Users are automatically restricted to their site directory for security.

**Connecting via SFTP:**
```bash
sftp username@your-server-ip
# Or use GUI clients like FileZilla, WinSCP, Cyberduck
```

### File Manager

The built-in file manager provides comprehensive file operations:

1. Navigate to "File Manager" from the menu
2. Select a site to manage its files
3. Available operations:
   - **Browse**: Navigate through directories
   - **Upload**: Upload multiple files via drag-and-drop or file selector
   - **Download**: Download individual files
   - **Create**: Create new files and folders
   - **Edit**: Edit text files with syntax highlighting
   - **Rename**: Rename files and folders
   - **Delete**: Delete files and folders
   - **Compress**: Create zip/tar archives from files/folders
   - **Extract**: Extract zip/tar/tar.gz/tar.bz2 archives

All file operations include security checks to prevent directory traversal attacks.

### System Information

Monitor your server health and resources:

1. Navigate to "System Info" from the menu
2. View real-time information:
   - System uptime and load average
   - CPU usage and details
   - Memory usage (RAM and swap)
   - Disk usage for all mounted filesystems
   - Network interface statistics
   - Running processes

### Service Manager

Manage system services from the web interface:

1. Navigate to "Service Manager" from the menu
2. View status of critical services:
   - Nginx web server
   - PHP-FPM versions (8.5, 8.4, 8.3, 8.2, 8.1)
   - MariaDB database
   - Lala Panel itself
3. Restart services as needed with one click

### Panel Settings

Configure the panel itself:

1. Navigate to "Settings" from the menu
2. Configure panel options:
   - **Panel Port**: Change the port the panel runs on (default: 8080)
   - **Panel SSL**: Enable HTTPS for the panel interface
   - Request Let's Encrypt certificate for panel domain
   - Disable SSL if needed

### Configuration Editing

Advanced users can directly edit configurations:

**Nginx Vhost Editing:**
1. Go to site details
2. Click "Edit Vhost"
3. Modify Nginx configuration directly
4. Test configuration before applying
5. Changes reload Nginx automatically

**PHP.ini Customization:**
1. Go to site details
2. Click "Edit PHP.ini"
3. Customize PHP settings per site:
   - memory_limit
   - upload_max_filesize
   - post_max_size
   - max_execution_time
   - And more...
4. Changes reload PHP-FPM automatically

## Security

### Built-in Security Features

- **HTTPS Enforcement**: All sites redirect to HTTPS when SSL is enabled
- **Rate Limiting**: Login attempts are limited to prevent brute force
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.
- **Isolated Configs**: Each site has its own Nginx configuration

### Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

**Note**: Port 8080 should NOT be exposed to the internet. The panel runs on `localhost:8080` and is accessed through Nginx reverse proxy on port 80/443.

### Securing the Panel

The panel is automatically secured with the following measures:
1. Flask app runs only on `localhost:8080` by default (not accessible from external IPs)
2. Nginx reverse proxy handles all external access on ports 80/443
3. You can further secure by:
   - Enabling SSL for the panel via Settings page
   - Changing the panel port via Settings page
   - Restricting access by IP in the Nginx configuration
   - Using strong passwords
   - Keeping the system updated

## File Permissions

Default permissions:
- Site directories: `755`
- Site files: `644`
- Nginx configs: `644`
- Log files: `644`

## Troubleshooting

### Panel won't start

```bash
# Check logs
sudo journalctl -u lalapanel -n 50

# Check if port 8080 is already in use on localhost
sudo netstat -tulpn | grep 127.0.0.1:8080
```

### Site not accessible

```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx configuration
sudo nginx -t

# Check site logs
sudo tail -f /var/log/lalapanel/yourdomain.com/error.log
```

### SSL certificate failed

```bash
# Ensure domain points to your server
dig yourdomain.com

# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Test manually
sudo certbot certonly --webroot -w /var/www/yourdomain.com/htdocs -d yourdomain.com
```

### Database connection failed

```bash
# Check MariaDB status
sudo systemctl status mariadb

# Test connection
mysql -u root -p
```

## Development

### Requirements

- Python 3.8+
- Node.js (for future enhancements)

### Running in Development Mode

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key

# Run the application
python app.py
```

### Project Structure

```
lalapanel/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── database.py         # Database models and operations
├── site_manager.py     # Site, database, and user management
├── requirements.txt    # Python dependencies
├── install.sh          # Installation script
├── templates/          # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── create_site.html
│   ├── site_detail.html
│   ├── databases.html
│   ├── users.html
│   ├── file_manager.html
│   ├── edit_vhost.html
│   ├── edit_php_ini.html
│   ├── system_info.html
│   ├── service_manager.html
│   └── panel_settings.html
└── static/             # Static assets
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Current Limitations

**Lala Panel does NOT include:**
- Automated backup features (you should implement your own backup strategy)
- Email services (MTA/mail server management)
- DNS management (use your DNS provider's interface)
- Multi-server support (single server only)

**Note**: Many features have been added since the initial release. The panel now includes a comprehensive file manager, configuration editors, system monitoring, and service management.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

## Acknowledgments

- Built with Flask
- Uses PHP-FPM for PHP runtime
- SSL by Let's Encrypt
- Nginx for web serving
- MariaDB for database management

---

**Note**: This is a minimal control panel. For production use, ensure proper security hardening, backups, and monitoring are in place.
