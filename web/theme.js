// Runs before styles load, so a saved dark theme never flashes a light page.
(() => {
  const root = document.documentElement;
  const system = window.matchMedia("(prefers-color-scheme: dark)");

  function apply(preference = "system") {
    const dark =
      preference === "dark" || (preference === "system" && system.matches);
    root.dataset.themePreference = preference;
    root.dataset.theme = dark ? "dark" : "light";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute(
        "aria-label",
        dark ? "Switch to light mode" : "Switch to dark mode",
      );
      button.title = dark ? "Switch to light mode" : "Switch to dark mode";
      button.innerHTML = `<span aria-hidden="true">${dark ? "☀" : "☾"}</span><span>${dark ? "Light mode" : "Dark mode"}</span>`;
    });
    const selector = document.querySelector("#theme-preference");
    if (selector) selector.value = preference;
  }

  window.UWCSTheme = { apply };
  apply(root.dataset.themePreference || "system");
  system.addEventListener("change", () => {
    if (root.dataset.themePreference === "system") apply("system");
  });
  document.addEventListener("DOMContentLoaded", () =>
    apply(root.dataset.themePreference),
  );
})();
