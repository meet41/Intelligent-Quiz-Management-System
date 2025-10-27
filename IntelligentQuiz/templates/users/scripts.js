// Basic JS placeholder
// Add interactive features to the quiz interface
document.addEventListener('DOMContentLoaded', () => {
    // Highlight active navigation link
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Enhance radio button interactions
    document.querySelectorAll('.choice-list input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            // Remove active state from all labels in the group
            const list = radio.closest('.choice-list');
            list.querySelectorAll('label').forEach(label => {
                label.style.background = '';
                label.style.borderColor = 'var(--border)';
            });
            
            // Add active state to selected label
            const label = radio.closest('label');
            if (label && radio.checked) {
                label.style.background = 'var(--bg)';
                label.style.borderColor = 'var(--primary)';
            }
        });
    });

    // Auto-hide flash messages after 5 seconds
    const messages = document.querySelector('.messages');
    if (messages) {
        setTimeout(() => {
            messages.querySelectorAll('li').forEach(msg => {
                msg.style.opacity = '0';
                msg.style.transition = 'opacity 0.5s ease-out';
                setTimeout(() => msg.remove(), 500);
            });
        }, 5000);
    }

    // Add loading state to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Please wait...';
            }
        });
    });

    // Add animation to quiz cards
    document.querySelectorAll('.quiz-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });

    // Initialize tooltips for question explanations
    const explanations = document.querySelectorAll('.explanation');
    explanations.forEach(exp => {
        exp.style.cursor = 'help';
        exp.title = 'Click to see explanation';
    });
});

// Add smooth scrolling to all anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Show confirmation dialog before deleting items
document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });
});
