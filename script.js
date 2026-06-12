const themeToggle = document.querySelector(".theme-toggle");
const themeToggleText = themeToggle?.querySelector(".theme-toggle-text");
const themeStorageKey = "lines-spaces-theme";
const themePreference = window.matchMedia?.("(prefers-color-scheme: dark)");

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

  return themePreference?.matches ? "dark" : "light";
};

const applyTheme = (theme) => {
  document.documentElement.dataset.theme = theme;

  if (!themeToggle) {
    return;
  }

  const isDark = theme === "dark";
  themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  themeToggle.setAttribute("aria-pressed", String(isDark));

  if (themeToggleText) {
    themeToggleText.textContent = isDark ? "Light" : "Dark";
  }
};

applyTheme(activeTheme());

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const nextTheme = activeTheme() === "dark" ? "light" : "dark";
    storeTheme(nextTheme);
    applyTheme(nextTheme);
  });
}

const handleThemePreferenceChange = () => {
  if (!getStoredTheme()) {
    applyTheme(activeTheme());
  }
};

if (themePreference?.addEventListener) {
  themePreference.addEventListener("change", handleThemePreferenceChange);
} else {
  themePreference?.addListener?.(handleThemePreferenceChange);
}
