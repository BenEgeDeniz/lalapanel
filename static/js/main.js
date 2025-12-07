/**
 * Lala Panel - Main JavaScript
 */

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Alerts are now persistent - removed auto-dismiss
    
    // Event delegation for copy-to-clipboard buttons
    document.addEventListener('click', function(e) {
        const copyBtn = e.target.closest('[data-copy]');
        if (copyBtn) {
            e.preventDefault();
            const textToCopy = copyBtn.getAttribute('data-copy');
            if (textToCopy) {
                copyToClipboard(textToCopy);
            }
        }
    });
    
    // Event delegation for delete confirmations
    document.addEventListener('submit', function(e) {
        const form = e.target;
        const confirmMsg = form.getAttribute('data-confirm');
        if (confirmMsg) {
            if (!confirm(confirmMsg)) {
                e.preventDefault();
                return false;
            }
        }
    });
});

// Confirm before deleting (kept for backward compatibility)
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}

// Copy to clipboard function
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
            // Show a temporary success message
            showCopyNotification('Copied to clipboard!');
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

// Fallback copy method for older browsers
// Note: document.execCommand('copy') is deprecated but kept for legacy browser support
// TODO: Consider removing this fallback when dropping support for browsers older than:
//       - Chrome 63 (2017), Firefox 53 (2017), Safari 13.1 (2020), Edge 79 (2020)
//       These versions fully support the modern Clipboard API
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopyNotification('Copied to clipboard!');
    } catch (err) {
        console.error('Fallback: Failed to copy', err);
        showCopyNotification('Failed to copy', true);
    }
    
    document.body.removeChild(textArea);
}

// Show copy notification
function showCopyNotification(message, isError = false) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${isError ? 'danger' : 'success'} position-fixed bottom-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    
    const icon = document.createElement('i');
    icon.className = `bi bi-${isError ? 'x-circle' : 'check-circle'}`;
    
    notification.appendChild(icon);
    notification.appendChild(document.createTextNode(' ' + message));
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}
