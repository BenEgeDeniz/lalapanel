# 🚀 Lala Panel

A minimal, lightweight hosting control panel designed specifically for PHP-based websites with modern Bootstrap UI.

## Features

- **Simple Site Management**: Create and delete websites with ease
- **PHP-FPM Support**: Multiple PHP version support with hot-switching capability
- **Flexible SSL Options**: 
  - Automatic Let's Encrypt certificate generation
  - Manual SSL certificate upload
  - Domain-only SSL (skip www subdomain)
- **PHP Settings**: Configurable upload limits, memory limits, and execution time
- **MariaDB Integration**: Built-in database management
- **SSH/FTP User Management**: Create secure SFTP/SSH users for site file access
- **Modern UI**: Professional Bootstrap 5 interface with responsive design
- **Security-First**: HTTPS enforcement, rate-limited login, isolated site configurations

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
2. Install PHP-FPM for PHP 8.1, 8.2, and 8.3
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
for version in 8.3 8.2 8.1; do
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
http://YOUR_SERVER_IP:8080
```

Login with the admin credentials you created during installation.

### Creating a Site

1. Log in to the panel
2. Click "Create New Site"
3. Enter domain name (e.g., example.com)
4. Select PHP version (8.1, 8.2, or 8.3)
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

1. Navigate to "SSH/FTP" from the menu
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

# Allow panel (be careful with this!)
sudo ufw allow 8080/tcp

# Enable firewall
sudo ufw enable
```

### Securing the Panel

It's recommended to:
1. Use a reverse proxy with SSL for the panel itself
2. Restrict panel access by IP
3. Use strong passwords
4. Keep the system updated

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

# Check if port is already in use
sudo netstat -tulpn | grep 8080
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
├── site_manager.py     # Site and database management
├── requirements.txt    # Python dependencies
├── install.sh          # Installation script
├── templates/          # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── create_site.html
│   ├── site_detail.html
│   └── databases.html
└── static/             # Static assets
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Limitations

By design, Lala Panel does **NOT** include:
- Backup features
- Email services
- DNS management
- Multi-server support
- File manager
- Cron management

These features may be added in future versions.

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
