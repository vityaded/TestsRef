# UI redesign baseline

_Date: 2025-12-20_

## Stack and entrypoints discovered
- Flask application factory in `app/__init__.py` with blueprints for main content, tests, reading, games, and authentication.
- Templates live under `app/templates`, with the base layout in `app/templates/layouts/base.html`.
- Static assets are served from `app/static` and currently include a single `styles.css` file; no Node/Vite/Webpack build pipeline or package manifest was found.
- Styling leans on Bootstrap 4.5.2 (CDN) plus custom CSS; JavaScript helpers rely on jQuery/jQuery UI on specific pages.

## Current UX observations
- Navigation is a plain Bootstrap navbar with inline links and inline flash alerts.
- Home page shows a compact search form and a vertical list of book cards without a hero/CTA or strong game identity.
- Quiz pages render selects/inputs in a simple list; drag-and-drop mode uses jQuery UI sortable with minimal visual feedback.
- A floating “+” button opens creation links for authenticated users, but it inherits default Bootstrap styling.

## Baseline performance notes
- External CDN assets (Bootstrap, jQuery) load synchronously without `defer`; no asset minification or hashing is configured.
- No compression or caching middleware is present in the Flask setup by default.
- Lighthouse, request timing, and database query counts have not been recorded yet in this environment. Capture these metrics after spinning up the server for comparison.

## Next measurement actions
- Run the app locally, capture Lighthouse for Home and Quiz flows, and attach screenshot paths.
- Log server request durations and review SQL query counts on list/quiz endpoints.
- Document any slow assets or blocking scripts before further optimization.
