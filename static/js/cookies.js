function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function acceptCookies() {
    setCookie('cookie_accepted', 'true', 365);
    const notice = document.getElementById('cookieNotice');
    notice.classList.add('cookie-accepted');
    setTimeout(() => {
        notice.style.display = 'none';
    }, 300);
}

document.addEventListener('DOMContentLoaded', function() {
    const cookieAccepted = getCookie('cookie_accepted');
    const notice = document.getElementById('cookieNotice');
    
    if (cookieAccepted === 'true') {
        notice.style.display = 'none';
    } else {
        setTimeout(() => {
            notice.classList.add('cookie-visible');
        }, 1000);
    }
});

