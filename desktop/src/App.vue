<script setup lang="ts">
import zhTw from 'element-plus/es/locale/lang/zh-tw';
import type { Row } from './api';
import { useDesktop } from './useDesktop';
import ModeSwitch from './ModeSwitch.vue';
const pages = [{ value: 'work', label: '工作區' }, { value: 'logs', label: '日誌' }, { value: 'settings', label: '設定' }];
const extensions = ['.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tgz', '.tbz2', '.txz', '.zst', '.cab', '.iso', '.wim', '.001'];
function navigatePage(value: string) { if (value === 'work' || value === 'logs' || value === 'settings') void navigate(value); }
const { page, state, draft, tools, ready, working, error, settingError, logs, mode, extension, engineMode, passwords, filter, selected, detail, help, dragging, checkedTools, dark, busy, candidatePasswords, statuses, statusTypes, shown, counts, done, retry, canStart, useBundled, dirty, name, size, attempt, navigate, pick, remove, start, changeMode, browse, checkTools, saveSettings, resetDraft, toggleTheme, openResult, cancel, copyLogs } = useDesktop();
</script>

<template>
  <el-config-provider :locale="zhTw">
    <div class="app-shell" :class="{ dragging }">
      <header class="app-header">
        <div class="brand"><span class="brand-mark">A<span>7</span></span><h1>Auto7z</h1></div>
        <nav class="navigation" aria-label="主導覽">
          <ModeSwitch :model-value="page" :items="pages" label="頁面切換" compact @update:model-value="navigatePage" />
        </nav>
        <el-button class="theme-button" circle :aria-label="dark ? '切換淺色主題' : '切換深色主題'" :disabled="busy || !ready || (page === 'settings' && dirty)" @click="toggleTheme">{{ dark ? '☀' : '☾' }}</el-button>
      </header>
      <el-alert v-if="error" type="error" :title="error" show-icon @close="error = ''" />

      <main v-show="page === 'work'" class="workspace-page">
        <section class="mode-toolbar" aria-label="處理方式">
          <ModeSwitch :model-value="mode" :disabled="busy" @update:model-value="changeMode" />
          <label v-if="mode !== 'extract'" class="inline-field"><span>目標後綴</span><el-select v-model="extension" aria-label="目標後綴，可選擇或自訂" :disabled="busy" class="extension-input" filterable allow-create default-first-option :reserve-keyword="false" placeholder="選擇或輸入後綴"><el-option v-for="ext in extensions" :key="ext" :label="ext" :value="ext" /></el-select></label>
          <label v-if="mode !== 'rename'" class="inline-field engine-field"><span>解壓軟體</span><el-select v-model="engineMode" aria-label="解壓軟體" :disabled="busy"><el-option label="自動選擇" value="auto" /><el-option label="7-Zip" value="7z" /><el-option label="WinRAR" value="winrar" /></el-select></label>
        </section>

        <section class="queue-panel" aria-label="文件佇列">
          <div class="panel-heading"><h2>文件佇列 <span class="count">{{ state.rows.length }}</span></h2><span v-if="state.scanning" class="muted" role="status">正在掃描…</span><div class="spacer" />
            <template v-if="state.rows.length"><el-button :disabled="busy" @click="pick()">加入文件</el-button><el-button :disabled="busy" @click="pick(true)">資料夾</el-button></template>
          </div>
          <div v-if="state.rows.length" class="queue-tools"><el-radio-group v-model="filter" size="small" aria-label="佇列篩選"><el-radio-button value="all">全部</el-radio-button><el-radio-button value="pending">待處理</el-radio-button><el-radio-button value="results">結果</el-radio-button></el-radio-group><div class="spacer" /><el-button v-if="selected.length" text :disabled="busy" @click="remove(selected.map(r => r.id))">移除 {{ selected.length }} 項</el-button><el-button v-else text :disabled="busy" @click="remove(state.rows.map(r => r.id))">清空佇列</el-button></div>
          <div v-if="!state.rows.length" class="empty-state">
            <div class="empty-icon" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none"><path d="M7 15a4 4 0 0 1 4-4h10l4 5h12a4 4 0 0 1 4 4v15a4 4 0 0 1-4 4H11a4 4 0 0 1-4-4V15Z" stroke="currentColor" stroke-width="2"/><path d="M7 23h34" stroke="currentColor" stroke-width="2"/></svg></div>
            <div class="empty-copy"><h3>加入要處理的文件</h3><p>拖入文件或資料夾，即可加入佇列</p><div class="empty-actions"><el-button type="primary" round :disabled="busy || !ready" @click="pick()">加入文件</el-button><el-button round :disabled="busy || !ready" @click="pick(true)">選擇資料夾</el-button><el-button text @click="help = true">使用說明</el-button></div></div>
          </div>
          <div v-else class="table-region">
            <el-table :data="shown" height="100%" row-key="id" highlight-current-row @selection-change="(rows: Row[]) => selected = rows" @row-click="(row: Row) => detail = row" empty-text="此檢視尚無文件">
              <el-table-column type="selection" width="44" />
              <el-table-column label="文件" min-width="260"><template #default="{ row }"><button class="file-button" @click.stop="detail = row"><span class="file-name">{{ name(row.source) }}</span><span class="file-path">{{ row.source }}</span></button></template></el-table-column>
              <el-table-column label="大小" width="96" class-name="size-column"><template #default="{ row }">{{ size(row.size) }}</template></el-table-column>
              <el-table-column label="狀態" width="108"><template #default="{ row }"><el-tag :type="statusTypes[row.status as Row['status']]" effect="light" round>{{ statuses[row.status as Row['status']] }}</el-tag></template></el-table-column>
            </el-table>
          </div>
        </section>

        <section v-if="mode !== 'rename'" class="password-panel" aria-label="候選密碼">
          <div class="password-heading"><h2>候選密碼</h2><span class="muted">{{ candidatePasswords.length ? `${candidatePasswords.length} 組` : '每行一組，或以逗號分隔' }}</span><span class="spacer" /><span class="muted session-note">僅保留於本次工作階段</span></div>
          <el-input v-model="passwords" aria-label="候選密碼" type="textarea" :rows="2" :disabled="busy" placeholder="輸入候選密碼；留空時嘗試無密碼解壓" resize="vertical" />
        </section>

        <footer class="task-footer">
          <div class="task-status"><div class="status-title" role="status"><strong>{{ state.activity }}</strong><span v-if="state.total">本輪已處理 {{ state.completed }} / {{ state.total }}</span></div><template v-if="state.busy">
            <div class="extraction-progress" :class="{ 'is-unknown': state.progress?.percent == null }" role="progressbar" aria-label="目前壓縮包的本次解壓進度" :aria-valuenow="state.progress?.percent ?? undefined" :aria-valuemin="0" :aria-valuemax="100"><span :style="state.progress?.percent != null ? { width: `${state.progress.percent}%` } : undefined" /></div>
            <div class="progress-caption"><span>目前壓縮包：{{ state.progress?.archive || name(state.rows.find(r => r.id === state.current)?.source || '') }}</span><strong v-if="state.progress?.percent != null">7-Zip 回報 {{ state.progress.percent }}%</strong><span v-else class="muted">{{ state.progress?.tool === 'winrar' ? 'WinRAR · 進度未知' : '預檢／等待軟體進度' }}</span></div>
          </template><span v-else-if="done" class="muted">成功 {{ counts.success }} · 部分完成 {{ counts.partial }} · 失敗 {{ counts.failed }} · 取消 {{ counts.cancelled }}</span></div>
          <el-button v-if="state.busy || state.scanning" round :disabled="state.stopping || working" @click="cancel">{{ state.stopping ? '正在取消…' : '取消工作' }}</el-button>
          <el-button v-else type="primary" round :disabled="!ready || busy || !canStart" @click="start">{{ retry ? '重試未成功項目' : mode === 'rename' ? '修改後綴' : '開始解壓' }}</el-button>
        </footer>
      </main>

      <main v-show="page === 'logs'" class="logs-page page-surface">
        <div class="page-heading"><div><h2>工作日誌</h2><p>最近 2,000 筆活動與處理訊息</p></div><el-button :disabled="!logs.length" @click="copyLogs">複製日誌</el-button></div>
        <el-input class="log-view" :model-value="logs.join('\n')" type="textarea" readonly resize="none" placeholder="尚無工作日誌" aria-label="工作日誌" />
      </main>

      <main v-show="page === 'settings'" class="settings-page page-surface">
        <div class="page-heading"><h2>設定</h2><el-tag v-if="dirty" type="warning" effect="plain">尚未儲存</el-tag></div>
        <el-alert v-if="state.busy || state.scanning" type="info" title="工作進行中，完成後可儲存設定。" :closable="false" />
        <el-alert v-if="settingError" type="error" :title="settingError" show-icon @close="settingError = ''" />
        <div class="settings-scroll"><el-form label-position="top" class="settings-form" :disabled="busy || !ready">
          <section class="settings-section"><h3>解壓軟體</h3>
            <el-form-item label="7-Zip"><el-radio-group v-model="useBundled"><el-radio-button :value="true" :disabled="!tools.bundled_7z_exists">使用內置版本</el-radio-button><el-radio-button :value="false">自訂路徑</el-radio-button></el-radio-group></el-form-item>
            <el-form-item label="7-Zip 執行檔" :error="checkedTools && draft.path_7z && !checkedTools.path_7z ? '找不到此執行檔' : ''"><div class="path-row"><el-input v-model="draft.path_7z" :readonly="useBundled" aria-label="7-Zip 執行檔路徑" placeholder="選擇 7z.exe" /><el-button v-if="!useBundled" @click="browse('path_7z')">瀏覽</el-button><el-tag v-if="checkedTools?.path_7z" type="success">已找到</el-tag></div></el-form-item>
            <el-form-item label="WinRAR 執行檔（選用）" :error="checkedTools && draft.path_rar && !checkedTools.path_rar ? '找不到此執行檔' : ''"><div class="path-row"><el-input v-model="draft.path_rar" aria-label="WinRAR 執行檔路徑" placeholder="選擇自行安裝的 WinRAR.exe" clearable /><el-button @click="browse('path_rar')">瀏覽</el-button><el-tag v-if="checkedTools?.path_rar" type="success">已找到</el-tag></div></el-form-item>
            <el-button @click="attempt(checkTools)">檢查路徑</el-button><p class="field-note">可使用內置 7-Zip，或指定已安裝的版本。自動選擇只需一個可用解壓軟體。</p>
          </section>
          <section class="settings-section"><h3>處理選項</h3><div class="numeric-settings"><el-form-item label="遞迴層數上限"><el-input-number v-model="draft.max_recursion_depth" :min="1" :max="100" controls-position="right" /></el-form-item><el-form-item label="目錄預檢逾時（秒）"><el-input-number v-model="draft.timeout_7z_precheck" :min="3" :max="300" controls-position="right" /></el-form-item><el-form-item label="停滯保護（秒，0 為關閉）"><el-input-number v-model="draft.idle_timeout_seconds" :min="0" :max="86400" controls-position="right" /></el-form-item></div><el-checkbox v-model="draft.delete_after_extract">成功解壓後刪除內層壓縮包</el-checkbox><p class="field-note">最外層原包始終保留；同名結果另建目錄。</p></section>
          <section class="settings-section"><h3>外觀</h3><el-radio-group v-model="draft.theme"><el-radio-button value="system">跟隨系統</el-radio-button><el-radio-button value="light">淺色</el-radio-button><el-radio-button value="dark">深色</el-radio-button></el-radio-group></section>
        </el-form></div>
        <footer class="settings-footer"><span class="muted">套用至下一次工作</span><div class="spacer" /><el-button :disabled="busy || !dirty" @click="resetDraft">還原變更</el-button><el-button type="primary" :disabled="busy || !ready || !dirty" @click="saveSettings">儲存設定</el-button></footer>
      </main>

      <el-drawer :model-value="!!detail" title="文件詳情" size="min(440px, 94vw)" @close="detail = null">
        <template v-if="detail"><el-tag :type="statusTypes[detail.status]" round>{{ statuses[detail.status] }}</el-tag><el-form label-position="top" class="detail-form"><el-form-item label="來源"><el-input :model-value="detail.source" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.archive && detail.archive !== detail.source" label="目前原包"><el-input :model-value="detail.archive" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.output" label="結果目錄"><el-input :model-value="detail.output" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" /></el-form-item><el-form-item v-if="detail.detail" label="處理訊息"><el-input :model-value="detail.detail" type="textarea" readonly :autosize="{ minRows: 3, maxRows: 12 }" /></el-form-item></el-form></template>
        <template #footer><el-button v-if="detail" type="primary" :disabled="['pending', 'running'].includes(detail.status)" @click="openResult">{{ detail.output ? '開啟結果目錄' : '開啟來源位置' }}</el-button></template>
      </el-drawer>
      <el-dialog v-model="help" title="使用說明" width="min(520px, 92vw)"><p>加入文件或資料夾，直接選擇處理方式後開始。資料夾會遞迴掃描；分卷只加入首卷。偽裝副檔名請使用「改後綴並解壓」。目標後綴可選擇或輸入自訂值後按 Enter；修改後綴不會轉換壓縮格式。</p><p>密碼每行一組或以逗號分隔。選取文件名稱可查看完整路徑、結果和錯誤；重試略過成功項目。</p><p>Ctrl+O 加入文件 · Ctrl+Shift+O 加入資料夾 · Ctrl+Enter 開始。日誌頁可選取複製記錄；設定頁可修改解壓軟體路徑。</p><template #footer><el-button type="primary" @click="help = false">知道了</el-button></template></el-dialog>
    </div>
  </el-config-provider>
</template>
