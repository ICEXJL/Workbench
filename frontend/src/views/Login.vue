<template>
  <main class="login-page">
    <div class="ambient-grid" aria-hidden="true"></div>
    <div class="ambient-lines" aria-hidden="true">
      <span class="ambient-line line-one"></span>
      <span class="ambient-line line-two"></span>
      <span class="ambient-line line-three"></span>
    </div>

    <header class="brand-lockup">
      <img class="brand-logo" src="/logo-transparent.png" alt="EnjoyOurs" />
      <span class="brand-divider"></span>
      <span class="brand-label">SEA OPERATIONS HUB</span>
    </header>

    <div class="login-layout">
      <section class="login-intro" aria-labelledby="login-heading">
        <p class="intro-kicker">GLOBAL COMMERCE / 2026</p>
        <h1 id="login-heading">把每一次出海，<br /><em>变成可复制的增长。</em></h1>
        <p class="intro-copy">跨境运营工作台</p>
        <div class="intro-signal" aria-hidden="true">
          <span class="signal-dot"></span>
          <span class="signal-line"></span>
          <span class="signal-text">OPERATIONS ONLINE</span>
        </div>
      </section>

      <section class="login-card" aria-labelledby="card-heading">
        <div class="card-heading">
          <p class="card-kicker">WORKSPACE ACCESS</p>
          <h2 id="card-heading">欢迎回来</h2>
          <p>登录您的运营工作台</p>
        </div>

        <form class="login-form" @submit.prevent="handleLogin">
          <label class="field-group" for="username">
            <span class="field-label">账号</span>
            <span class="field-control">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21a8 8 0 0 0-16 0M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" /></svg>
              <input id="username" v-model.trim="form.username" autocomplete="username" placeholder="请输入账号" required />
            </span>
          </label>

          <label class="field-group" for="password">
            <span class="field-label">密码</span>
            <span class="field-control">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
              <input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码" required />
              <button class="password-toggle" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
                <svg v-if="!showPassword" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2A10.5 10.5 0 0 1 12 6c6 0 9.5 6 9.5 6a16 16 0 0 1-3.2 3.7M6.3 6.4C3.9 8.2 2.5 12 2.5 12s3.5 6 9.5 6c1.1 0 2.1-.2 3-.6" /><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" /></svg>
              </button>
            </span>
          </label>

          <div class="form-options">
            <label class="remember-option"><input v-model="rememberMe" type="checkbox" /> <span>记住登录</span></label>
            <button class="forgot-button" type="button" @click="showForgotMessage">忘记密码？</button>
          </div>

          <button class="submit-button" type="submit" :class="{ loading }" :disabled="loading">
            <span>{{ loading ? '正在验证…' : '进入工作台' }}</span>
            <svg v-if="!loading" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
        </form>

        <p v-if="notice" class="form-notice" role="status">{{ notice }}</p>
        <div class="card-footer">
          <span class="secure-mark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 19 6v5c0 4.4-2.7 8-7 10-4.3-2-7-5.6-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></svg>安全连接</span>
          <span>EnjoyOurs · Southeast Asia</span>
        </div>
      </section>
    </div>

    <footer class="login-footer">
      <span>ENJOYourS OPERATIONS</span>
      <span class="footer-rule"></span>
      <span>让业务更清晰，让决策更靠前</span>
    </footer>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = ref({ username: '', password: '' })
const rememberMe = ref(true)
const showPassword = ref(false)
const loading = ref(false)
const notice = ref('')

async function handleLogin() {
  if (!form.value.username || !form.value.password || loading.value) return
  notice.value = ''
  loading.value = true
  try {
    await authStore.login(form.value.username, form.value.password)
    router.push('/daily')
  } catch (e) {
    // 请求拦截器负责显示接口错误，这里只结束按钮状态。
  } finally {
    loading.value = false
  }
}

function showForgotMessage() {
  notice.value = '请联系管理员重置登录密码'
}
</script>

