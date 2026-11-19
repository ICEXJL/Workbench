<template>
  <div class="app-shell" :class="{ 'nav-open': mobileNavOpen }">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img src="/logo-transparent.png" alt="EnjoyOurs" />
        <div><strong>Operations</strong><span>SEA COMMAND CENTER</span></div>
      </div>
      <nav class="nav-list" aria-label="主导航">
        <p class="nav-section">跨境工作台</p>
        <button v-for="item in logisticsNav" :key="item.key" class="nav-item" :class="{ active: activeKey === item.key }" @click="go(item.key)">
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-copy"><strong>{{ item.label }}</strong><small>{{ item.caption }}</small></span>
        </button>
        <p class="nav-section">经营分析</p>
        <button v-for="item in primaryNav" :key="item.key" class="nav-item" :class="{ active: activeKey === item.key }" @click="go(item.key)">
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-copy"><strong>{{ item.label }}</strong><small>{{ item.caption }}</small></span>
        </button>
        <p class="nav-section nav-section-secondary">组织管理</p>
        <button v-for="item in secondaryNav" :key="item.key" class="nav-item" :class="{ active: activeKey === item.key }" @click="go(item.key)">
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-copy"><strong>{{ item.label }}</strong><small>{{ item.caption }}</small></span>
        </button>
      </nav>
      <div class="sidebar-status" :class="{ offline: !serviceOnline }"><span class="status-dot"></span><div><strong>{{ serviceOnline ? '数据服务正常' : '数据服务未连接' }}</strong><small>{{ serviceOnline ? '接口连接可用' : '请启动后端服务' }}</small></div></div>
    </aside>
    <button class="mobile-mask" aria-label="关闭导航" @click="mobileNavOpen = false"></button>
    <main class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <button class="mobile-menu" aria-label="打开导航" @click="mobileNavOpen = true"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" /></svg></button>
          <div><p>SEA OPERATIONS / {{ currentSection }}</p><h1>{{ route.meta.title || '运营工作台' }}</h1></div>
        </div>
        <div class="topbar-actions">
          <button class="icon-button" title="刷新页面" @click="refreshPage"><svg viewBox="0 0 24 24"><path d="M20 6v5h-5M4 18v-5h5" /><path d="M6.1 9a7 7 0 0 1 11.6-2.6L20 11M4 13l2.3 4.6A7 7 0 0 0 18 15" /></svg></button>
          <span class="action-divider"></span>
          <div class="user-menu-wrap" @click.stop>
            <button type="button" class="user-menu user-menu-trigger" aria-label="打开用户菜单" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen">
              <span class="avatar">{{ userInitial }}</span>
              <span class="user-copy"><strong>{{ authStore.realName || authStore.username || '运营人员' }}</strong><small>{{ roleLabel }} · {{ authStore.department || '跨境运营中心' }}</small></span>
              <span class="user-chevron" :class="{ open: userMenuOpen }" aria-hidden="true"></span>
            </button>
            <div v-if="userMenuOpen" class="user-dropdown-panel">
              <button type="button" class="user-dropdown-item" @click="handleUserMenuClick('profile')">个人信息</button>
              <button type="button" class="user-dropdown-item" @click="handleUserMenuClick('password')">修改密码</button>
              <div class="user-dropdown-divider"></div>
              <button type="button" class="user-dropdown-item" @click="handleUserMenuClick('logout')">退出登录</button>
            </div>
          </div>
          <button class="logout-button" title="退出登录" @click="logout"><svg viewBox="0 0 24 24"><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10" /></svg></button>
        </div>
      </header>
      <div class="content"><router-view /></div>
    </main>
    <a-modal v-model:open="profileOpen" title="个人信息" :footer="null" centered>
      <div class="profile-details">
        <div><span>姓名</span><strong>{{ authStore.realName || '-' }}</strong></div>
        <div><span>登录账号</span><strong>{{ authStore.username || '-' }}</strong></div>
        <div><span>角色</span><strong>{{ roleLabel }}</strong></div>
        <div><span>所属部门</span><strong>{{ authStore.department || '未配置' }}</strong></div>
      </div>
    </a-modal>
    <a-modal v-model:open="passwordOpen" :title="passwordRequired ? '首次登录，请修改密码' : '修改密码'" :closable="!passwordRequired" :mask-closable="!passwordRequired" :keyboard="!passwordRequired" centered @cancel="handlePasswordCancel">
      <a-alert v-if="passwordRequired" class="password-required-alert" type="warning" show-icon message="为了账号安全，请先设置新密码" description="完成修改后才能进入工作台。" />
      <a-form ref="passwordFormRef" :model="passwordForm" layout="vertical" class="password-form">
        <a-form-item label="当前密码" name="current_password" :rules="passwordRules.current_password">
          <a-input-password v-model:value="passwordForm.current_password" autocomplete="current-password" placeholder="请输入当前密码" />
        </a-form-item>
        <a-form-item label="新密码" name="new_password" :rules="passwordRules.new_password">
          <a-input-password v-model:value="passwordForm.new_password" autocomplete="new-password" placeholder="至少 8 位，且包含字母和数字" />
        </a-form-item>
        <a-form-item label="确认新密码" name="confirm_password" :rules="passwordRules.confirm_password">
          <a-input-password v-model:value="passwordForm.confirm_password" autocomplete="new-password" placeholder="请再次输入新密码" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button v-if="!passwordRequired" @click="handlePasswordCancel">取消</a-button>
        <a-button type="primary" :loading="passwordSaving" @click="submitPassword">{{ passwordRequired ? '完成并进入工作台' : '确认修改' }}</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/services/api'
