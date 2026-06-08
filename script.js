const year = document.getElementById("year");
const themeToggle = document.querySelector(".theme-toggle");
const themeStorageKey = "lines-spaces-theme";
const themePreference = window.matchMedia("(prefers-color-scheme: dark)");

const getStoredTheme = () => {
  try {
    return localStorage.getItem(themeStorageKey);
  } catch (_error) {
    return null;
  }
};

const storeTheme = (theme) => {
  try {
    localStorage.setItem(themeStorageKey, theme);
  } catch (_error) {
    // The visible theme still updates when storage is unavailable.
  }
};

const activeTheme = () => {
  const storedTheme = getStoredTheme();

  if (storedTheme === "dark" || storedTheme === "light") {
    return storedTheme;
  }

  return themePreference.matches ? "dark" : "light";
};

const applyTheme = (theme) => {
  document.documentElement.dataset.theme = theme;

  if (!themeToggle) {
    return;
  }

  const isDark = theme === "dark";
  themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeToggle.querySelector(".theme-toggle-text").textContent = isDark ? "Light" : "Dark";
};

if (year) {
  year.textContent = new Date().getFullYear();
}

applyTheme(activeTheme());

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const nextTheme = activeTheme() === "dark" ? "light" : "dark";
    storeTheme(nextTheme);
    applyTheme(nextTheme);
  });

  themePreference.addEventListener("change", () => {
    if (!getStoredTheme()) {
      applyTheme(activeTheme());
    }
  });
}

const revealItems = document.querySelectorAll(".about-reveal");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (revealItems.length) {
  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 },
    );

    revealItems.forEach((item) => observer.observe(item));
  }
}

const landingFlaps = document.querySelectorAll(".landing-flap");

landingFlaps.forEach((flap) => {
  const words = (flap.dataset.words || "")
    .split(",")
    .map((word) => word.trim())
    .filter(Boolean);

  if (!words.length) {
    return;
  }

  const displayLength = words.reduce((longest, word) => Math.max(longest, word.length), 0);
  let currentWord = words[0].toUpperCase().padEnd(displayLength, " ");
  const cells = [];

  const setCellCharacter = (cell, character) => {
    cell.querySelector(".landing-flap-char").textContent = character === " " ? "\u00a0" : character;
  };

  for (let index = 0; index < displayLength; index += 1) {
    const cell = document.createElement("span");
    cell.className = "landing-flap-cell";
    cell.innerHTML = '<span class="landing-flap-card"><span class="landing-flap-char"></span></span>';
    setCellCharacter(cell, currentWord[index]);
    flap.appendChild(cell);
    cells.push(cell);
  }

  if (reducedMotion || words.length === 1) {
    return;
  }

  const path = flap.closest(".landing-path");
  let timer;
  let wordQueue = [];
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

  const randomCharacter = () => alphabet[Math.floor(Math.random() * alphabet.length)];

  const shuffle = (items) => {
    const shuffled = [...items];

    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[randomIndex]] = [shuffled[randomIndex], shuffled[index]];
    }

    return shuffled;
  };

  const fillWordQueue = () => {
    wordQueue = shuffle(words);

    if (wordQueue.length > 1 && wordQueue[0].toUpperCase().padEnd(displayLength, " ") === currentWord) {
      const swapIndex = 1 + Math.floor(Math.random() * (wordQueue.length - 1));
      [wordQueue[0], wordQueue[swapIndex]] = [wordQueue[swapIndex], wordQueue[0]];
    }
  };

  const nextQueuedWord = () => {
    if (!wordQueue.length) {
      fillWordQueue();
    }

    return wordQueue.shift();
  };

  const flip = () => {
    const nextWord = nextQueuedWord().toUpperCase().padEnd(displayLength, " ");

    cells.forEach((cell, index) => {
      if (currentWord[index] === nextWord[index]) {
        return;
      }

      const delay = Math.floor(Math.random() * 260);

      window.setTimeout(() => {
        cell.classList.add("is-flipping");

        window.setTimeout(() => {
          setCellCharacter(cell, randomCharacter());
        }, 140);

        window.setTimeout(() => {
          setCellCharacter(cell, nextWord[index]);
        }, 280);

        window.setTimeout(() => {
          cell.classList.remove("is-flipping");
        }, 500);
      }, delay);
    });

    currentWord = nextWord;
  };

  const start = (delay, flipImmediately = false) => {
    window.clearInterval(timer);
    if (flipImmediately) {
      flip();
    }
    timer = window.setInterval(flip, delay);
  };

  start(4200 + Math.floor(Math.random() * 1200));

  if (path) {
    path.addEventListener("mouseenter", () => start(900, true));
    path.addEventListener("mouseleave", () => start(4200 + Math.floor(Math.random() * 1200)));
    path.addEventListener("focus", () => start(900, true));
    path.addEventListener("blur", () => start(4200 + Math.floor(Math.random() * 1200)));
  }
});
