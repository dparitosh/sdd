import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "htmlcov/**",
      ".pytest_cache/**",
      "**/__pycache__/**",
      ".venv/**",
      "venv/**",
      "logs/**",
      "data/**/raw/**",
      "data/**/processed/**",
      "data/**/output/**",
      "coverage/**",
    ],
  },

  js.configs.recommended,

  // This repo includes several Node config files; avoid false positives on globals.
  {
    files: ["**/*.{js,cjs,mjs}", "**/*.{ts,tsx,mts,cts}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // TypeScript covers undefined vars in TS/TSX; config files often rely on Node globals.
      "no-undef": "off",
    },
  },

  // TypeScript rules (non type-aware by default; keeps lint fast and robust)
  ...tseslint.configs.recommended,

  {
    files: ["**/*.{ts,tsx}", "**/*.{mts,cts}", "**/*.d.ts"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // Existing code currently uses `any` in multiple places; keep lint actionable.
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-empty-object-type": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
];