const route = useRoute(); const router = useRouter(); const authStore = useAuthStore(); const mobileNavOpen = ref(false); const serviceOnline = ref(false)
const profileOpen = ref(false); const passwordOpen = ref(false); const passwordSaving = ref(false); const passwordFormRef = ref(); const userMenuOpen = ref(false)
const passwordRequired = computed(() => authStore.mustChangePassword)
const passwordForm = reactive({ current_password: '', new_password: '', confirm_password: '' })
const passwordRules = {
  current_password: [{ required: true, message: '请输入当前密码' }],
  new_password: [
    { required: true, message: '请输入新密码' },
    { min: 8, message: '新密码至少 8 位' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: '新密码必须同时包含字母和数字' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码' },
    { validator: (_, value) => value === passwordForm.new_password ? Promise.resolve() : Promise.reject(new Error('两次输入的新密码不一致')) },
  ],
}
const icon = (paths) => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`
const basePrimaryNav = [
  { key: 'daily', label: '经营总览', caption: '订单与销售明细', icon: icon('<path d="M4 13h6V4H4v9Zm10 7h6V11h-6v9ZM4 20h6v-3H4v3Zm10-13h6V4h-6v3Z"/>') },
  { key: 'personnel', label: '人员销售', caption: '团队与店铺表现', icon: icon('<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a5 5 0 0 1 10 0v2M16 4a3 3 0 0 1 0 6M16 13a5 5 0 0 1 5 5v2"/>') },
  { key: 'report-submit', label: '提交日报', caption: '每日运营数据填报', roles: ['operator','leader','manager'], icon: icon('<path d="M6 3h9l3 3v15H6z"/><path d="M9 12h6M9 16h6M14 3v4h4"/>') },
  { key: 'stats7d', label: '趋势分析', caption: '近 7 天经营趋势', roles: ['admin'], icon: icon('<path d="M4 19V5M4 19h16M7 15l4-4 3 2 5-6"/>') },
  { key: 'statsdaily', label: '分布洞察', caption: '区域与仓库结构', roles: ['admin'], icon: icon('<path d="M12 3a9 9 0 1 0 9 9h-9V3Z"/><path d="M16 3.9A9 9 0 0 1 20.1 8H16V3.9Z"/>') },
]
const logisticsNav = [
  { key: 'logistics-search', label: '物流查询', caption: '库存与出货追踪', icon: icon('<path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h5"/>') },
]
const baseSecondaryNav = [
  { key: 'report-list', label: '日报进度', caption: '团队提交与目标进度', icon: icon('<path d="M4 19V5M4 19h16M7 15l4-4 3 2 5-6"/>') },
  { key: 'report-targets', label: '月度目标', caption: '配置销售与上架目标', roles: ['admin'], icon: icon('<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"/><path d="M12 7v5l3 2"/>') },
  { key: 'manage', label: '人员目录', caption: '角色与部门信息', roles: ['admin'], icon: icon('<path d="M4 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM18 8v6M15 11h6"/>') }
]
const primaryNav = computed(() => basePrimaryNav.filter(item => !item.roles || item.roles.includes(authStore.role)))
const secondaryNav = computed(() => baseSecondaryNav.filter(item => !item.roles || item.roles.includes(authStore.role)))
const activeKey = computed(() => route.name || 'daily')
const userInitial = computed(() => (authStore.realName || authStore.username || 'O').slice(0, 1).toUpperCase())
const roleLabel = computed(() => ({admin:'管理端',manager:'主管',leader:'组长',operator:'运营'}[authStore.role] || '运营'))
const ORGANIZATION_PAGES = new Set(['manage', 'report-targets', 'report-list'])
const currentSection = computed(() => activeKey.value === 'logistics-search' ? 'CROSS-BORDER' : (ORGANIZATION_PAGES.has(activeKey.value) ? 'ORGANIZATION' : 'ANALYTICS'))
function go(key) { mobileNavOpen.value = false; router.push({ name: key }) }
function refreshPage() { window.location.reload() }
function logout() { authStore.logout(); router.push('/login') }
function closeUserMenu() { userMenuOpen.value = false }
function handleUserMenuClick(key) {
  closeUserMenu()
  if (key === 'profile') profileOpen.value = true
  if (key === 'password') {
    resetPasswordForm()
    passwordOpen.value = true
  }
  if (key === 'logout') logout()
}
function handlePasswordCancel() {
  if (passwordRequired.value) return
  passwordOpen.value = false
  resetPasswordForm()
}
function resetPasswordForm() {
  passwordForm.current_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate?.()
}
async function submitPassword() {
  try {
    await passwordFormRef.value?.validate()
    passwordSaving.value = true
    const response = await changePassword({ ...passwordForm })
    authStore.completePasswordChange(response?.access_token)
    message.success('密码修改成功')
    passwordOpen.value = false
    resetPasswordForm()
  } catch (error) {
    if (error?.errorFields) return
  } finally {
    passwordSaving.value = false
  }
}
onMounted(async()=>{document.addEventListener('click',closeUserMenu);if(passwordRequired.value){resetPasswordForm();passwordOpen.value=true}try{const response=await fetch('/health');serviceOnline.value=response.ok}catch{serviceOnline.value=false}})
onBeforeUnmount(()=>document.removeEventListener('click',closeUserMenu))
</script>

<style scoped>
.app-shell { --blue:#2f7df4;--blue-strong:#1767df;--blue-soft:#eaf3ff;--ink:#17243f;--muted:#71809d;--line:#dce5f2;display:flex;min-height:100vh;color:var(--ink);background:#f5f8fc }
.password-required-alert { margin-bottom: 18px; }
.sidebar{position:fixed;inset:0 auto 0 0;z-index:40;display:flex;width:250px;flex-direction:column;border-right:1px solid var(--line);background:#fff}.sidebar-brand{display:flex;align-items:center;gap:12px;height:82px;padding:0 22px;border-bottom:1px solid #edf1f7}.sidebar-brand img{width:104px}.sidebar-brand div{display:flex;min-width:0;flex-direction:column;gap:2px;padding-left:12px;border-left:1px solid var(--line)}.sidebar-brand strong{font-size:13px;line-height:1.2}.sidebar-brand span{overflow:hidden;color:#91a0b8;font-size:8px;letter-spacing:.12em;white-space:nowrap}
.nav-list{flex:1;padding:22px 13px;overflow-y:auto}.nav-section{margin:0 10px 10px;color:#9aa8be;font-size:10px;font-weight:700;letter-spacing:.16em}.nav-section-secondary{margin-top:26px}.nav-item{display:flex;width:100%;min-height:54px;align-items:center;gap:12px;margin:3px 0;padding:8px 11px;border:1px solid transparent;border-radius:7px;color:#52627e;background:transparent;text-align:left;cursor:pointer;transition:.18s ease}.nav-item:hover{color:var(--blue-strong);background:#f4f8ff}.nav-item.active{border-color:#dbe9ff;color:var(--blue-strong);background:var(--blue-soft)}.nav-icon{display:grid;width:30px;height:30px;flex:0 0 30px;place-items:center;border-radius:6px;color:#7a8aa6;background:#f3f6fa}.nav-item.active .nav-icon{color:#fff;background:var(--blue)}.nav-icon :deep(svg),.topbar svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.7}.nav-copy{display:flex;min-width:0;flex:1;flex-direction:column;gap:1px}.nav-copy strong{font-size:13px;font-weight:600}.nav-copy small{color:#98a5b9;font-size:10px}
.sidebar-status{display:flex;align-items:center;gap:10px;margin:14px;padding:13px;border:1px solid #e5edf7;border-radius:7px;background:#f8fbff}.status-dot{width:8px;height:8px;border-radius:50%;background:#25b67a;box-shadow:0 0 0 4px #e4f7ef}.sidebar-status.offline .status-dot{background:#e39a3b;box-shadow:0 0 0 4px #fff1dc}.sidebar-status div{display:flex;flex-direction:column}.sidebar-status strong{font-size:11px}.sidebar-status small{color:#8e9db4;font-size:9px}.workspace{min-width:0;flex:1;margin-left:250px}
.topbar{position:sticky;top:0;z-index:30;display:flex;height:82px;align-items:center;justify-content:space-between;gap:24px;padding:0 30px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.95);backdrop-filter:blur(14px)}.topbar-title{display:flex;align-items:center;gap:14px}.topbar-title p{margin:0 0 3px;color:var(--blue);font-size:9px;font-weight:700;letter-spacing:.16em}.topbar-title h1{margin:0;font-size:20px;font-weight:650}.topbar-actions{display:flex;align-items:center;gap:13px}.action-divider{width:1px;height:28px;background:var(--line)}
.icon-button,.logout-button,.mobile-menu{display:grid;width:36px;height:36px;place-items:center;border:1px solid var(--line);border-radius:6px;color:#6d7c96;background:#fff;cursor:pointer}.icon-button:hover,.logout-button:hover{color:var(--blue);border-color:#bfd6fb;background:#f5f9ff}.user-menu-wrap{position:relative;z-index:51}.user-menu{display:flex;align-items:center;gap:10px}.user-menu-trigger{padding:0;border:0;color:var(--ink);background:transparent;text-align:left;cursor:pointer;box-shadow:none;transition:color .18s ease}.user-menu-trigger:hover{color:var(--blue);background:transparent;box-shadow:none}.user-menu-trigger:focus-visible{outline:2px solid #bfd6fb;outline-offset:3px}.avatar{display:grid;width:36px;height:36px;place-items:center;border-radius:50%;color:#fff;background:var(--blue);font-size:13px;font-weight:700}.user-copy{display:flex;flex-direction:column}.user-menu strong{font-size:12px}.user-menu small{color:#8d9ab0;font-size:9px}.user-chevron{width:7px;height:7px;margin-left:2px;border-right:1.5px solid #7887a0;border-bottom:1.5px solid #7887a0;transform:rotate(45deg) translateY(-2px);transition:transform .18s ease}.user-chevron.open{transform:rotate(225deg) translate(-1px,-1px)}.user-dropdown-panel{position:absolute;top:calc(100% + 10px);right:0;min-width:164px;padding:6px;border:1px solid #dce5f2;border-radius:8px;background:#fff;box-shadow:none}.user-dropdown-panel::before{position:absolute;top:-6px;right:22px;width:10px;height:10px;border-top:1px solid #dce5f2;border-left:1px solid #dce5f2;background:#fff;content:'';transform:rotate(45deg)}.user-dropdown-item{display:block;width:100%;margin:2px 0;padding:10px;border:0;border-radius:5px;color:#52627e;background:transparent;font:inherit;font-size:13px;text-align:left;cursor:pointer}.user-dropdown-item:hover{color:#1767df;background:#eef5ff}.user-dropdown-divider{height:1px;margin:5px 0;background:#edf2f8}.profile-details{display:grid;gap:0;margin:2px 0 6px;border:1px solid #e5edf7;border-radius:8px;overflow:hidden}.profile-details div{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;border-bottom:1px solid #edf2f8}.profile-details div:last-child{border-bottom:0}.profile-details span{color:#7c8ba4;font-size:13px}.profile-details strong{color:var(--ink);font-size:13px;font-weight:600}.password-form{padding-top:6px}.content{min-height:calc(100vh - 82px);padding:26px 30px 44px}.mobile-menu,.mobile-mask{display:none}
@media(max-width:900px){.sidebar{transform:translateX(-100%);transition:transform .22s}.nav-open .sidebar{transform:translateX(0)}.workspace{margin-left:0}.mobile-menu{display:grid}.mobile-mask{position:fixed;inset:0;z-index:35;border:0;background:rgba(18,35,65,.34)}.nav-open .mobile-mask{display:block}.topbar{padding:0 18px}.content{padding:20px 18px 36px}}
@media(max-width:560px){.topbar{height:72px}.topbar-title p{display:none}.topbar-title h1{max-width:170px;overflow:hidden;font-size:17px;text-overflow:ellipsis;white-space:nowrap}.user-copy,.user-chevron,.action-divider,.icon-button{display:none}.content{min-height:calc(100vh - 72px);padding:16px 12px 30px}}
</style>
