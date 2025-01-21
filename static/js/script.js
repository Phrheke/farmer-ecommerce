// Toggle menu visibility for mobile responsiveness
document.addEventListener("DOMContentLoaded", function () {
    const toggleMenu = document.querySelector(".menu-toggle");
    const menu = document.querySelector(".menu");

    if (toggleMenu && menu) {
        toggleMenu.addEventListener("click", function () {
            menu.classList.toggle("visible");
        });
    }
});
// JavaScript for Hamburger Menu
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');

hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('active');
});
