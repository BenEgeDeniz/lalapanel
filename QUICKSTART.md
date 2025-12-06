# Quick Start Guide

This guide will help you get Lala Panel up and running quickly.

## Prerequisites

- Ubuntu 20.04 LTS or 22.04 LTS
- Root or sudo access
- At least 1GB RAM
- 10GB free disk space

## Installation

### 1. Download Lala Panel

```bash
git clone https://github.com/BenEgeDeniz/lalapanel.git
cd lalapanel
```

### 2. Run Installation Script

```bash
sudo bash install.sh
```

The installer will:
- Install system dependencies (Nginx, MariaDB, Python, etc.)
- Set up directory structure
- Create Python virtual environment
- Configure systemd service
- Prompt for admin credentials

### 3. Configure Environment

Edit `/opt/lalapanel/.env`:

```bash
sudo nano /opt/lalapanel/.env
```

Set these variables:
```bash
MARIADB_ROOT_PASSWORD=your_secure_mariadb_password
LETSENCRYPT_EMAIL=your_email@example.com
```

### 4. Install FrankenPHP

FrankenPHP must be installed manually for each PHP version:

```bash
# Create directory for PHP 8.3
sudo mkdir -p /opt/frankenphp/php8.3
cd /opt/frankenphp/php8.3

# Download FrankenPHP (adjust URL for your system)
sudo wget https://github.com/dunglas/frankenphp/releases/latest/download/frankenphp-linux-x86_64
sudo chmod +x frankenphp-linux-x86_64
sudo mv frankenphp-linux-x86_64 frankenphp
```

Create systemd service for FrankenPHP:

```bash
sudo nano /etc/systemd/system/frankenphp-8.3.service
```

Add:
```ini
[Unit]
Description=FrankenPHP PHP 8.3
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/frankenphp/php8.3
ExecStart=/opt/frankenphp/php8.3/frankenphp php-server --listen unix:/opt/frankenphp/php8.3/frankenphp.sock
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable frankenphp-8.3
sudo systemctl start frankenphp-8.3
```

Repeat for PHP 8.2 and 8.1 if needed.

### 5. Start Lala Panel

```bash
sudo systemctl start lalapanel
sudo systemctl status lalapanel
```

### 6. Configure Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
```

### 7. Access the Panel

Open your browser and navigate to:
```
http://YOUR_SERVER_IP:8080
```

Login with the credentials you created during installation.

## Creating Your First Site

1. Click "Create New Site"
2. Enter domain name (e.g., `example.com`)
3. Select PHP version (8.3, 8.2, or 8.1)
4. Check "Enable SSL" for Let's Encrypt certificate
5. Check "Create MariaDB Database" if you need one
6. Click "Create Site"

**Important**: Before requesting SSL, ensure:
- Your domain points to your server's IP
- Ports 80 and 443 are accessible
- No other service is using port 80

## Uploading Files

After creating a site, upload your files to:
```
/var/www/example.com/htdocs/
```

Example:
```bash
# Upload via SCP
scp -r /local/website/* user@server:/var/www/example.com/htdocs/

# Or using SFTP client like FileZilla
# Connect to your server and navigate to /var/www/example.com/htdocs/
```

## Common Commands

### Check Panel Status
```bash
sudo systemctl status lalapanel
```

### View Panel Logs
```bash
sudo journalctl -u lalapanel -f
```

### Restart Panel
```bash
sudo systemctl restart lalapanel
```

### Check Site Nginx Config
```bash
sudo cat /etc/nginx/sites-available/example.com
sudo nginx -t  # Test configuration
```

### View Site Logs
```bash
sudo tail -f /var/log/lalapanel/example.com/access.log
sudo tail -f /var/log/lalapanel/example.com/error.log
```

### Manually Renew SSL
```bash
sudo certbot renew
```

## Troubleshooting

### Panel Won't Start
```bash
# Check logs
sudo journalctl -u lalapanel -n 50

# Check port 8080
sudo netstat -tulpn | grep 8080

# Ensure directories exist
ls -la /etc/lalapanel
ls -la /var/log/lalapanel
```

### Site Shows 502 Error
```bash
# Check FrankenPHP is running
sudo systemctl status frankenphp-8.3

# Check socket exists
ls -la /opt/frankenphp/php8.3/frankenphp.sock

# Restart FrankenPHP
sudo systemctl restart frankenphp-8.3
```

### SSL Certificate Failed
```bash
# Verify domain points to server
dig example.com +short

# Check port 80 is accessible
curl -I http://example.com

# Try manual certificate request
sudo certbot certonly --webroot -w /var/www/example.com/htdocs -d example.com
```

## Next Steps

- Read the full [README.md](README.md) for detailed information
- Check [CONFIGURATION.md](CONFIGURATION.md) for advanced configuration
- Set up regular backups (see README.md)
- Configure monitoring
- Harden security settings

## Getting Help

If you encounter issues:
1. Check the logs: `sudo journalctl -u lalapanel -f`
2. Review the documentation
3. Open an issue on GitHub

## Security Reminders

- Change default admin password
- Set strong MariaDB root password
- Configure firewall properly
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Regularly backup your sites and databases
- Use SSL for the panel itself (reverse proxy)
- Restrict panel access by IP if possible
