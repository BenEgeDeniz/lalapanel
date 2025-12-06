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
