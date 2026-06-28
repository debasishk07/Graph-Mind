import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // GraphMind Design System - Dark Intelligence
        void: "#080B14",
        surface: "#0E1220",
        elevated: "#151C2E",
        border: "#1E2A42",
        "border-subtle": "#1E2A42",
        "accent-primary": "#3B82F6",
        "accent-graph": "#8B5CF6",
        "accent-success": "#10B981",
        "accent-danger": "#EF4444",
        "accent-warn": "#F59E0B",
        "text-primary": "#F1F5F9",
        "text-secondary": "#94A3B8",
        "text-muted": "#475569",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "monospace"],
        sans: ["Inter", "sans-serif"],
        display: ["JetBrains Mono", "monospace"],
      },
      fontSize: {
        "display-xl": ["72px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "display-lg": ["48px", { lineHeight: "1.15", letterSpacing: "-0.01em" }],
        "display-md": ["36px", { lineHeight: "1.2", letterSpacing: "0" }],
        "display-sm": ["24px", { lineHeight: "1.3" }],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "shimmer": "shimmer 2s linear infinite",
        "slide-in": "slideIn 200ms ease-out",
        "slide-out": "slideOut 200ms ease-in",
        "fade-in": "fadeIn 200ms ease-out",
        "scale-in": "scaleIn 150ms ease-out",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        slideIn: {
          "0%": { transform: "translateX(-100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        slideOut: {
          "0%": { transform: "translateX(0)", opacity: "1" },
          "100%": { transform: "translateX(-100%)", opacity: "0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "shimmer": "linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)",
      },
      boxShadow: {
        "glow-primary": "0 0 20px rgba(59, 130, 246, 0.3)",
        "glow-graph": "0 0 20px rgba(139, 92, 246, 0.3)",
        "glow-danger": "0 0 20px rgba(239, 68, 68, 0.3)",
        "glow-success": "0 0 20px rgba(16, 185, 129, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;