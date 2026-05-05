// main.js — General helpers for non-exam pages

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.querySelectorAll('.flash').forEach(el => {
            el.style.animation = 'slideOut 0.4s ease forwards';
            setTimeout(() => el.remove(), 400);
        });
    }, 5000);
});

// Smooth scroll to top on nav click
document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
});

// Add slideOut animation
const style = document.createElement('style');
style.textContent = '@keyframes slideOut{from{transform:translateX(0);opacity:1}to{transform:translateX(100px);opacity:0}}';
document.head.appendChild(style);
