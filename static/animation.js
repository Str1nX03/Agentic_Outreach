document.addEventListener("DOMContentLoaded", () => {
    // 1. Glowing Cursor Effect
    const cursor = document.getElementById("glow-cursor");
    if (cursor) {
        document.addEventListener("mousemove", (e) => {
            requestAnimationFrame(() => {
                cursor.style.left = e.clientX + "px";
                cursor.style.top = e.clientY + "px";
            });
        });

        // Interactive states for buttons
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                cursor.style.width = '500px';
                cursor.style.height = '500px';
                cursor.style.background = 'radial-gradient(circle, rgba(139, 92, 246, 0.25) 0%, transparent 70%)';
            });
            btn.addEventListener('mouseleave', () => {
                cursor.style.width = '400px';
                cursor.style.height = '400px';
                cursor.style.background = 'radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 70%)';
            });
        });
    }

    // 2. Scroll Reveal Animations (Intersection Observer)
    const revealElements = document.querySelectorAll(".reveal");
    
    // Check if we are on the dashboard to trigger immediately
    const isDashboard = document.body.classList.contains('app-page');

    const revealCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("active");
            }
        });
    };

    const revealOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const revealObserver = new IntersectionObserver(revealCallback, revealOptions);

    revealElements.forEach(el => {
        revealObserver.observe(el);
        // Force immediate reveal on dashboard to prevent waiting for scroll
        if (isDashboard) {
            setTimeout(() => {
                el.classList.add("active");
            }, 100);
        }
    });

    // 3. Trigger home page hero animation immediately
    const hero = document.querySelector('.hero-content.reveal');
    if (hero) {
        setTimeout(() => {
            hero.classList.add("active");
        }, 100);
    }
});
