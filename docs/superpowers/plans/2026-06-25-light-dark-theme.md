# Light and Dark Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a light-default theme with a persisted manual dark mode switch for the static web visualizer.

**Architecture:** Keep the current HTML/CSS/JS app. Move page colors behind CSS custom properties, set light tokens in `:root`, preserve the existing dark look in `html[data-theme="dark"]`, and use a small JavaScript theme state helper for the toggle and canvas redraw.

**Tech Stack:** Static HTML, CSS custom properties, vanilla JavaScript, Python `unittest` asset tests.

---

## Files

- Modify: `tests/test_web_visualizer_assets.py`
  Adds focused asset tests for default light theme, dark overrides, early theme bootstrapping, and JavaScript theme persistence.
- Modify: `web/index.html`
  Adds the early theme script and the header theme toggle button.
- Modify: `web/styles.css`
  Defines light tokens, dark token overrides, and updates theme-sensitive component colors to use tokens.
- Modify: `web/app.js`
  Caches and binds the theme toggle, persists theme preference, updates button text, and redraws canvas views after theme changes.

## Tasks

### Task 1: Theme Asset Tests

- [ ] Add tests in `tests/test_web_visualizer_assets.py`:
  - `test_visualizer_page_has_light_default_theme_bootstrap_and_toggle`
  - `test_visualizer_styles_define_light_tokens_and_dark_overrides`
  - add theme helper names to the existing script behavior assertion
- [ ] Run `python -m unittest tests.test_web_visualizer_assets.WebVisualizerAssetsTests.test_visualizer_page_has_light_default_theme_bootstrap_and_toggle tests.test_web_visualizer_assets.WebVisualizerAssetsTests.test_visualizer_styles_define_light_tokens_and_dark_overrides tests.test_web_visualizer_assets.WebVisualizerAssetsTests.test_visualizer_script_contains_projection_and_selection_behaviors`
- [ ] Confirm the new tests fail because `themeToggleButton`, `THEME_STORAGE_KEY`, and `html[data-theme="dark"]` are not implemented yet.

### Task 2: HTML Theme Entry Points

- [ ] Add an inline `<script>` in `web/index.html` before the stylesheet link:
  ```html
  <script>
    (() => {
      try {
        if (localStorage.getItem("uld-packing-theme") === "dark") {
          document.documentElement.dataset.theme = "dark";
        }
      } catch {
        document.documentElement.dataset.theme = "";
      }
    })();
  </script>
  ```
- [ ] Add `<button id="themeToggleButton" type="button" class="secondary-button theme-toggle-button" aria-label="切换深色主题">深色模式</button>` inside `.header-actions`.

### Task 3: CSS Theme Tokens

- [ ] Change `:root` to light defaults with `color-scheme: light`.
- [ ] Add `html[data-theme="dark"]` with the current dark token values.
- [ ] Add token variables for theme-sensitive gradients, controls, cards, table headers, canvas surfaces, tooltips, selected states, and status surfaces.
- [ ] Replace hard-coded dark values in visible app styles with those tokens.
- [ ] Keep layout variables unchanged.

### Task 4: JavaScript Theme State

- [ ] Add `const THEME_STORAGE_KEY = "uld-packing-theme";`.
- [ ] Cache `elements.themeToggleButton`.
- [ ] Bind the toggle click handler.
- [ ] Implement:
  ```javascript
  function initializeTheme() {
    updateThemeToggle();
  }

  function currentTheme() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  }

  function toggleTheme() {
    const nextTheme = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.dataset.theme = "dark";
      localStorage.setItem(THEME_STORAGE_KEY, "dark");
    } else {
      delete document.documentElement.dataset.theme;
      localStorage.removeItem(THEME_STORAGE_KEY);
    }
    updateThemeToggle();
    drawAllViews();
  }

  function updateThemeToggle() {
    if (!elements.themeToggleButton) {
      return;
    }
    const dark = currentTheme() === "dark";
    elements.themeToggleButton.textContent = dark ? "亮色模式" : "深色模式";
    elements.themeToggleButton.setAttribute("aria-label", dark ? "切换亮色主题" : "切换深色主题");
    elements.themeToggleButton.setAttribute("aria-pressed", String(dark));
  }
  ```

### Task 5: Verification

- [ ] Run the focused failing tests again and confirm they pass.
- [ ] Run `python -m unittest tests.test_web_visualizer_assets`.
- [ ] Do not use Playwright.
- [ ] Do not create a git commit unless the user explicitly asks for one.
