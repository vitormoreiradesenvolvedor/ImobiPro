import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      // Quebra de linha em markup é assunto do Prettier, não do ESLint.
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/html-closing-bracket-newline': 'off',
      // Indentação também: o Prettier reindenta e as duas regras brigavam.
      'vue/html-indent': 'off',
      // Diálogos nativos travam a thread: usamos o ConfirmHost.
      'no-alert': 'error',
      'no-console': ['error', { allow: ['warn', 'error'] }],
      eqeqeq: ['error', 'smart'],
      'no-var': 'error',
      'prefer-const': 'error',
    },
  },
  {
    files: ['tests/**/*.js'],
    languageOptions: { globals: { ...globals.node } },
  },
  // Scripts de produção de mídia: rodam no Node e injetam código no navegador.
  {
    files: ['scripts/**/*.mjs'],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
  // Saída de ferramenta, não código do projeto: relatório e traces do Playwright.
  {
    ignores: [
      'dist/',
      'node_modules/',
      'coverage/',
      'tests/e2e/relatorio/',
      'tests/e2e/telas/',
      'test-results/',
    ],
  },
]
