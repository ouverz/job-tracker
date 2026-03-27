/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f1117",
          1: "#161b22",
          2: "#1c2333",
          3: "#21262d",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
