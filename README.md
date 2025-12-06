# 🚀 Lala Panel

A minimal, lightweight hosting control panel designed specifically for PHP-based websites.

## Features

- **Simple Site Management**: Create and delete websites with ease
- **FrankenPHP Support**: Multiple PHP version support with hot-switching capability
- **SSL Automation**: Automatic Let's Encrypt certificate generation and renewal
- **MariaDB Integration**: Built-in database management
- **Clean UI**: Minimalist, fast web interface
- **Security-First**: HTTPS enforcement, rate-limited login, isolated site configurations

## Tech Stack

- **OS**: Ubuntu (Latest LTS)
- **Web Server**: Nginx
- **PHP Runtime**: FrankenPHP (with version switching)
- **Database**: MariaDB
- **SSL**: Let's Encrypt (certbot)
- **Backend**: Python 3 + Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (no CDN dependencies)

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

/opt/frankenphp/           # FrankenPHP installations
  ├── php8.3/
  ├── php8.2/
  └── php8.1/

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
2. Set up FrankenPHP directory structure
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
sudo mkdir -p /opt/lalapanel /etc/lalapanel /var/log/lalapanel /var/www /opt/frankenphp

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

### FrankenPHP Setup

FrankenPHP binaries need to be installed manually for each PHP version:

```bash
# Example for PHP 8.3
mkdir -p /opt/frankenphp/php8.3
cd /opt/frankenphp/php8.3

# Download FrankenPHP (adjust URL for your architecture)
wget https://github.com/dunglas/frankenphp/releases/download/v1.0.0/frankenphp-linux-x86_64.tar.gz
tar -xzf frankenphp-linux-x86_64.tar.gz

# Create systemd service for FrankenPHP
# (Service file configuration depends on FrankenPHP version)
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
4. Select PHP version
5. Enable SSL (optional, but recommended)
6. Create database (optional)
7. Click "Create Site"

The panel will:
- Create site directory structure
- Generate Nginx configuration
- Request SSL certificate (if enabled)
- Create database and user (if requested)
- Reload Nginx

### Managing Sites

- **View Sites**: Dashboard shows all sites with status
- **Update PHP Version**: Change PHP version from site detail page
- **Delete Site**: Removes all site files, configs, and databases

### Database Management

- Create databases for specific sites
- View all databases with credentials
- Delete databases when no longer needed

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
- Uses FrankenPHP for PHP runtime
- SSL by Let's Encrypt
- Nginx for web serving
- MariaDB for database management

---

**Note**: This is a minimal control panel. For production use, ensure proper security hardening, backups, and monitoring are in place.
