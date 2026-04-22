# QRTendify

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)
![Tailwind](https://img.shields.io/badge/TailwindCSS-3.x-06B6D4?logo=tailwindcss&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)

Attendance and session management platform built with Django + Tailwind.

> [!WARNING]
> This project is **working**, but still has **many bugs and UI inconsistencies**.  
> Contributions are strongly welcomed to help stabilize and improve it.

## Features

- 📅 Session creation and management
- 👥 Organization/member based access flows
- 🧾 Attendance tracking and reports
- 🏅 Certificate workflow pages
- 🎨 Ongoing global UI consistency improvements

## Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/zis3c/QRTendify.git
   cd QRTendify
   ```

2. **Install backend dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\python -m pip install -U pip
   .venv\Scripts\python -m pip install -r requirements-dev.txt
   ```

3. **Configure environment**
   ```bash
   copy .env.example .env
   ```

4. **Install frontend dependencies**
   ```bash
   npm ci
   npm run build:css
   ```

5. **Run app**
   ```bash
   .venv\Scripts\python manage.py migrate
   .venv\Scripts\python manage.py runserver
   ```

## Project Structure

```text
Qrtendify/
├── QRTendify_project/        # Django project settings and urls
├── core/                     # Main app logic (models/views/forms/services)
├── templates/                # Django templates
├── static/                   # Tailwind source, built CSS, JS, assets
├── scripts/                  # Utility / smoke scripts
├── requirements*.txt         # Python dependencies
├── package.json              # Frontend toolchain config
└── README.md                 # Project documentation
```

## Usage

### Run development server
```bash
.venv\Scripts\python manage.py runserver
```

### Build Tailwind CSS
```bash
npm run build:css
```

### Watch Tailwind CSS
```bash
npm run watch:css
```

### Basic project checks
```bash
.venv\Scripts\python manage.py check
```

## Contributing

Contributions are very welcome, especially for bug fixes.

Priority areas:
- Sidebar behavior and visual glitches
- Form control consistency (placeholder, focus, sizing)
- Session creation UI/UX edge cases
- Regression testing for critical flows

### Suggested PR flow
1. Create a branch from `main`
2. Keep PR scope focused
3. Include reproduction + fix notes
4. Attach before/after UI screenshots if relevant

## Contributors

Special shoutout to **Idham** and **Koden**. Jangan malas, fix this QRTendify lah

## Security Notes

- Never commit `.env` or credentials
- Keep API keys/secrets in environment variables only
- Review staged files before push:
  ```bash
  git status
  git diff --staged
  ```

## License

License is currently **not specified** in this repository.
