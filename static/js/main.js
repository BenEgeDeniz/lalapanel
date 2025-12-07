/**
 * Lala Panel - Main JavaScript
 */

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Confirm before deleting
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
    notification.innerHTML = `
        <i class="bi bi-${isError ? 'x-circle' : 'check-circle'}"></i> ${message}
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}
