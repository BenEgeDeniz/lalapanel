# Contributing to Lala Panel

Thank you for your interest in contributing to Lala Panel! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a positive community

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Use the latest version of Lala Panel
3. Verify it's actually a bug and not a configuration issue

When creating a bug report, include:
- Lala Panel version
- Ubuntu version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs
- Screenshots if applicable

### Suggesting Features

Feature requests are welcome! Please:
1. Check if the feature has already been requested
2. Clearly describe the feature and its use case
3. Explain why it would be useful to users
4. Remember: Lala Panel is intentionally minimal

**Out of Scope Features:**
- Backups (by design)
- Email services
- DNS management
- Multi-server support
- File manager
- Cron management

These may be reconsidered in future versions.

### Pull Requests

1. **Fork the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/lalapanel.git
   cd lalapanel
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

3. **Make Your Changes**
   - Follow the coding standards
   - Write clear commit messages
   - Test your changes thoroughly

4. **Test Locally**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run tests (if available)
   python -m pytest
   ```

5. **Submit Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Ensure all checks pass

## Development Setup

### Prerequisites

- Python 3.8+
- Git
- Ubuntu 20.04+ (for full testing)

### Local Development

```bash
# Clone repository
git clone https://github.com/BenEgeDeniz/lalapanel.git
cd lalapanel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables for testing
export CONFIG_DIR=/tmp/lalapanel-test
export SITES_DIR=/tmp/lalapanel-sites
export LOG_DIR=/tmp/lalapanel-logs

# Run the application
python app.py
```

### Testing

Currently, Lala Panel doesn't have a comprehensive test suite. Contributions to add tests are very welcome!

Testing checklist:
- [ ] Application starts without errors
- [ ] Login works
- [ ] Site creation works (with mock services)
- [ ] Site deletion works
- [ ] PHP version switching updates config
- [ ] Database creation works (with MariaDB)
- [ ] SSL certificate logic is correct

## Coding Standards

### Python Code Style

Follow PEP 8 guidelines:

```python
# Good
def create_site(domain, php_version):
    """Create a new site with specified PHP version."""
    site_path = os.path.join(SITES_DIR, domain)
    return site_path

# Bad
def createSite(d,p):
    sp=os.path.join(SITES_DIR,d)
    return sp
```

### Code Organization

- Keep functions focused and single-purpose
- Use descriptive variable names
- Add docstrings to functions and classes
- Comment complex logic
- Avoid deep nesting

### File Structure

```python
# 1. Module docstring
"""
Module description
"""

# 2. Imports (standard library, third-party, local)
import os
import sys

from flask import Flask

from config import Config

# 3. Constants
DEFAULT_PORT = 8080

# 4. Classes
class SiteManager:
    pass

# 5. Functions
def helper_function():
    pass

# 6. Main execution
if __name__ == '__main__':
    main()
```

### HTML/CSS/JavaScript

- Use semantic HTML5
- Mobile-first responsive design
- No external CDN dependencies
- Vanilla JavaScript (no frameworks)
- Progressive enhancement

### Git Commit Messages

```
# Good
Add SSL certificate renewal automation

- Implement certbot renewal checker
- Add systemd timer for auto-renewal
- Update documentation

# Bad
fixed stuff
update files
changes
```

Format:
```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance tasks

## Project Structure

Understanding the codebase:

```
lalapanel/
├── app.py              # Main Flask application
├── config.py           # Configuration
├── database.py         # Database operations
├── site_manager.py     # Site/DB management
├── templates/          # HTML templates
├── static/            # CSS, JS, images
├── install.sh         # Installation script
└── setup.py           # Setup utility
```

## Key Components to Understand

### 1. Flask Application (`app.py`)

Routes and request handling. Key functions:
- `login()`: Authentication
- `create_site()`: Site creation logic
- `update_site_php()`: PHP version switching

### 2. Database Layer (`database.py`)

SQLite operations. Important methods:
- `create_site()`: Store site metadata
- `get_all_sites()`: Retrieve sites
- `create_database()`: Store DB credentials

### 3. Site Manager (`site_manager.py`)

System operations. Critical functions:
- `create_site_directories()`: File structure
- `create_nginx_config()`: Generate configs
- `request_ssl_certificate()`: SSL automation

## Security Considerations

When contributing, always consider:

1. **Input Validation**
   ```python
   # Always validate user input
   if not domain or not re.match(r'^[a-z0-9.-]+$', domain):
       raise ValueError("Invalid domain")
   ```

2. **SQL Injection Prevention**
   ```python
   # Use parameterized queries
   cursor.execute('SELECT * FROM sites WHERE id = ?', (site_id,))
   # Never: f'SELECT * FROM sites WHERE id = {site_id}'
   ```

3. **Command Injection Prevention**
   ```python
   # Use subprocess with list arguments
   subprocess.run(['certbot', 'renew'], check=True)
   # Never: os.system(f'certbot renew {domain}')
   ```

4. **File Path Validation**
   ```python
   # Prevent directory traversal
   safe_path = os.path.realpath(os.path.join(base_dir, user_input))
   if not safe_path.startswith(base_dir):
       raise ValueError("Invalid path")
   ```

## Documentation

When adding features:

1. **Update README.md** - Main documentation
2. **Update CONFIGURATION.md** - If adding config options
3. **Update QUICKSTART.md** - If affecting quick start
4. **Add code comments** - For complex logic
5. **Update ARCHITECTURE.md** - For structural changes

## Questions?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- Release notes (for significant contributions)
- README acknowledgments

## Thank You!

Your contributions help make Lala Panel better for everyone. Whether it's a bug fix, feature, documentation improvement, or just a typo fix - every contribution is valued!
