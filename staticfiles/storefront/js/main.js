// Green Nest Nursery - Interactive storefront script
document.addEventListener("DOMContentLoaded", () => {
  // Mobile navigation toggle
  const mobileToggle = document.querySelector(".mobile-menu-toggle, .menu-toggle");
  const navBar = document.querySelector(".navigation-bar, .main-nav");

  if (mobileToggle && navBar) {
    mobileToggle.addEventListener("click", () => {
      const isOpen = navBar.classList.toggle("is-open");
      mobileToggle.classList.toggle("active", isOpen);
      mobileToggle.setAttribute("aria-expanded", String(isOpen));
    });

    // Close when clicking outside
    document.addEventListener("click", (e) => {
      if (!navBar.contains(e.target) && !mobileToggle.contains(e.target)) {
        navBar.classList.remove("is-open");
        mobileToggle.classList.remove("active");
        mobileToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Mobile submenu click
  const dropdownItems = document.querySelectorAll(".nav-has-dropdown > .nav-link");
  dropdownItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      if (window.innerWidth <= 991) {
        e.preventDefault();
        const parent = item.parentElement;
        parent.classList.toggle("open-submenu");
      }
    });
  });

  // Hero Slider
  const slides = [...document.querySelectorAll(".hero-slide-item, .hero-slide")];
  const dots = [...document.querySelectorAll(".slider-dot, .hero-dot")];
  const prevBtn = document.querySelector(".slider-prev, .hero-previous");
  const nextBtn = document.querySelector(".slider-next, .hero-next");
  let currentSlide = 0;
  let autoTimer;

  if (slides.length > 1) {
    function goToSlide(index) {
      currentSlide = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => {
        slide.classList.toggle("is-active", i === currentSlide);
      });
      dots.forEach((dot, i) => {
        dot.classList.toggle("is-active", i === currentSlide);
        dot.setAttribute("aria-pressed", String(i === currentSlide));
      });
    }

    function resetTimer() {
      if (autoTimer) clearInterval(autoTimer);
      autoTimer = setInterval(() => {
        goToSlide(currentSlide + 1);
      }, 5000);
    }

    dots.forEach((dot, i) => {
      dot.addEventListener("click", () => {
        goToSlide(i);
        resetTimer();
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        goToSlide(currentSlide - 1);
        resetTimer();
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        goToSlide(currentSlide + 1);
        resetTimer();
      });
    }

    resetTimer();
  }

  // Password Visibility Toggle
  const toggleButtons = document.querySelectorAll(".password-toggle-trigger");
  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const parent = btn.closest(".auth-input-wrapper");
      const input = parent ? parent.querySelector("input") : null;
      if (input) {
        if (input.type === "password") {
          input.type = "text";
          btn.innerHTML = '<span class="eye-icon">🙈</span>';
        } else {
          input.type = "password";
          btn.innerHTML = '<span class="eye-icon">👁️</span>';
        }
      }
    });
  });

});
