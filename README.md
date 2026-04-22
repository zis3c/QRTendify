# QRTendify
Smart attendance and session management with Django + Tailwind.

## ⚠️ Current Project Status
This project is **working**, but it still has **many bugs and UI inconsistencies**.

If you like fixing real-world issues and improving developer experience, your help is very welcome.

## Why This Exists
- Build session-based attendance flows
- Support role-based organization workflows
- Generate reports and certificate-related workflows
- Keep the UI modern and practical for everyday use

## Tech Stack
- Python / Django
- SQLite (default local DB)
- Tailwind CSS
- Alpine.js (UI interactions)

## Quick Start (Windows / PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\python -m pip install -r requirements-dev.txt

Copy-Item .env.example .env
.venv\Scripts\python manage.py migrate
npm ci
npm run build:css
.venv\Scripts\python manage.py runserver
```

## Development Commands
```powershell
# Build Tailwind once
npm run build:css

# Watch Tailwind
npm run watch:css

# Django checks
.venv\Scripts\python manage.py check
```

## Contributing (Please!)
Contributions are encouraged, especially for:
- UI consistency fixes
- Sidebar and layout edge cases
- Form/placeholder styling consistency
- Session creation UX bugs
- Regression tests for critical flows

### Suggested Contribution Flow
1. Create a branch from `main`
2. Keep PRs focused and small
3. Include before/after screenshots for UI fixes
4. Add test coverage where possible
5. Open a PR with clear reproduction steps

## Security Notes
- Never commit `.env` or secret keys
- Keep credentials in environment variables only
- Review staged files before every push:
```powershell
git status
git diff --staged
```

---
Built with momentum, still evolving.  
If it breaks, let’s fix it together 💙
