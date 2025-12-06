# Configuration Guide

## Environment Variables

Lala Panel can be configured using environment variables. Create a `.env` file in `/opt/lalapanel/`:

```bash
# Flask Settings
SECRET_KEY=your_random_secret_key_here
FLASK_ENV=production

# Database Settings
MARIADB_ROOT_PASSWORD=your_mariadb_root_password
MARIADB_HOST=localhost
MARIADB_PORT=3306

# SSL Settings
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Panel Settings
PANEL_PORT=8080
PANEL_HOST=0.0.0.0
```

## FrankenPHP Configuration

### Installing FrankenPHP

For each PHP version, download and install FrankenPHP:

```bash
# Create directory for PHP 8.3
mkdir -p /opt/frankenphp/php8.3
cd /opt/frankenphp/php8.3

# Download FrankenPHP
wget https://github.com/dunglas/frankenphp/releases/latest/download/frankenphp-linux-x86_64
chmod +x frankenphp-linux-x86_64
mv frankenphp-linux-x86_64 frankenphp

# Create systemd service
cat > /etc/systemd/system/frankenphp-8.3.service << 'EOF'
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
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable frankenphp-8.3
systemctl start frankenphp-8.3
```

Repeat for PHP 8.2 and 8.1.

## Nginx Configuration

### Main Nginx Configuration

Edit `/etc/nginx/nginx.conf`:

```nginx
user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 2048;
    multi_accept on;
}

http {
    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    # Logging Settings
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    
    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;
    
    # Virtual Host Configs
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

## MariaDB Configuration

### Initial Setup

```bash
# Secure MariaDB installation
mysql_secure_installation

# Set root password
mysql -u root
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;
EXIT;
```

### Optimize MariaDB

Edit `/etc/mysql/mariadb.conf.d/50-server.cnf`:

```ini
[mysqld]
# Connection settings
max_connections = 200
connect_timeout = 10

# Buffer settings
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M

# Query cache
query_cache_type = 1
query_cache_size = 64M

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

Restart MariaDB:
```bash
systemctl restart mariadb
```

## SSL/TLS Configuration

### Automatic Certificate Renewal

Certbot automatically creates a renewal timer. Verify it's active:

```bash
systemctl status certbot.timer
```

### Manual Certificate Renewal

```bash
# Renew all certificates
certbot renew

# Renew specific certificate
certbot renew --cert-name yourdomain.com
```

### SSL Best Practices

1. Use strong ciphers
2. Enable HSTS
3. Redirect HTTP to HTTPS
4. Keep certificates up to date

## Security Hardening

### Firewall Configuration

```bash
# Install UFW
apt-get install ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (be careful!)
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow panel (consider restricting by IP)
ufw allow 8080/tcp

# Enable firewall
ufw enable
```

### Fail2ban Configuration

```bash
# Install fail2ban
apt-get install fail2ban

# Create jail for Lala Panel
cat > /etc/fail2ban/jail.d/lalapanel.conf << 'EOF'
[lalapanel]
enabled = true
port = 8080
filter = lalapanel
logpath = /var/log/lalapanel/access.log
maxretry = 5
bantime = 3600
EOF

# Create filter
cat > /etc/fail2ban/filter.d/lalapanel.conf << 'EOF'
[Definition]
failregex = ^<HOST> .* "POST /login HTTP.*" 401
ignoreregex =
EOF

# Restart fail2ban
systemctl restart fail2ban
```

### File Permissions

```bash
# Set proper ownership
chown -R www-data:www-data /var/www
chown -R root:root /etc/lalapanel
chown -R root:root /opt/lalapanel

# Set proper permissions
chmod -R 755 /var/www
chmod 700 /etc/lalapanel
chmod 755 /opt/lalapanel
```

## Monitoring

### System Monitoring

```bash
# Monitor system resources
htop

# Monitor disk usage
df -h

# Monitor network
iftop
```

### Log Monitoring

```bash
# Panel logs
journalctl -u lalapanel -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# Nginx error logs
tail -f /var/log/nginx/error.log

# Site-specific logs
tail -f /var/log/lalapanel/yourdomain.com/error.log
```

## Backup Strategy

While Lala Panel doesn't include built-in backup features, here's a recommended strategy:

### Manual Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup sites
tar -czf "$BACKUP_DIR/sites.tar.gz" /var/www

# Backup databases
mysqldump --all-databases > "$BACKUP_DIR/databases.sql"

# Backup configs
tar -czf "$BACKUP_DIR/configs.tar.gz" /etc/lalapanel /etc/nginx/sites-available

# Backup panel database
cp /etc/lalapanel/lalapanel.db "$BACKUP_DIR/"
```

### Automated Backup with Cron

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /root/backup.sh
```

## Performance Tuning

### Nginx Optimization

```nginx
# Worker processes
worker_processes auto;

# Worker connections
events {
    worker_connections 4096;
}

# Enable caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=cache:10m max_size=1g;
```

### PHP/FrankenPHP Optimization

Configure FrankenPHP with appropriate memory limits and workers based on your server resources.

### MariaDB Optimization

```sql
-- Check slow queries
SELECT * FROM mysql.slow_log;

-- Optimize tables
OPTIMIZE TABLE database_name.table_name;

-- Check index usage
SHOW INDEX FROM database_name.table_name;
```

## Troubleshooting Common Issues

### Issue: Panel won't start

**Solution:**
```bash
# Check Python dependencies
source /opt/lalapanel/venv/bin/activate
pip list

# Check for port conflicts
netstat -tulpn | grep 8080

# Check logs
journalctl -u lalapanel -n 100 --no-pager
```

### Issue: Site shows 502 Bad Gateway

**Solution:**
```bash
# Check FrankenPHP is running
systemctl status frankenphp-8.3

# Check socket exists
ls -la /opt/frankenphp/php8.3/frankenphp.sock

# Restart FrankenPHP
systemctl restart frankenphp-8.3
```

### Issue: SSL certificate failed

**Solution:**
```bash
# Check domain DNS
dig yourdomain.com +short

# Check port 80 is accessible
curl -I http://yourdomain.com

# Try manual certificate request
certbot certonly --nginx -d yourdomain.com
```

## Upgrading Lala Panel

```bash
# Stop the service
systemctl stop lalapanel

# Backup current installation
cp -r /opt/lalapanel /opt/lalapanel.backup

# Pull latest changes
cd /opt/lalapanel
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
systemctl start lalapanel
```
