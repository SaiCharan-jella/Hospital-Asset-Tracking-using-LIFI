/**
 * Main JavaScript for Hospital LiFi Handoff System
 * Handles interactive features and real-time updates
 */

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
});

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// File upload drag and drop enhancement
const uploadAreas = document.querySelectorAll('.upload-area');
uploadAreas.forEach(area => {
    const fileInput = area.querySelector('input[type="file"]');

    if (fileInput) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.style.borderColor = 'var(--lifi-blue)';
                area.style.background = 'rgba(0, 212, 255, 0.1)';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.style.borderColor = 'var(--glass-border)';
                area.style.background = 'transparent';
            }, false);
        });

        // Handle dropped files
        area.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files.length > 0) {
                fileInput.files = files;
                showFileInfo(area, files[0]);
            }
        }, false);

        // Handle file selection via click
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                showFileInfo(area, e.target.files[0]);
            }
        });
    }
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function showFileInfo(area, file) {
    const uploadIcon = area.querySelector('.upload-icon');
    const heading = area.querySelector('h3');

    if (uploadIcon && heading) {
        uploadIcon.textContent = '✓';
        uploadIcon.style.color = 'var(--success)';
        heading.textContent = `Selected: ${file.name}`;
        heading.style.color = 'var(--lifi-blue)';

        // Show file size
        const sizeText = area.querySelector('.upload-hint');
        if (sizeText) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            sizeText.textContent = `File size: ${sizeMB} MB - Ready to encrypt and upload`;
            sizeText.style.color = 'var(--success)';
        }
    }
}

// Real-time statistics update (optional)
function updateStatistics() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            // Update stat cards if they exist
            updateStatCard('total_users', data.total_users);
            updateStatCard('pending_users', data.pending_users);
            updateStatCard('total_assets', data.total_assets);
            updateStatCard('total_files', data.total_files);
            updateStatCard('active_handoffs', data.active_handoffs);
        })
        .catch(error => console.log('Statistics update disabled'));
}

function updateStatCard(key, value) {
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach(card => {
        const text = card.querySelector('p');
        if (text && text.textContent.toLowerCase().includes(key.replace('_', ' '))) {
            const valueElement = card.querySelector('h3');
            if (valueElement && valueElement.textContent !== value.toString()) {
                valueElement.textContent = value;
                card.style.animation = 'pulse 0.5s ease-out';
            }
        }
    });
}

// Add pulse animation
const pulseStyle = document.createElement('style');
pulseStyle.textContent = `
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
`;
document.head.appendChild(pulseStyle);

// Update statistics every 30 seconds if on dashboard
if (window.location.pathname.includes('dashboard')) {
    updateStatistics();
    setInterval(updateStatistics, 30000);
}

// Form validation
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('submit', function (e) {
        const fileInput = form.querySelector('input[type="file"]');

        if (fileInput && fileInput.required && fileInput.files.length === 0) {
            e.preventDefault();
            alert('Please select a file to upload.');
            return false;
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span>⏳ Processing...</span>';

            // Re-enable after 10 seconds in case of error
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }, 10000);
        }
    });
});

// Copy to clipboard functionality for code elements
document.querySelectorAll('code').forEach(codeBlock => {
    codeBlock.style.cursor = 'pointer';
    codeBlock.title = 'Click to copy';

    codeBlock.addEventListener('click', function () {
        const text = this.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const originalBg = this.style.background;
            this.style.background = 'rgba(16, 185, 129, 0.2)';
            setTimeout(() => {
                this.style.background = originalBg;
            }, 500);
        });
    });
});

// Role info display on signup page
const roleSelect = document.getElementById('role');
if (roleSelect) {
    roleSelect.addEventListener('change', function () {
        const infoDiv = document.getElementById('role-info');
        if (infoDiv) {
            infoDiv.style.animation = 'fadeIn 0.3s ease-out';
        }
    });
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Table row highlighting
document.querySelectorAll('.data-table tbody tr').forEach(row => {
    row.addEventListener('click', function () {
        // Remove highlight from other rows
        document.querySelectorAll('.data-table tbody tr').forEach(r => {
            r.style.background = '';
        });
        // Highlight clicked row
        this.style.background = 'rgba(0, 212, 255, 0.15)';
    });
});

// Console welcome message
console.log('%c Hospital LiFi Handoff System ', 'background: linear-gradient(135deg, #00d4ff, #00ff88); color: white; font-size: 16px; padding: 10px; border-radius: 5px;');
console.log('%c Fernet-AES128 Encryption Active ', 'background: #10b981; color: white; font-size: 12px; padding: 5px; border-radius: 3px;');
console.log('%c Simulating Stable Optical Handoff ', 'background: #8b5cf6; color: white; font-size: 12px; padding: 5px; border-radius: 3px;');
