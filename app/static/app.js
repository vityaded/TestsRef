function setupFlashToasts() {
  const toasts = Array.from(document.querySelectorAll(".flash-toast"));
  toasts.forEach((toast, index) => {
    requestAnimationFrame(() => {
      setTimeout(() => toast.classList.add("is-visible"), 80 * index);
    });

    const dismiss = () => toast.classList.add("is-dismissing");
    toast.querySelector(".toast-close")?.addEventListener("click", dismiss);
    const ttl = Number(toast.dataset.ttl || 4800);
    setTimeout(dismiss, ttl);

    toast.addEventListener("transitionend", () => {
      if (toast.classList.contains("is-dismissing")) {
        toast.remove();
      }
    });
  });
}

function setupQuizWizard() {
  const wizard = document.querySelector("[data-quiz-wizard]");
  if (!wizard || wizard.dataset.completed === "true") return;

  const questionCards = Array.from(wizard.querySelectorAll("[data-question-step]"));
  if (!questionCards.length) return;

  wizard.classList.add("quiz-wizard-active");

  let current = 0;
  const total = questionCards.length;
  const progressBar = wizard.querySelector(".question-progress-bar");
  const progressText = wizard.querySelector(".question-progress-text");
  const nextBtn = wizard.querySelector("[data-quiz-next]");
  const prevBtn = wizard.querySelector("[data-quiz-prev]");
  const form = wizard.querySelector("[data-quiz-form]");

  function updateUI() {
    questionCards.forEach((card, idx) => card.classList.toggle("is-active", idx === current));
    if (progressBar) {
      const percent = ((current + 1) / total) * 100;
      progressBar.style.width = `${percent}%`;
    }
    if (progressText) {
      progressText.textContent = `Question ${current + 1} / ${total}`;
    }
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.textContent = current === total - 1 ? "Submit answers" : "Next question";
  }

  nextBtn?.addEventListener("click", () => {
    if (current === total - 1) {
      form?.requestSubmit();
      return;
    }
    current = Math.min(total - 1, current + 1);
    updateUI();
    wizard.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  prevBtn?.addEventListener("click", () => {
    current = Math.max(0, current - 1);
    updateUI();
  });

  updateUI();
}

function setupAutocompleteInputs() {
  const inputs = Array.from(document.querySelectorAll("[data-autocomplete-url]"));
  inputs.forEach((input) => {
    const datalist = document.querySelector(input.dataset.datalistTarget || "");
    const optionSelector = document.querySelector(input.dataset.optionTarget || "");
    let debounce;

    if (!datalist) return;

    if (optionSelector) {
      optionSelector.addEventListener("change", () => {
        if (input.value.trim().length >= 2) {
          input.dispatchEvent(new Event("input"));
        }
      });
    }

    input.addEventListener("input", () => {
      const term = input.value.trim();
      if (term.length < 2) {
        datalist.innerHTML = "";
        return;
      }

      clearTimeout(debounce);
      debounce = setTimeout(() => {
        const url = new URL(input.dataset.autocompleteUrl, window.location.origin);
        url.searchParams.set("query", term);
        if (optionSelector) {
          url.searchParams.set("search_option", optionSelector.value);
        }

        fetch(url)
          .then((res) => res.json())
          .then((items) => {
            datalist.innerHTML = "";
            (items || []).forEach((item) => {
              const value = item.label || item.value || item;
              const option = document.createElement("option");
              option.value = value;
              datalist.appendChild(option);
            });
          })
          .catch(() => {
            datalist.innerHTML = "";
          });
      }, 200);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupFlashToasts();
  setupQuizWizard();
  setupAutocompleteInputs();

  const navbar = document.getElementById("main-navbar");
  if (navbar) {
    let lastScrollTop = 0;
    const delta = 5;
    const navbarHeight = navbar.offsetHeight;

    const handleScroll = () => {
      const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
      const atTop = currentScroll <= 0;

      if (atTop) {
        navbar.classList.add("at-top");
      } else {
        navbar.classList.remove("at-top");
      }

      if (Math.abs(lastScrollTop - currentScroll) <= delta) {
        lastScrollTop = currentScroll;
        return;
      }

      if (currentScroll > lastScrollTop && currentScroll > navbarHeight) {
        navbar.classList.add("nav-hidden");
      } else {
        navbar.classList.remove("nav-hidden");
      }

      lastScrollTop = currentScroll;
    };

    window.addEventListener("scroll", handleScroll);
    handleScroll();
  }
});