<style scoped>
:global(*) { box-sizing: border-box; }
:global(body) { margin: 0; color: #17243f; background: #edf5ff; }
:global(button), :global(input) { font: inherit; }

.login-page {
  --ink: #17243f;
  --muted: #71809d;
  --paper: #fffefa;
  --line: #d8e4f3;
  --teal: #4b91f7;
  --teal-dark: #2f7df4;
  --coral: #d88963;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  isolation: isolate;
  background: #edf5ff;
  padding: 38px 5.5vw 30px;
}

.ambient-grid, .ambient-lines { position: absolute; inset: 0; pointer-events: none; }
.ambient-grid {
  z-index: -3;
  opacity: .55;
  background-image: linear-gradient(rgba(47, 125, 244, .07) 1px, transparent 1px), linear-gradient(90deg, rgba(47, 125, 244, .07) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(90deg, #000 0%, rgba(0, 0, 0, .86) 48%, transparent 92%);
  animation: grid-drift 28s linear infinite;
}
.ambient-lines { z-index: -2; overflow: hidden; }
.ambient-line {
  position: absolute;
  display: block;
  height: 18vw;
  width: 78vw;
  border-top: 1px solid rgba(47, 125, 244, .2);
  border-bottom: 1px solid rgba(255, 255, 255, .8);
  transform: rotate(-18deg) translate3d(0, 0, 0);
  animation: line-drift 18s ease-in-out infinite alternate;
}
.line-one { top: 8%; left: -12%; }
.line-two { right: -22%; bottom: 1%; transform: rotate(-18deg) scale(.82); animation-delay: -7s; }
.line-three { top: 48%; left: 44%; transform: rotate(62deg) scale(.44); opacity: .55; animation-delay: -12s; }

.brand-lockup, .login-layout, .login-footer { position: relative; z-index: 1; }
.brand-lockup { display: flex; align-items: center; gap: 16px; min-height: 42px; }
.brand-logo { display: block; width: 176px; height: auto; mix-blend-mode: screen; filter: saturate(.86); }
.brand-divider, .footer-rule { width: 1px; height: 18px; background: rgba(23, 36, 63, .2); }
.brand-label, .intro-kicker, .card-kicker, .signal-text { font-size: 10px; font-weight: 700; letter-spacing: .22em; color: var(--teal-dark); }
.brand-label { color: var(--muted); }

.login-layout {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(420px, 490px);
  gap: clamp(48px, 8vw, 148px);
  align-items: center;
  max-width: 1240px;
  min-height: calc(100vh - 150px);
  margin: 0 auto;
}
.login-intro { padding: 8vh 0 7vh clamp(0px, 2vw, 30px); }
.intro-kicker, .card-kicker { margin: 0 0 24px; }
.login-intro h1 { max-width: 640px; margin: 0; font-size: clamp(38px, 4.6vw, 68px); font-weight: 500; line-height: 1.12; letter-spacing: -.04em; color: var(--ink); }
.login-intro h1 em { color: var(--teal-dark); font-style: normal; }
.intro-copy { margin: 28px 0 0; color: var(--muted); font-size: 18px; letter-spacing: .12em; }
.intro-signal { display: flex; align-items: center; gap: 12px; margin-top: 76px; color: var(--muted); }
.signal-dot { width: 8px; height: 8px; border: 2px solid var(--teal); border-radius: 50%; box-shadow: 0 0 0 5px rgba(47, 125, 244, .09); animation: pulse 2.4s ease-in-out infinite; }
.signal-line { width: 74px; height: 1px; background: var(--teal); opacity: .55; }

.login-card { width: 100%; padding: 50px 52px 34px; border: 1px solid rgba(216, 228, 243, .98); border-radius: 10px; background: rgba(255, 255, 255, .97); box-shadow: 0 26px 80px rgba(42, 91, 161, .13), 0 5px 18px rgba(42, 91, 161, .06); }
.card-heading h2 { margin: 0; color: var(--ink); font-size: 30px; font-weight: 600; letter-spacing: -.035em; }
.card-heading p:last-child { margin: 10px 0 0; color: var(--muted); font-size: 14px; }
.login-form { margin-top: 36px; }
.field-group { display: block; margin-bottom: 23px; color: var(--ink); }
.field-label { display: block; margin-bottom: 9px; font-size: 13px; font-weight: 600; }
.field-control { display: flex; align-items: center; gap: 12px; min-height: 52px; padding: 0 15px; border: 1px solid var(--line); border-radius: 6px; background: #fcfdfb; transition: border-color .2s, box-shadow .2s, background .2s; }
.field-control:focus-within { border-color: var(--teal); background: #fff; box-shadow: 0 0 0 4px rgba(47, 125, 244, .11); }
.field-control > svg, .password-toggle svg, .submit-button svg, .secure-mark svg { flex: 0 0 auto; width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.field-control > svg { color: #90a6a7; }
.field-control input { min-width: 0; flex: 1; border: 0; outline: 0; color: var(--ink); background: transparent; font-size: 15px; }
.field-control input::placeholder { color: #a6b5b5; }
.password-toggle, .forgot-button { padding: 0; border: 0; color: var(--muted); background: transparent; cursor: pointer; }
.password-toggle { display: grid; place-items: center; width: 24px; height: 30px; }
.password-toggle:hover, .forgot-button:hover { color: var(--teal-dark); }
.form-options { display: flex; justify-content: space-between; align-items: center; margin: 2px 0 30px; color: var(--muted); font-size: 13px; }
.remember-option { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.remember-option input { width: 15px; height: 15px; margin: 0; accent-color: var(--teal); }
.submit-button { display: flex; align-items: center; justify-content: center; gap: 12px; width: 100%; min-height: 54px; border: 0; border-radius: 6px; color: #fff; background: var(--teal-dark); box-shadow: 0 8px 18px rgba(47, 125, 244, .2); cursor: pointer; font-size: 15px; font-weight: 600; transition: transform .2s, background .2s, box-shadow .2s; }
.submit-button:hover:not(:disabled) { background: #1767df; box-shadow: 0 12px 26px rgba(47, 125, 244, .26); transform: translateY(-1px); }
.submit-button:active:not(:disabled) { transform: translateY(0); }
.submit-button:disabled { cursor: wait; opacity: .72; }
.form-notice { margin: 16px 0 0; padding: 10px 12px; border-left: 2px solid var(--coral); color: #9b6045; background: #fff3ed; font-size: 13px; }
.card-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 34px; padding-top: 18px; border-top: 1px solid var(--line); color: #91a3a3; font-size: 11px; }
.secure-mark { display: inline-flex; align-items: center; gap: 6px; }
.secure-mark svg { width: 14px; height: 14px; color: var(--teal); }
.login-footer { display: flex; align-items: center; gap: 14px; color: #88a09f; font-size: 10px; letter-spacing: .12em; }
.footer-rule { height: 1px; width: 34px; }

@keyframes grid-drift { from { transform: translate3d(0, 0, 0); } to { transform: translate3d(48px, 48px, 0); } }
@keyframes line-drift { from { margin-left: -1.5vw; opacity: .42; } to { margin-left: 3vw; opacity: .86; } }
@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 5px rgba(47, 125, 244, .09); } 50% { box-shadow: 0 0 0 9px rgba(47, 125, 244, .03); } }

@media (max-width: 1100px) and (min-width: 901px) {
  .login-layout { grid-template-columns: minmax(300px, 1fr) minmax(400px, 440px); gap: 42px; }
  .login-intro h1 { font-size: 36px; }
  .login-card { padding-right: 42px; padding-left: 42px; }
}

@media (max-width: 900px) {
  .login-page { padding: 28px 24px 24px; }
  .login-layout { grid-template-columns: 1fr; gap: 34px; min-height: auto; padding: 8vh 0 7vh; }
  .login-intro { padding: 0; }
  .login-intro h1 { font-size: clamp(36px, 8vw, 56px); }
  .intro-signal { margin-top: 34px; }
  .login-card { max-width: 540px; padding: 40px 34px 30px; }
}
@media (max-width: 520px) {
  .brand-lockup { gap: 10px; }
  .brand-logo { width: 142px; }
  .brand-divider { display: none; }
  .brand-label { font-size: 8px; letter-spacing: .13em; }
  .login-layout { padding-top: 6vh; }
  .login-card { padding: 34px 22px 26px; }
  .card-heading h2 { font-size: 27px; }
  .card-footer { align-items: flex-start; flex-direction: column; }
  .login-footer { flex-wrap: wrap; line-height: 1.7; }
  .footer-rule { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .ambient-grid, .ambient-line, .signal-dot { animation: none; }
  .submit-button { transition: none; }
}
</style>
