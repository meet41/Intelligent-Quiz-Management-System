// Basic JS placeholder

// Add interactive features to the quiz interface
document.addEventListener('DOMContentLoaded', () => {

    // Apply fade-in animations to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }


    // Stagger animations for cards
    const cards = document.querySelectorAll('.quiz-card, .category-card, .stat-card');
    cards.forEach((card, index) => {
        if (index < 3) {
            card.classList.add('fade-in', `fade-in-delay-${Math.min(index + 1, 3)}`);
        } else {
            card.classList.add('fade-in');
        }
    });


    // Global loader helper
    (function initGlobalLoader(){
        const el = document.getElementById('global-loader');
        const msgEl = el ? el.querySelector('.loader-message') : null;
        
        function show(message){
            if (!el) return;
            if (msgEl && message) msgEl.textContent = message;
            el.hidden = false;
            el.setAttribute('aria-hidden','false');
            try { document.body.setAttribute('aria-busy','true'); } catch(e) {}
        }
        function hide(){
            if (!el) return;
            el.hidden = true;
            el.setAttribute('aria-hidden','true');
            try { document.body.removeAttribute('aria-busy'); } catch(e) {}
        }

        
        // Immediately hide loader on page load
        hide();
        function wrap(promise, message){
            show(message);
            return Promise.resolve(promise).finally(hide);
        }

        // Expose globally
        window.Loader = { show, hide, wrap };

        // Auto-bind to forms/buttons with data-global-loader
        document.querySelectorAll('form[data-global-loader]')
            .forEach(f => f.addEventListener('submit', (e) => {
                const msg = f.dataset.globalLoader || 'Working on it…';
                show(msg);

                // Ensure the loader paints before navigation by deferring submission once
                if (!f.dataset.loaderArmed) {
                    e.preventDefault();
                    f.dataset.loaderArmed = '1';

                    // next frame to allow paint
                    requestAnimationFrame(() => {
                        setTimeout(() => f.submit(), 0);
                    });
                }
            }));
        document.querySelectorAll('[data-show-loader]')
            .forEach(btn => btn.addEventListener('click', (e) => {
                const msg = btn.dataset.showLoader || 'Working on it…';
                const href = btn.getAttribute('href');

                // For anchors, delay navigation to allow a paint
                if (href) {
                    e.preventDefault();
                    show(msg);
                    requestAnimationFrame(() => { setTimeout(() => { window.location.href = href; }, 0); });
                } else {
                    show(msg);
                }
            }));

        // Hide on page show from bfcache
        window.addEventListener('pageshow', () => hide());
    })();

    // Theme initialization
    (function initTheme() {
        const root = document.documentElement;
        const saved = localStorage.getItem('theme');
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = saved || (prefersDark ? 'dark' : 'light');
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            const isDark = theme === 'dark';
            toggle.setAttribute('aria-pressed', String(isDark));
            toggle.dataset.active = String(isDark);
            const sun = toggle.querySelector('.icon-sun');
            const moon = toggle.querySelector('.icon-moon');
            const label = toggle.querySelector('.label');
            if (sun && moon) {
                sun.style.display = isDark ? 'inline' : 'none';
                moon.style.display = isDark ? 'none' : 'inline';
            }
            if (label) label.textContent = isDark ? 'Light' : 'Theme';
            toggle.addEventListener('click', () => {
                const activeDark = root.getAttribute('data-theme') === 'dark';
                if (activeDark) {
                    root.removeAttribute('data-theme');
                    localStorage.setItem('theme', 'light');
                } else {
                    root.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                }
                const nowDark = root.getAttribute('data-theme') === 'dark';
                toggle.setAttribute('aria-pressed', String(nowDark));
                toggle.dataset.active = String(nowDark);
                if (sun && moon) {
                    sun.style.display = nowDark ? 'inline' : 'none';
                    moon.style.display = nowDark ? 'none' : 'inline';
                }
                if (label) label.textContent = nowDark ? 'Light' : 'Theme';
            });
        }
    })();

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
            if (submitBtn) submitBtn.disabled = true;

            // If a global loader is present for this form, don't overwrite button label
            if (!form.matches('[data-global-loader]') && submitBtn) {
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
