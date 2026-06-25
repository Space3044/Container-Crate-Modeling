# Light and Dark Theme Design

## Scope

The web visualizer will keep the current layout and workflow. The change only adds a light-first theme system and a manual dark theme switch.

Default behavior:

- First load uses the light theme.
- If the user switches to dark theme, the choice is saved locally.
- Future loads apply the saved theme before the stylesheet paints the page.

## Visual Direction

The light theme should feel like an operations dashboard:

- Page background: cool off-white with subtle blue-gray depth.
- Panels: white or near-white surfaces with visible borders.
- Text: dark slate for primary text, slate gray for secondary text.
- Accent: keep the existing blue/cyan identity for primary actions, focus rings, active states, and selected records.
- Status colors: preserve green for success and red for errors, adjusted for light contrast.

The dark theme should preserve the current look. Existing dark colors will move behind `html[data-theme="dark"]` tokens rather than being rewritten as a new style.

## Architecture

Use CSS custom properties as the theme contract.

- `:root` defines the light theme tokens.
- `html[data-theme="dark"]` defines dark theme overrides.
- Component rules consume tokens instead of hard-coded dark colors where the element changes between themes.
- Canvas CSS backgrounds use tokens where possible.
- Canvas drawing colors that are currently hard-coded will use a small JavaScript theme palette helper where needed.

Use one local storage key for theme preference. The absence of that key means light theme.

## UI Behavior

Add a theme toggle button in the header action group.

- The button label reflects the action or current mode clearly.
- The control is keyboard reachable and has an accessible label.
- Switching theme updates the `html[data-theme]` attribute and redraws visualizations.
- Theme selection is persisted with `localStorage`.

Add an inline script in `web/index.html` before loading CSS. It reads the saved preference and sets `document.documentElement.dataset.theme = "dark"` only when the saved value is dark. This prevents a dark-theme user from seeing a light flash during page load.

## Testing

Add focused asset tests for:

- Default HTML does not force dark theme.
- `styles.css` defines light root tokens and dark overrides.
- `index.html` contains the early theme initialization script.
- `app.js` caches and binds the theme toggle button.
- Theme changes persist in `localStorage`.

Run the web asset test suite after implementation.

## Out Of Scope

- No layout redesign.
- No new frontend framework.
- No system-theme auto mode.
- No changes to solver behavior or export file data.
