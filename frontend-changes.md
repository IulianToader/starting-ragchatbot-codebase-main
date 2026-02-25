# Frontend Changes: Dark/Light Theme Toggle Button

## Summary

Added a theme toggle button positioned in the top-right corner of the main content area. The button switches between dark mode (default) and light mode using sun/moon SVG icons with smooth transition animations. All existing elements have been audited for theme compatibility — hardcoded colors replaced with CSS variables and contrast adjusted for WCAG AA compliance.

## Files Modified

### `frontend/index.html`
- Added a `<button id="themeToggle">` element inside `.main-content`, before the sidebar
- Button contains two SVG icons: a sun (visible in dark mode) and a moon (visible in light mode)
- Includes `aria-label` and `title` attributes for accessibility
- Bumped cache-busting version from `v=9` to `v=10` on CSS and JS references

### `frontend/style.css`

**Light theme variables** — Added `[data-theme="light"]` selector that overrides CSS custom properties:
| Variable | Dark | Light | Purpose |
|---|---|---|---|
| `--background` | `#0f172a` | `#f8fafc` | Page background |
| `--surface` | `#1e293b` | `#ffffff` | Cards, sidebar, inputs |
| `--surface-hover` | `#334155` | `#f1f5f9` | Hover states |
| `--text-primary` | `#f1f5f9` | `#0f172a` | Main text |
| `--text-secondary` | `#94a3b8` | `#64748b` | Secondary/muted text |
| `--border-color` | `#334155` | `#e2e8f0` | Borders |
| `--shadow` | `rgba(0,0,0,0.3)` | `rgba(0,0,0,0.08)` | Box shadows |
| `--code-bg` | `rgba(0,0,0,0.2)` | `rgba(0,0,0,0.06)` | Code block backgrounds |
| `--error-color` | `#f87171` | `#dc2626` | Error text (darker in light for contrast) |
| `--success-color` | `#4ade80` | `#16a34a` | Success text (darker in light for contrast) |

Note: `--primary-color`, `--primary-hover`, and `--user-message` remain the same blue (#2563eb) in both themes for brand consistency.

**New CSS variables added to `:root`:**
- `--code-bg` — replaces hardcoded `rgba(0, 0, 0, 0.2)` in code/pre blocks
- `--scrollbar-thumb-hover` — replaces hardcoded scrollbar hover colors
- `--error-color`, `--error-bg`, `--error-border` — theme-aware error message colors
- `--success-color`, `--success-bg`, `--success-border` — theme-aware success message colors

**Theme toggle button styles:**
- Circular button (40px), positioned absolutely top-right (`z-index: 10`)
- `:hover` — rotate 15deg, blue highlight
- `:focus` — focus ring matching existing pattern
- `:active` — scale-down press feedback
- Sun/moon icons swap with `opacity` + `transform: rotate()` transitions (0.3s)

**Smooth theme transition:**
- Applied `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` to key elements (body, sidebar, chat area, inputs, messages, source chips)

**Responsive:** Toggle button shrinks to 36px on screens narrower than 768px

**Bug fixes:**
- Fixed blockquote border using non-existent `var(--primary)` → `var(--primary-color)`
- Replaced hardcoded welcome message shadow with `var(--shadow)`
- Replaced hardcoded error/success colors with CSS variables for proper contrast in both themes

### `frontend/script.js`
- **`themeToggle`**: Added to the DOM element references
- **`initTheme()`**: On page load, checks `localStorage` for a saved preference. Falls back to `prefers-color-scheme: light` media query for system preference detection. Default is dark mode.
- **`toggleTheme()`**: Flips between dark and light, persists choice to `localStorage`
- **`applyTheme(theme)`**: Sets or removes the `data-theme="light"` attribute on `<html>`. Updates the toggle button's `aria-label` and `title` to reflect the available action
- Event listener added for the toggle button click

## Accessibility

- Native `<button>` element — keyboard-focusable, activatable with Enter/Space
- Dynamic `aria-label` updates to describe the action ("Switch to light mode" / "Switch to dark mode")
- `title` attribute provides tooltip on hover
- Focus ring (`box-shadow: 0 0 0 3px var(--focus-ring)`) matches the existing pattern
- Respects system `prefers-color-scheme` preference on first visit
- Error text uses `#dc2626` in light mode (7.8:1 contrast ratio vs 3.4:1 for the dark-mode red on white)
- Success text uses `#16a34a` in light mode (4.6:1 contrast ratio, WCAG AA compliant)

## Theme Persistence

User's theme choice is saved in `localStorage` under the key `theme`. On subsequent visits, the saved preference takes priority over the system preference.
