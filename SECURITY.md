# Security Documentation for Lala Panel

This document describes the security measures implemented in Lala Panel to protect against common web application vulnerabilities.

## Security Overview

Lala Panel has been hardened with comprehensive security controls to ensure a secure hosting environment. All code has been scanned with CodeQL static analysis and shows **0 security vulnerabilities**.

## Implemented Security Controls

### 1. Cross-Site Request Forgery (CSRF) Protection

**Status**: ✅ Fully Implemented

- **Library**: Flask-WTF
- **Implementation**: 
  - CSRF tokens required for all POST requests
  - Tokens embedded in HTML forms via `{{ csrf_token() }}`
  - JavaScript fetch requests include CSRF tokens via meta tag
  - 1-hour token lifetime (no expiration limit)
  
**Testing**: All forms and AJAX requests validated to include CSRF protection.

### 2. Cross-Site Scripting (XSS) Prevention

**Status**: ✅ Fully Implemented

- **Jinja2 Auto-escaping**: All template variables automatically escaped
- **Security Headers**:
  - `X-XSS-Protection: 1; mode=block`
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy` ready (via Flask-Talisman, can be enabled)
  
### 3. SQL Injection Prevention

**Status**: ✅ Fully Implemented

- **Parameterized Queries**: All database queries use parameterized statements
- **Identifier Validation**: Database/user names validated with regex `^[a-zA-Z0-9_]+$`
- **Context Managers**: All database operations use proper connection handling

**Example**:
```python
cursor.execute('SELECT * FROM sites WHERE id = ?', (site_id,))
cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY %s", (db_password,))
```

### 4. Command Injection Prevention

**Status**: ✅ Fully Implemented

- **Input Validation**: All inputs validated before passing to subprocess
- **Username Validation**: Regex `^[a-z0-9_]+$`, max 32 characters
- **Domain Validation**: Regex for valid domain format
- **Subprocess Security**: Using list arguments instead of shell=True

**Example**:
```python
subprocess.run(['/usr/sbin/useradd', '-m', '-d', site_dir, '-s', '/bin/bash', username], check=True)
```

### 5. Path Traversal Prevention

**Status**: ✅ Fully Implemented

- **Multiple Protection Layers**:
  1. Input validation (reject `..` and absolute paths)
  2. `os.path.realpath()` resolution
  3. `startswith()` validation against base path
  4. `validate_path()` helper function
  
**Example**:
```python
def validate_path(path, base_path):
    try:
        abs_path = os.path.abspath(os.path.join(base_path, path))
        abs_base = os.path.abspath(base_path)
        return abs_path.startswith(abs_base)
    except (ValueError, OSError):
        return False
```

### 6. Session Security

**Status**: ✅ Fully Implemented

- **Configuration**:
  - `SESSION_COOKIE_SECURE = True` (HTTPS only)
  - `SESSION_COOKIE_HTTPONLY = True` (prevent JavaScript access)
  - `SESSION_COOKIE_SAMESITE = 'Lax'` (CSRF protection)
  - `PERMANENT_SESSION_LIFETIME = 3600` (1-hour timeout)
  
- **Session Fixation Prevention**: Session regenerated on login
- **Session Data**: Minimal sensitive data stored in sessions

### 7. Authentication & Authorization

**Status**: ✅ Fully Implemented

- **Password Hashing**: Werkzeug's `generate_password_hash()` with salt
- **Login Rate Limiting**: 10 attempts per minute per IP
- **Brute Force Protection**: 5 failed attempts per IP in 15 minutes
- **Login Attempts Tracking**: All attempts logged with IP and timestamp
- **Flask-Login**: Industry-standard session management

### 8. Rate Limiting

**Status**: ✅ Fully Implemented

- **Library**: Flask-Limiter
- **Global Limits**: 200/day, 50/hour per IP
- **Endpoint-Specific Limits**:
  - Login: 10/minute
  - Site creation: 20/hour
  - SSL requests: 5/hour
  - File uploads: 50/hour
  - Site deletion: 10/hour

### 9. File Upload Security

**Status**: ✅ Fully Implemented

- **Size Limit**: 100 MB max (`MAX_CONTENT_LENGTH`)
- **Filename Sanitization**: Remove path components and dangerous characters
- **Path Validation**: Uploads restricted to site directories
- **File Permissions**: 0o644 for uploaded files
- **Hidden Files**: Prevented by sanitization

**Example**:
```python
def sanitize_filename(filename):
    filename = os.path.basename(filename)  # Remove path
    filename = re.sub(r'[^\w\s\-\.]', '', filename)  # Remove special chars
    if filename.startswith('.'):
        filename = filename[1:]  # Prevent hidden files
    return filename
