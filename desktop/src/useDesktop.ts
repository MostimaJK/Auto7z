import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { open } from '@tauri-apps/plugin-dialog';
import { getCurrentWebview } from '@tauri-apps/api/webview';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { connect, native, rpc, type Row, type State, type Settings } from './api';

export function useDesktop() {
  type Page = 'work' | 'logs' | 'settings';
  const page = ref<Page>('work');
  const state = ref<State>({ rows: [], busy: false, scanning: false, stopping: false, current: null, activity: '準備就緒', completed: 0, total: 0 });
  const defaults: Settings = { path_7z: '', path_rar: '', max_recursion_depth: 20, idle_timeout_seconds: 0, timeout_7z_precheck: 30, delete_after_extract: false, theme: 'system' };
  const settings = ref<Settings>({ ...defaults });
  const draft = reactive<Settings>({ ...defaults });
  const tools = reactive({ bundled_7z: '', bundled_7z_exists: false, settings_file: '' });
  const ready = ref(false);
  const working = ref(false);
  const error = ref('');
  const settingError = ref('');
  const logs = ref<string[]>([]);
  const mode = ref('extract');
  const extension = ref('.zip');
  const engineMode = ref('auto');
  const passwords = ref('');
  const filter = ref('all');
  const selected = ref<Row[]>([]);
  const detail = ref<Row | null>(null);
  const help = ref(false);
  const dragging = ref(false);
  const checkedTools = ref<Record<string, boolean> | null>(null);
  const systemDark = ref(matchMedia('(prefers-color-scheme: dark)').matches);
  const dark = computed(() => settings.value.theme === 'dark' || (settings.value.theme === 'system' && systemDark.value));
  const busy = computed(() => working.value || state.value.busy || state.value.scanning);
  const candidatePasswords = computed(() => [...new Set(passwords.value.split(/[\n,，]/).map(s => s.trim()).filter(Boolean))]);
  const statuses: Record<Row['status'], string> = { pending: '待處理', running: '處理中', success: '成功', partial: '部分完成', failed: '失敗', cancelled: '已取消' };
  const statusTypes: Record<Row['status'], 'primary' | 'success' | 'warning' | 'danger' | 'info'> = { pending: 'info', running: 'primary', success: 'success', partial: 'warning', failed: 'danger', cancelled: 'info' };
  const shown = computed(() => state.value.rows.filter(r => filter.value === 'all' || (filter.value === 'pending' ? ['pending', 'running'].includes(r.status) : !['pending', 'running'].includes(r.status))));
  const counts = computed(() => ({ success: state.value.rows.filter(r => r.status === 'success').length, partial: state.value.rows.filter(r => r.status === 'partial').length, failed: state.value.rows.filter(r => r.status === 'failed').length, cancelled: state.value.rows.filter(r => r.status === 'cancelled').length }));
  const done = computed(() => state.value.rows.filter(r => !['pending', 'running'].includes(r.status)).length);
  const retry = computed(() => state.value.rows.some(r => ['partial', 'failed', 'cancelled'].includes(r.status)));
  const canStart = computed(() => state.value.rows.some(r => r.status !== 'success'));
  const customSeven = ref('');
  const useBundled = computed({ get: () => draft.path_7z === tools.bundled_7z, set: value => {
    if (value && draft.path_7z !== tools.bundled_7z) customSeven.value = draft.path_7z;
    draft.path_7z = value ? tools.bundled_7z : customSeven.value; checkedTools.value = null;
  } });
  const dirty = computed(() => (Object.keys(defaults) as (keyof Settings)[]).some(key => draft[key] !== settings.value[key]));
  const name = (path: string) => path.split(/[\\/]/).pop() || path;
  const size = (value: number) => value < 1024 ? `${value} B` : value < 1048576 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1048576).toFixed(1)} MB`;

  watch(dark, value => {
    document.documentElement.classList.toggle('dark', value);
    if (native && ready.value) void getCurrentWindow().setTheme(value ? 'dark' : 'light').catch(e => error.value = String(e));
  }, { immediate: true });
  watch(() => [draft.path_7z, draft.path_rar], () => checkedTools.value = null);

  async function attempt(action: () => Promise<unknown>) {
    try { working.value = true; await action(); }
    catch (e) { error.value = e instanceof Error ? e.message : String(e); }
    finally { working.value = false; }
  }
  async function navigate(next: Page) {
    if (next === page.value) return;
    if (page.value === 'settings' && dirty.value) {
      try { await ElMessageBox.confirm('尚有未儲存的設定，是否捨棄？', '離開設定', { confirmButtonText: '捨棄變更', cancelButtonText: '繼續編輯', type: 'warning' }); }
      catch { return; }
    }
    if (next === 'settings') { Object.assign(draft, settings.value); customSeven.value = draft.path_7z === tools.bundled_7z ? '' : draft.path_7z; settingError.value = ''; checkedTools.value = null; }
    page.value = next;
  }
  async function pick(folder = false) {
    await attempt(async () => {
      const paths = await open({ directory: folder, multiple: true, title: folder ? '加入資料夾' : '加入文件' });
      if (paths) await rpc('add', { paths: Array.isArray(paths) ? paths : [paths], include_all: mode.value !== 'extract' });
    });
  }
  async function remove(ids: string[]) {
    await attempt(async () => { await rpc('remove', { ids }); selected.value = []; if (detail.value && ids.includes(detail.value.id)) detail.value = null; });
  }
  const reorder = (ids: string[]) => attempt(() => rpc('reorder', { ids }));
  const requeue = (ids: string[]) => attempt(() => rpc('requeue', { ids }));
  async function start() {
    await attempt(async () => { error.value = ''; extension.value = extension.value.trim(); if (extension.value && !extension.value.startsWith('.')) extension.value = '.' + extension.value; await rpc('start', { mode: mode.value, extension: extension.value, passwords: candidatePasswords.value, engine_mode: engineMode.value }); });
  }
  async function changeMode(value: string | number | boolean | undefined) {
    const next = String(value);
    if (next === mode.value) return;
    if (busy.value || !['extract', 'rename', 'restore'].includes(next)) return;
    mode.value = next; filter.value = 'all';
  }
  async function browse(key: 'path_7z' | 'path_rar') {
    await attempt(async () => {
      const path = await open({ directory: false, multiple: false, title: key === 'path_7z' ? '選擇 7-Zip 執行檔' : '選擇 WinRAR 執行檔', filters: [{ name: '執行檔', extensions: ['exe'] }] });
      if (typeof path === 'string') { draft[key] = path; if (key === 'path_7z') customSeven.value = path; }
    });
  }
  async function checkTools() { checkedTools.value = await rpc('check_tools', { path_7z: draft.path_7z.trim(), path_rar: draft.path_rar.trim() }); }
  async function saveSettings() {
    working.value = true; settingError.value = '';
    try {
      draft.path_7z = draft.path_7z.trim(); draft.path_rar = draft.path_rar.trim(); await checkTools();
      if (!checkedTools.value?.path_7z && !checkedTools.value?.path_rar) throw new Error('請至少指定一個可用的解壓執行檔。');
      if (draft.path_7z && !checkedTools.value?.path_7z) throw new Error('7-Zip 路徑不存在，請重新選擇。');
      if (draft.path_rar && !checkedTools.value?.path_rar) throw new Error('WinRAR 路徑不存在，請重新選擇。');
      const saved = await rpc<Settings>('save', { ...draft }); settings.value = saved; Object.assign(draft, saved); ElMessage.success('設定已儲存');
    } catch (e) { settingError.value = e instanceof Error ? e.message : String(e); }
    finally { working.value = false; }
  }
  function resetDraft() { Object.assign(draft, settings.value); settingError.value = ''; checkedTools.value = null; }
  async function toggleTheme() { await attempt(async () => settings.value = await rpc('save', { ...settings.value, theme: dark.value ? 'light' : 'dark' })); }
  const copyPath = (path: string) => attempt(() => navigator.clipboard.writeText(path));
  const openRow = (row: Row) => attempt(() => rpc('open', { id: row.id }));
  const openResult = () => attempt(() => rpc('open', { id: detail.value!.id }));
  const cancel = () => attempt(() => rpc('cancel'));
  const copyLogs = () => attempt(() => navigator.clipboard.writeText(logs.value.join('\n')));
  function onKey(e: KeyboardEvent) {
    if (page.value !== 'work' || detail.value || help.value || busy.value || !ready.value) return;
    if (e.ctrlKey && e.key.toLowerCase() === 'o') { e.preventDefault(); void pick(e.shiftKey); }
    if (e.ctrlKey && e.key === 'Enter' && canStart.value) { e.preventDefault(); void start(); }
  }
  const off: (() => void)[] = [];
  let disposed = false;
  onMounted(async () => {
    window.addEventListener('keydown', onKey);
    const media = matchMedia('(prefers-color-scheme: dark)');
    const change = () => systemDark.value = media.matches;
    media.addEventListener('change', change); off.push(() => media.removeEventListener('change', change));
    try {
      const disconnect = await connect((event, data) => {
        if (disposed) return;
        if (event === 'state') { state.value = data; if (detail.value) detail.value = state.value.rows.find(r => r.id === detail.value?.id) || null; }
        if (event === 'activity') state.value.activity = data;
        if (event === 'progress') state.value.progress = data;
        if (event === 'log') logs.value = [...logs.value.slice(-1999), `${new Date().toLocaleTimeString('zh-TW')}  ${data}`];
        if (event === 'error') error.value = data;
      });
      if (disposed) { disconnect(); return; } off.push(disconnect);
      if (!native) { error.value = '瀏覽器僅供版面預覽。請使用 Start_Auto7z.bat 處理本機文件。'; return; }
      const init = await rpc<{ settings: Settings; state: State; warning: string; tools: typeof tools }>('init');
      settings.value = init.settings; Object.assign(draft, init.settings); Object.assign(tools, init.tools); state.value = init.state; ready.value = true;
      await getCurrentWindow().setTheme(dark.value ? 'dark' : 'light'); if (init.warning) error.value = init.warning;
      off.push(await getCurrentWebview().onDragDropEvent(({ payload }) => {
        dragging.value = page.value === 'work' && (payload.type === 'enter' || payload.type === 'over');
        if (payload.type === 'drop') { dragging.value = false; if (page.value === 'work' && !busy.value) void attempt(() => rpc('add', { paths: payload.paths, include_all: mode.value !== 'extract' })); }
      }));
      off.push(await getCurrentWindow().onCloseRequested(async event => {
        if (state.value.busy || state.value.scanning) {
          event.preventDefault();
          try { await ElMessageBox.confirm('取消目前工作後再關閉；已成功的結果會保留。', '工作仍在進行', { confirmButtonText: '取消工作', cancelButtonText: '繼續工作' }); await rpc('cancel'); } catch { /* retain work */ }
        } else if (page.value === 'settings' && dirty.value) {
          event.preventDefault();
          try { await ElMessageBox.confirm('捨棄未儲存設定並關閉？', '關閉視窗', { confirmButtonText: '關閉', cancelButtonText: '繼續編輯' }); await getCurrentWindow().destroy(); } catch { /* retain draft */ }
        }
      }));
    } catch (e) { error.value = String(e); }
  });
  onUnmounted(() => { disposed = true; off.forEach(fn => fn()); window.removeEventListener('keydown', onKey); });
  return { page, state, settings, draft, tools, ready, working, error, settingError, logs, mode, extension, engineMode, passwords, filter, selected, detail, help, dragging, checkedTools, dark, busy, candidatePasswords, statuses, statusTypes, shown, counts, done, retry, canStart, useBundled, dirty, name, size, attempt, navigate, pick, remove, reorder, requeue, start, changeMode, browse, checkTools, saveSettings, resetDraft, toggleTheme, openResult, cancel, copyLogs, copyPath, openRow };
}
