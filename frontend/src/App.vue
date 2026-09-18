<template>
  <router-view />
</template>

<script setup>
</script>

<style>
:root {
  --app-blue: #2f7df4;
  --app-blue-strong: #1767df;
  --app-ink: #17243f;
  --app-muted: #71809d;
  --app-line: #dce5f2;
}
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
body { color: var(--app-ink); background: #f5f8fc; -webkit-font-smoothing: antialiased; }
button, input { letter-spacing: 0; }
.ant-card { border-color: var(--app-line) !important; border-radius: 8px !important; box-shadow: none !important; }
.ant-btn { border-radius: 6px !important; box-shadow: none !important; }
.ant-btn-primary { background: var(--app-blue) !important; }
.ant-input, .ant-input-affix-wrapper, .ant-picker, .ant-select-selector { border-radius: 6px !important; }
.ant-tabs .ant-tabs-tab-active .ant-tabs-tab-btn, .ant-tabs .ant-tabs-tab:hover { color: var(--app-blue) !important; }
.ant-tabs .ant-tabs-ink-bar { background: var(--app-blue) !important; }
</style>
