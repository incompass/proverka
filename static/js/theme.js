const html = document.documentElement;
const themeButtons = document.querySelectorAll('.theme-btn');

function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function setTheme(theme) {
    if (theme === 'system') {
        html.setAttribute('data-theme', 'system');
    } else {
        html.setAttribute('data-theme', theme);
    }
    
    localStorage.setItem('theme', theme);
    updateActiveButton(theme);
}

function updateActiveButton(theme) {
    themeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.theme === theme) {
            btn.classList.add('active');
        }
    });
}

const savedTheme = localStorage.getItem('theme') || 'system';
setTheme(savedTheme);

themeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        setTheme(btn.dataset.theme);
    });
});

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (html.getAttribute('data-theme') === 'system') {
        html.setAttribute('data-theme', 'system');
    }
});

