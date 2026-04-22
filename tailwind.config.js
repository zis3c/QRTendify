/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./static/src/**/*.{js,html}",
    "./node_modules/flowbite/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      colors: {
        primary: "#1a73e8",
        danger: "#dc2626",
        success: "#10b981",
        warning: "#f59e0b",
      },
    },
  },
  plugins: [
    require("flowbite/plugin"),
  ],
};