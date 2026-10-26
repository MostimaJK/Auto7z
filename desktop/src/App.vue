<script setup lang="ts">
import { t, uiLanguage } from './i18n';
import { computed } from 'vue';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import en from 'element-plus/es/locale/lang/en';
import zhTw from 'element-plus/es/locale/lang/zh-tw';
const elementLocale = computed(() => ({ 'zh-TW': zhTw, 'zh-CN': zhCn, en })[uiLanguage.value]);
import QueueList from './QueueList.vue';
import { useDesktop } from './useDesktop';
import ModeSwitch from './ModeSwitch.vue';
const pages = computed(() => [{ value: 'work', label: t('工作區') }, { value: 'logs', label: t('日誌') }, { value: 'settings', label: t('設定') }]);
const filters = computed(() => [{ value: 'all', label: t('全部') }, { value: 'pending', label: t('待處理') }, { value: 'results', label: t('結果') }]);
const themes = computed(() => [{ value: 'system', label: t('跟隨系統') }, { value: 'light', label: t('淺色') }, { value: 'dark', label: t('深色') }]);
const extensions = ['.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tgz', '.tbz2', '.txz', '.zst', '.cab', '.iso', '.wim', '.001'];
function navigatePage(value: string) { if (value === 'work' || value === 'logs' || value === 'settings') void navigate(value); }
const { page, state, draft, tools, ready, working, error, settingError, logs, mode, extension, engineMode, passwords, filter, selected, detail, help, dragging, checkedTools, dark, busy, candidatePasswords, statuses, statusTypes, shown, counts, done, retry, canStart, useBundled, dirty, name, size, attempt, navigate, pick, remove, reorder, requeue, start, changeMode, browse, checkTools, saveSettings, resetDraft, toggleTheme, openResult, openLatest, cancel, copyLogs, copyPath, openRow } = useDesktop();
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <div class="app-shell" :class="{ dragging }">
      <header class="app-header">
        <div class="brand"><span class="brand-mark">A<span>7</span></span><h1>Auto7z</h1></div>
        <nav class="navigation" :aria-label="t('主導覽')">
          <ModeSwitch :model-value="page" :items="pages" :label="t('頁面切換')" compact @update:model-value="navigatePage" />
        </nav>
        <el-button class="theme-button" circle :aria-label="dark ? t('切換淺色主題') : t('切換深色主題')" :disabled="busy || !ready || (page === 'settings' && dirty)" @click="toggleTheme">{{ dark ? '☀' : '☾' }}</el-button>
      </header>
      <el-alert v-if="error" type="error" :title="error" show-icon @close="error = ''" />

      <main v-show="page === 'work'" class="workspace-page">
        <section class="mode-toolbar" :aria-label="t('處理方式')">
          <ModeSwitch :model-value="mode" :disabled="busy" @update:model-value="changeMode" />
          <label v-if="mode !== 'extract'" class="inline-field"><span>{{ t('目標後綴') }}</span><el-select v-model="extension" :aria-label="t('目標後綴，可選擇或自訂')" :disabled="busy" class="extension-input" filterable allow-create default-first-option :reserve-keyword="false" :placeholder="t('選擇或輸入後綴')"><el-option v-for="ext in extensions" :key="ext" :label="ext" :value="ext" /></el-select></label>
          <label v-if="mode !== 'rename'" class="inline-field engine-field"><span>{{ t('解壓軟體') }}</span><el-select v-model="engineMode" :aria-label="t('解壓軟體')" :disabled="busy"><el-option :label="t('自動選擇')" value="auto" /><el-option label="7-Zip" value="7z" /><el-option label="WinRAR" value="winrar" /></el-select></label>
        </section>

        <section class="queue-panel" :aria-label="t('文件佇列')">
          <div class="panel-heading"><h2>{{ t('文件佇列') }}<span class="count">{{ state.rows.length }}</span></h2><span v-if="state.scanning" class="muted" role="status">{{ t('正在掃描…') }}</span><div class="spacer" />
            <el-button text circle :title="t('清空列表（保留磁碟文件）')" :aria-label="t('清空列表')" :disabled="busy || !state.rows.length" @click="remove(state.rows.map(r => r.id))"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 10v7M14 10v7" stroke-linecap="round" stroke-linejoin="round" /></svg></el-button>
            <template v-if="state.rows.length"><el-button :disabled="busy" @click="pick()">{{ t('加入文件') }}</el-button><el-button :disabled="busy" @click="pick(true)">{{ t('資料夾') }}</el-button></template>
          </div>
          <div v-if="state.rows.length" class="queue-tools"><ModeSwitch v-model="filter" :items="filters" :label="t('佇列篩選')" compact /><div class="spacer" /><el-button v-if="selected.length" text :disabled="busy" @click="remove(selected.map(r => r.id))">{{ t('選取數量', { count: selected.length }) }}</el-button></div>
          <div v-if="!state.rows.length" class="empty-state">
            <div class="empty-icon" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none"><path d="M7 15a4 4 0 0 1 4-4h10l4 5h12a4 4 0 0 1 4 4v15a4 4 0 0 1-4 4H11a4 4 0 0 1-4-4V15Z" stroke="currentColor" stroke-width="2"/><path d="M7 23h34" stroke="currentColor" stroke-width="2"/></svg></div>
            <div class="empty-copy"><h3>{{ t('加入要處理的文件') }}</h3><p>{{ t('拖入文件或資料夾，即可加入佇列') }}</p><div class="empty-actions"><el-button type="primary" round :disabled="busy || !ready" @click="pick()">{{ t('加入文件') }}</el-button><el-button round :disabled="busy || !ready" @click="pick(true)">{{ t('選擇資料夾') }}</el-button><el-button text @click="help = true">{{ t('使用說明') }}</el-button></div></div>
          </div>
          <QueueList v-else :rows="state.rows" :shown="shown" :selected="selected" :busy="busy" :active="page === 'work'" :statuses="statuses" :status-types="statusTypes" :name="name" :size="size" @select="selected = $event" @detail="detail = $event" @remove="remove" @reorder="reorder" @requeue="requeue" @copy="copyPath" @open="openRow" />
        </section>

        <section v-if="mode !== 'rename'" class="password-panel" :aria-label="t('候選密碼')">
          <div class="password-heading"><h2>{{ t('候選密碼') }}</h2><span class="muted">{{ candidatePasswords.length ? t('密碼數量', { count: candidatePasswords.length }) : t('每行一組，或以逗號分隔') }}</span><span class="spacer" /><span class="muted session-note">{{ t('僅保留於本次工作階段') }}</span></div>
          <el-input v-model="passwords" :aria-label="t('候選密碼')" type="textarea" :rows="2" :disabled="busy" :placeholder="t('輸入候選密碼；留空時嘗試無密碼解壓')" resize="vertical" />
        </section>

        <footer class="task-footer">
          <div class="task-status"><div class="status-title" role="status"><strong>{{ t(state.activity) }}</strong><span v-if="state.total">{{ t('已處理數量', { done: state.completed, total: state.total }) }}</span></div><template v-if="state.busy">
            <div class="extraction-progress" :class="{ 'is-unknown': state.progress?.percent == null }" role="progressbar" :aria-label="t('目前壓縮包的本次解壓進度')" :aria-valuenow="state.progress?.percent ?? undefined" :aria-valuemin="0" :aria-valuemax="100"><span :style="state.progress?.percent != null ? { width: `${state.progress.percent}%` } : undefined" /></div>
            <div class="progress-caption"><span>{{ t('目前壓縮包', { name: state.progress?.archive || name(state.rows.find(r => r.id === state.current)?.source || '') }) }}</span><strong v-if="state.progress?.percent != null">{{ t('軟體進度', { percent: state.progress.percent }) }}</strong><span v-else class="muted">{{ state.progress?.tool === 'winrar' ? t('WinRAR · 進度未知') : t('預檢／等待軟體進度') }}</span></div>
          </template><span v-else-if="done" class="muted">{{ t('結果統計', counts) }}</span></div>
          <el-button round :disabled="!ready || working || !state.latest_output" :title="state.latest_output ? t('最近結果', { path: state.latest_output }) : t('解壓成功後可開啟結果資料夾')" @click="openLatest">{{ t('開啟資料夾') }}</el-button>
          <el-button v-if="state.busy || state.scanning" round :disabled="state.stopping || working" @click="cancel">{{ state.stopping ? t('正在取消…') : t('取消工作') }}</el-button>
          <el-button v-else type="primary" round :disabled="!ready || busy || !canStart" @click="start">{{ retry ? t('重試未成功項目') : mode === 'rename' ? t('修改後綴') : t('開始解壓') }}</el-button>
        </footer>
      </main>

      <main v-show="page === 'logs'" class="logs-page page-surface">
        <div class="page-heading"><div><h2>{{ t('工作日誌') }}</h2><p>{{ t('最近 2,000 筆活動與處理訊息') }}</p></div><el-button :disabled="!logs.length" @click="copyLogs">{{ t('複製日誌') }}</el-button></div>
        <el-input class="log-view" :model-value="logs.join('\n')" type="textarea" readonly resize="none" :placeholder="t('尚無工作日誌')" :aria-label="t('工作日誌')" />
      </main>

      <main v-show="page === 'settings'" class="settings-page page-surface">
        <div class="page-heading"><h2>{{ t('設定') }}</h2><el-tag v-if="dirty" type="warning" effect="plain">{{ t('尚未儲存') }}</el-tag></div>
        <el-alert v-if="state.busy || state.scanning" type="info" :title="t('工作進行中，完成後可儲存設定。')" :closable="false" />
        <el-alert v-if="settingError" type="error" :title="settingError" show-icon @close="settingError = ''" />
        <div class="settings-scroll"><el-form label-position="top" class="settings-form" :disabled="busy || !ready">
          <section class="settings-section"><h3>{{ t('解壓軟體') }}</h3>
            <el-form-item label="7-Zip"><ModeSwitch :model-value="useBundled ? 'bundled' : 'custom'" :items="[{ value: 'bundled', label: t('使用內置版本'), disabled: !tools.bundled_7z_exists }, { value: 'custom', label: t('自訂路徑') }]" :disabled="busy || !ready" :label="t('7-Zip 來源')" @update:model-value="useBundled = $event === 'bundled'" /></el-form-item>
            <el-form-item :label="t('7-Zip 執行檔')" :error="checkedTools && draft.path_7z && !checkedTools.path_7z ? t('找不到此執行檔') : ''"><div class="path-row"><el-input v-model="draft.path_7z" :readonly="useBundled" :aria-label="t('7-Zip 執行檔路徑')" :placeholder="t('選擇 7z.exe')" /><el-button v-if="!useBundled" @click="browse('path_7z')">{{ t('瀏覽') }}</el-button><el-tag v-if="checkedTools?.path_7z" type="success">{{ t('已找到') }}</el-tag></div></el-form-item>
            <el-form-item :label="t('WinRAR 執行檔（選用）')" :error="checkedTools && draft.path_rar && !checkedTools.path_rar ? t('找不到此執行檔') : ''"><div class="path-row"><el-input v-model="draft.path_rar" :aria-label="t('WinRAR 執行檔路徑')" :placeholder="t('選擇自行安裝的 WinRAR.exe')" clearable /><el-button @click="browse('path_rar')">{{ t('瀏覽') }}</el-button><el-tag v-if="checkedTools?.path_rar" type="success">{{ t('已找到') }}</el-tag></div></el-form-item>
            <el-button @click="attempt(checkTools)">{{ t('檢查路徑') }}</el-button><p class="field-note">{{ t('可使用內置 7-Zip，或指定已安裝的版本。自動選擇只需一個可用解壓軟體。') }}</p>
          </section>
          <section class="settings-section"><h3>{{ t('處理選項') }}</h3><div class="numeric-settings"><el-form-item :label="t('遞迴層數上限')"><el-input-number v-model="draft.max_recursion_depth" :min="1" :max="100" controls-position="right" /></el-form-item><el-form-item :label="t('目錄預檢逾時（秒）')"><el-input-number v-model="draft.timeout_7z_precheck" :min="3" :max="300" controls-position="right" /></el-form-item><el-form-item :label="t('停滯保護（秒，0 為關閉）')"><el-input-number v-model="draft.idle_timeout_seconds" :min="0" :max="86400" controls-position="right" /></el-form-item></div></section>
          <section class="settings-section cleanup-settings"><h3>{{ t('壓縮文件清理') }}</h3><el-checkbox v-model="draft.delete_after_extract">{{ t('刪除已成功解壓的內層壓縮文件') }}</el-checkbox><p class="field-note">{{ t('僅清理解壓目錄內已成功處理的壓縮文件，不刪除失敗項或其他文件。') }}</p><el-checkbox v-model="draft.delete_source_archive">{{ t('刪除原始壓縮包') }}</el-checkbox><p class="field-note">{{ t('完整解壓成功後永久刪除來源壓縮包及已識別分卷。失敗、部分完成或取消時保留來源；預設關閉。') }}</p></section>
          <section class="settings-section"><h3>{{ t('語言 / Language') }}</h3><el-select v-model="draft.language" :aria-label="t('語言 / Language')" style="max-width: 280px"><el-option label="中文简体" value="zh-CN" /><el-option label="中文繁體" value="zh-TW" /><el-option label="English" value="en" /></el-select></section>
          <section class="settings-section"><h3>{{ t('外觀') }}</h3><ModeSwitch v-model="draft.theme" :items="themes" :disabled="busy || !ready" :label="t('外觀主題')" /></section>
        </el-form></div>
        <footer class="settings-footer"><span class="muted">{{ t('套用至下一次工作') }}</span><div class="spacer" /><el-button :disabled="busy || !dirty" @click="resetDraft">{{ t('還原變更') }}</el-button><el-button type="primary" :disabled="busy || !ready || !dirty" @click="saveSettings">{{ t('儲存設定') }}</el-button></footer>
      </main>

      <el-drawer :model-value="!!detail" :title="t('文件詳情')" size="min(440px, 94vw)" @close="detail = null">
        <template v-if="detail"><el-tag :type="statusTypes[detail.status]" round>{{ statuses[detail.status] }}</el-tag><el-form label-position="top" class="detail-form"><el-form-item :label="t('來源')"><el-input :model-value="detail.source" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.archive && detail.archive !== detail.source" :label="t('目前原包')"><el-input :model-value="detail.archive" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.output" :label="t('結果目錄')"><el-input :model-value="detail.output" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.detail" :label="t('處理訊息')"><el-input :model-value="detail.detail" type="textarea" readonly :autosize="{ minRows: 3, maxRows: 12 }" /></el-form-item></el-form></template>
        <template #footer><el-button v-if="detail" type="primary" :disabled="['pending', 'running'].includes(detail.status)" @click="openResult">{{ detail.output ? t('開啟結果目錄') : t('開啟來源位置') }}</el-button></template>
      </el-drawer>
      <el-dialog v-model="help" :title="t('使用說明')" width="min(520px, 92vw)"><p>{{ t('helpModes') }}</p><p>{{ t('helpQueue') }}</p><p>{{ t('helpKeys') }}</p><template #footer><el-button type="primary" @click="help = false">{{ t('知道了') }}</el-button></template></el-dialog>
    </div>
  </el-config-provider>
</template>