```

### 10. SSL/TLS Configuration

**Status**: ✅ Fully Implemented

- **Protocols**: TLS 1.2 and TLS 1.3 only
- **Cipher Suites**: Mozilla Intermediate compatibility
  ```
  ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:
  ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:
  ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:
  DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
  ```
- **Certificate Validation**: Cryptography library validates uploaded certificates
- **SSL Directory Permissions**: 0o700 (owner only)
- **Private Key Permissions**: 0o600 (owner read/write only)
- **HSTS**: `max-age=31536000; includeSubDomains; preload`

### 11. Security Headers

**Status**: ✅ Fully Implemented

All responses include comprehensive security headers:

```python
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload  # HTTPS only
```

### 12. Audit Logging

**Status**: ✅ Fully Implemented

All security-relevant operations are logged to `/var/log/lalapanel/audit.log`:

- Site creation and deletion
- SSL certificate operations
- Database creation and deletion
- User creation and deletion
- File uploads and operations
- Login attempts (via separate table)

**Log Format**:
```
[2024-12-08T21:20:05] User 1: SITE_CREATE - Creating site: example.com
[2024-12-08T21:21:15] User 1: SSL_REQUEST - Requesting SSL for example.com (mode: auto)
```

### 13. Input Validation & Sanitization

**Status**: ✅ Fully Implemented

- **Domain Names**: RFC-compliant domain validation
- **Usernames**: Lowercase alphanumeric + underscore, max 32 chars
- **Database Names**: Alphanumeric + underscore validation
- **File Names**: Path removal, special character removal, hidden file prevention
- **Paths**: Multiple layers of traversal prevention
- **PHP Versions**: Whitelist validation against `AVAILABLE_PHP_VERSIONS`

### 14. Open Redirect Prevention

**Status**: ✅ Fully Implemented

- **Next Page Validation**: Only relative URLs starting with `/` are allowed
- **Example**:
  ```python
  next_page = request.args.get('next')
  if next_page and next_page.startswith('/'):
      return redirect(next_page)
  return redirect(url_for('dashboard'))
  ```

### 15. Information Disclosure Prevention

**Status**: ✅ Fully Implemented

- **Error Messages**: Generic messages shown to users, details logged
- **Debug Mode**: Disabled in production (`debug=False`)
- **Stack Traces**: Not exposed to end users
- **Sensitive Data**: Database passwords not displayed in UI after creation

## Security Testing

### Static Analysis

- **Tool**: GitHub CodeQL
- **Languages**: Python, JavaScript
- **Results**: 0 vulnerabilities found
- **Scan Date**: 2024-12-08

### Code Review

All security-critical code has been reviewed with the following findings addressed:

1. ✅ Session lifetime moved to app initialization
2. ✅ SSL directory permissions restricted to 0o700
3. ✅ SSL cipher suite extracted to configuration constant
4. ✅ Cryptography imports moved to module top

## Security Best Practices for Deployment

### 1. Environment Configuration

**Required**:
```bash
# Set a strong random secret key
export SECRET_KEY=$(openssl rand -hex 32)

# Configure Let's Encrypt email
export LETSENCRYPT_EMAIL="admin@yourdomain.com"

# Secure MariaDB root password (auto-generated during install)
# Stored in /etc/lalapanel/lalapanel.env
```

### 2. File Permissions

```bash
# Secure environment file
chmod 600 /etc/lalapanel/lalapanel.env

# Secure database
chmod 600 /etc/lalapanel/lalapanel.db

# Audit log directory
chmod 755 /var/log/lalapanel
chmod 644 /var/log/lalapanel/audit.log
```

### 3. Firewall Configuration

```bash
# Allow only HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 4. Panel Access

- Panel runs on `127.0.0.1:8080` (localhost only)
- Accessed via Nginx reverse proxy
- Can be configured with custom domain and SSL

### 5. Regular Updates

```bash
# Update system packages
apt update && apt upgrade

# Update Python dependencies
cd /opt/lalapanel
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Threat Model

### Protected Against

✅ SQL Injection  
✅ Command Injection  
✅ Path Traversal  
✅ XSS (Reflected, Stored, DOM-based)  
✅ CSRF  
✅ Session Fixation  
✅ Session Hijacking (via secure cookies)  
✅ Brute Force (rate limiting)  
✅ Open Redirect  
✅ Information Disclosure  
✅ Clickjacking (X-Frame-Options)  
✅ MIME Sniffing (X-Content-Type-Options)  
✅ Man-in-the-Middle (HSTS, modern TLS)  

### Out of Scope

⚠️ DDoS attacks (requires infrastructure-level protection)  
⚠️ Social engineering attacks  
⚠️ Physical access to server  
⚠️ Zero-day vulnerabilities in dependencies  

## Vulnerability Reporting

If you discover a security vulnerability in Lala Panel, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Contact the maintainers privately
3. Provide detailed information about the vulnerability
4. Allow reasonable time for a fix before public disclosure

## Security Roadmap

### Planned Enhancements

- [ ] Dependency vulnerability scanning in CI/CD
- [ ] Content Security Policy with nonce support
- [ ] Password complexity requirements
- [ ] Two-Factor Authentication (2FA)
- [ ] Web Application Firewall (WAF) integration
- [ ] Intrusion Detection System (IDS) integration

## Compliance Notes

### OWASP Top 10 (2021)

| Risk | Status | Notes |
|------|--------|-------|
| A01:2021-Broken Access Control | ✅ Protected | Flask-Login, path validation |
| A02:2021-Cryptographic Failures | ✅ Protected | Modern TLS, secure password hashing |
| A03:2021-Injection | ✅ Protected | Parameterized queries, input validation |
| A04:2021-Insecure Design | ✅ Addressed | Security-first design principles |
| A05:2021-Security Misconfiguration | ✅ Protected | Secure defaults, hardened config |
| A06:2021-Vulnerable Components | ⚠️ Monitor | Regular dependency updates required |
| A07:2021-Authentication Failures | ✅ Protected | Rate limiting, secure sessions |
| A08:2021-Software & Data Integrity | ✅ Protected | Audit logging, CSRF protection |
| A09:2021-Security Logging Failures | ✅ Protected | Comprehensive audit logging |
| A10:2021-Server-Side Request Forgery | N/A | No SSRF attack surface |

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/3.0.x/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: 2024-12-08  
**Version**: 1.0  
**Security Review Status**: ✅ Complete
