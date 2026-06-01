export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        drought: {
          low: "#22c55e",
          moderate: "#f59e0b",
          severe: "#ef4444",
          extreme: "#7f1d1d"
        }
      }
    }
  },
  plugins: []
};

