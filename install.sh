#!/bin/bash

###############################################################################
# Lala Panel Installation Script
# 
# This script installs Lala Panel on Ubuntu with:
# - Nginx
# - PHP-FPM (multiple versions)
# - MariaDB
# - Let's Encrypt (certbot)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/lalapanel"
CONFIG_DIR="/etc/lalapanel"
LOG_DIR="/var/log/lalapanel"
SITES_DIR="/var/www"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

check_ubuntu() {
    if [ ! -f /etc/os-release ]; then
        print_error "Cannot detect OS"
        exit 1
    fi
    
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        print_error "This script is designed for Ubuntu only"
        exit 1
    fi
    
    print_info "Detected Ubuntu $VERSION_ID"
}

install_system_packages() {
    print_info "Updating package lists..."
    apt-get update -qq
    
    print_info "Installing system packages..."
    apt-get install -y \
        nginx \
        mariadb-server \
        certbot \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        wget \
        unzip \
        git \
        software-properties-common
}

setup_mariadb() {
    print_info "Setting up MariaDB..."
    
    # Start MariaDB
    systemctl start mariadb
    systemctl enable mariadb
    
    # Secure installation (basic)
    mysql -e "DELETE FROM mysql.user WHERE User='';"
    mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
    mysql -e "DROP DATABASE IF EXISTS test;"
    mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
    mysql -e "FLUSH PRIVILEGES;"
    
    print_info "MariaDB setup complete"
}

install_php_fpm() {
    print_info "Installing PHP-FPM..."
    
    # Add ondrej/php PPA for multiple PHP versions
    add-apt-repository -y ppa:ondrej/php
    apt-get update -qq
    
    # Install PHP-FPM for different PHP versions
    for version in 8.3 8.2 8.1; do
        print_info "Installing PHP $version and PHP-FPM..."
        
        apt-get install -y \
            php${version}-fpm \
            php${version}-cli \
            php${version}-common \
            php${version}-mysql \
            php${version}-xml \
            php${version}-curl \
            php${version}-gd \
            php${version}-mbstring \
            php${version}-zip \
            php${version}-bcmath \
            php${version}-intl \
            php${version}-soap \
            php${version}-readline
        
        # Enable and start PHP-FPM service
        systemctl enable php${version}-fpm
        systemctl start php${version}-fpm
        
        print_info "PHP $version and PHP-FPM installed successfully"
    done
}

setup_nginx() {
    print_info "Configuring Nginx..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create Nginx configuration for the panel
    cat > /etc/nginx/sites-available/lalapanel << 'EOF'
server {
    listen 8080;
    server_name _;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    # Test nginx configuration
    nginx -t
    
    # Reload nginx
    systemctl reload nginx
    systemctl enable nginx
    
    print_info "Nginx configured"
}

install_lalapanel() {
    print_info "Installing Lala Panel..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$SITES_DIR"
    
    # Copy application files
    # Assuming we're running from the source directory
    cp -r . "$INSTALL_DIR/"
    
    # Create Python virtual environment
    cd "$INSTALL_DIR"
    python3 -m venv venv
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install --quiet -r requirements.txt
    deactivate
    
    # Set permissions
    chmod -R 755 "$INSTALL_DIR"
    chmod -R 755 "$CONFIG_DIR"
    chmod -R 755 "$LOG_DIR"
    
    print_info "Lala Panel installed"
}

create_admin_user() {
    print_info "Creating admin user..."
    
    # Prompt for admin credentials
    read -p "Enter admin username [admin]: " ADMIN_USER
    ADMIN_USER=${ADMIN_USER:-admin}
    
    read -s -p "Enter admin password: " ADMIN_PASS
    echo
    
    if [ -z "$ADMIN_PASS" ]; then
        print_error "Password cannot be empty"
        exit 1
    fi
    
    # Create admin user using Python with environment variable
    cd "$INSTALL_DIR"
    source venv/bin/activate
    export ADMIN_USERNAME="$ADMIN_USER"
    export ADMIN_PASSWORD="$ADMIN_PASS"
    python3 << 'EOF'
from database import Database
from werkzeug.security import generate_password_hash
import os

db_path = os.path.join(os.environ.get('CONFIG_DIR', '/etc/lalapanel'), 'lalapanel.db')
db = Database(db_path)

try:
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD')
    password_hash = generate_password_hash(password)
    db.create_user(username, password_hash)
    print("Admin user created successfully")
except Exception as e:
    print(f"Error creating admin user: {e}")
EOF
    unset ADMIN_PASSWORD
    deactivate
}

create_systemd_service() {
    print_info "Creating systemd service..."
    
    cat > /etc/systemd/system/lalapanel.service << EOF
[Unit]
Description=Lala Panel Hosting Control Panel
After=network.target mariadb.service nginx.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    systemctl enable lalapanel
    
    print_info "Systemd service created"
}

show_completion_message() {
    print_info "Installation complete!"
    echo
    echo "================================================================"
    echo "  Lala Panel has been installed successfully!"
    echo "================================================================"
    echo
    echo "To start Lala Panel:"
    echo "  sudo systemctl start lalapanel"
    echo
    echo "To check status:"
    echo "  sudo systemctl status lalapanel"
    echo
    echo "Access the panel at:"
    echo "  http://YOUR_SERVER_IP:8080"
    echo
    echo "Admin credentials:"
    echo "  Username: $ADMIN_USER"
    echo "  Password: [your password]"
    echo
    echo "Important notes:"
    echo "  - Configure firewall to allow port 8080"
    echo "  - PHP-FPM is installed and running for PHP 8.1, 8.2, and 8.3"
    echo "  - Set MARIADB_ROOT_PASSWORD environment variable"
    echo "  - Set LETSENCRYPT_EMAIL environment variable"
    echo
    echo "================================================================"
}

# Main installation
main() {
    print_info "Starting Lala Panel installation..."
    echo
    
    check_root
    check_ubuntu
    
    install_system_packages
    setup_mariadb
    install_php_fpm
    setup_nginx
    install_lalapanel
    create_admin_user
    create_systemd_service
    
    show_completion_message
}

main
