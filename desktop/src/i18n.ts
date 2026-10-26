import { ref } from 'vue';
export type Language = 'zh-CN' | 'zh-TW' | 'en';
export const uiLanguage = ref<Language>('zh-TW');
// Traditional Chinese is the source locale. Paths, filenames and raw tool diagnostics are never converted.
const messages: Record<string, readonly [string, string]> = {
  '工作區': ['工作区', 'Workspace'], '日誌': ['日志', 'Logs'], '設定': ['设置', 'Settings'],
  '主導覽': ['主导航', 'Main navigation'], '頁面切換': ['页面切换', 'Pages'],
  '切換淺色主題': ['切换浅色主题', 'Switch to light theme'], '切換深色主題': ['切换深色主题', 'Switch to dark theme'],
  '處理方式': ['处理方式', 'Processing mode'], '遞迴解壓': ['递归解压', 'Extract recursively'],
  '修改後綴': ['修改后缀', 'Rename extension'], '修改後綴並解壓': ['修改后缀并解压', 'Rename and extract'],
  '目標後綴': ['目标后缀', 'Target extension'], '目標後綴，可選擇或自訂': ['目标后缀，可选择或自定义', 'Target extension, choose or enter'],
  '選擇或輸入後綴': ['选择或输入后缀', 'Choose or enter extension'], '解壓軟體': ['解压软件', 'Extraction software'],
  '自動選擇': ['自动选择', 'Automatic'], '文件佇列': ['文件队列', 'File queue'],
  '清空列表（保留磁碟文件）': ['清空列表（保留磁盘文件）', 'Clear list (keep files on disk)'],
  '清空列表': ['清空列表', 'Clear list'], '正在掃描…': ['正在扫描…', 'Scanning…'],
  '加入文件': ['添加文件', 'Add files'], '資料夾': ['文件夹', 'Folder'], '全部': ['全部', 'All'],
  '待處理': ['待处理', 'Pending'], '結果': ['结果', 'Results'], '佇列篩選': ['队列筛选', 'Queue filter'],
  '加入要處理的文件': ['添加要处理的文件', 'Add files to process'],
  '拖入文件或資料夾，即可加入佇列': ['拖入文件或文件夹，即可加入队列', 'Drop files or folders to add them to the queue'],
  '選擇資料夾': ['选择文件夹', 'Choose folder'], '使用說明': ['使用说明', 'Help'],
  '候選密碼': ['候选密码', 'Password candidates'], '每行一組，或以逗號分隔': ['每行一组，或以逗号分隔', 'One per line, or separated by commas'],
  '僅保留於本次工作階段': ['仅保留于本次会话', 'This session only'],
  '輸入候選密碼；留空時嘗試無密碼解壓': ['输入候选密码；留空时尝试无密码解压', 'Enter passwords; leave empty to try without a password'],
  '目前壓縮包的本次解壓進度': ['当前压缩包本次解压进度', 'Current archive extraction progress'],
  'WinRAR · 進度未知': ['WinRAR · 进度未知', 'WinRAR · progress unknown'],
  '預檢／等待軟體進度': ['预检／等待软件进度', 'Checking / waiting for progress'],
  '開啟資料夾': ['打开文件夹', 'Open folder'], '解壓成功後可開啟結果資料夾': ['解压成功后可打开结果文件夹', 'Available after successful extraction'],
  '正在取消…': ['正在取消…', 'Cancelling…'], '取消工作': ['取消任务', 'Cancel task'],
  '重試未成功項目': ['重试未成功项', 'Retry unfinished'], '開始解壓': ['开始解压', 'Start extraction'],
  '工作日誌': ['任务日志', 'Task logs'], '最近 2,000 筆活動與處理訊息': ['最近 2,000 条活动与处理消息', 'Latest 2,000 activity and processing messages'],
  '複製日誌': ['复制日志', 'Copy logs'], '尚無工作日誌': ['暂无任务日志', 'No logs yet'],
  '尚未儲存': ['尚未保存', 'Unsaved'], '工作進行中，完成後可儲存設定。': ['任务进行中，完成后可保存设置。', 'Settings can be saved when the task finishes.'],
  '使用內置版本': ['使用内置版本', 'Bundled version'], '自訂路徑': ['自定义路径', 'Custom path'],
  '7-Zip 來源': ['7-Zip 来源', '7-Zip source'], '7-Zip 執行檔': ['7-Zip 可执行文件', '7-Zip executable'],
  '找不到此執行檔': ['找不到此可执行文件', 'Executable not found'], '7-Zip 執行檔路徑': ['7-Zip 可执行文件路径', '7-Zip executable path'],
  '選擇 7z.exe': ['选择 7z.exe', 'Choose 7z.exe'], '瀏覽': ['浏览', 'Browse'], '已找到': ['已找到', 'Found'],
  'WinRAR 執行檔（選用）': ['WinRAR 可执行文件（可选）', 'WinRAR executable (optional)'],
  'WinRAR 執行檔路徑': ['WinRAR 可执行文件路径', 'WinRAR executable path'],
  '選擇自行安裝的 WinRAR.exe': ['选择自行安装的 WinRAR.exe', 'Choose your installed WinRAR.exe'],
  '檢查路徑': ['检查路径', 'Check paths'],
  '可使用內置 7-Zip，或指定已安裝的版本。自動選擇只需一個可用解壓軟體。': ['可使用内置 7-Zip，或指定已安装的版本。自动选择只需一个可用解压软件。', 'Use bundled 7-Zip or an installed version. Automatic mode needs one available extraction tool.'],
  '處理選項': ['处理选项', 'Processing'], '遞迴層數上限': ['递归层数上限', 'Maximum nesting depth'],
  '目錄預檢逾時（秒）': ['目录预检超时（秒）', 'Precheck timeout (seconds)'],
  '停滯保護（秒，0 為關閉）': ['停滞保护（秒，0 为关闭）', 'Idle timeout (seconds, 0 disables)'],
  '壓縮文件清理': ['压缩文件清理', 'Archive cleanup'],
  '刪除已成功解壓的內層壓縮文件': ['删除已成功解压的内层压缩文件', 'Delete successfully extracted nested archives'],
  '僅清理解壓目錄內已成功處理的壓縮文件，不刪除失敗項或其他文件。': ['仅清理解压目录内已成功处理的压缩文件，不删除失败项或其他文件。', 'Remove processed archives inside the output folder. Keep failed archives and other files.'],
  '刪除原始壓縮包': ['删除原始压缩包', 'Delete source archives'],
  '完整解壓成功後永久刪除來源壓縮包及已識別分卷。失敗、部分完成或取消時保留來源；預設關閉。': ['完整解压成功后永久删除来源压缩包及已识别分卷。失败、部分完成或取消时保留来源；默认关闭。', 'Permanently delete source archives and recognized volumes only after full success. Keep sources on failure, partial completion or cancellation. Off by default.'],
  '語言 / Language': ['语言 / Language', 'Language'], '外觀': ['外观', 'Appearance'],
  '外觀主題': ['外观主题', 'Theme'], '跟隨系統': ['跟随系统', 'System'], '淺色': ['浅色', 'Light'], '深色': ['深色', 'Dark'],
  '套用至下一次工作': ['应用于下一次任务', 'Applies to the next task'], '還原變更': ['还原更改', 'Discard changes'], '儲存設定': ['保存设置', 'Save settings'],
  '文件詳情': ['文件详情', 'File details'], '來源': ['来源', 'Source'], '目前原包': ['当前原包', 'Current archive'],
  '結果目錄': ['结果目录', 'Output folder'], '處理訊息': ['处理消息', 'Details'],
  '開啟結果目錄': ['打开结果目录', 'Open output folder'], '開啟來源位置': ['打开来源位置', 'Open source folder'], '知道了': ['知道了', 'Got it'],
  '成功': ['成功', 'Succeeded'], '部分完成': ['部分完成', 'Partial'], '失敗': ['失败', 'Failed'], '已取消': ['已取消', 'Cancelled'], '處理中': ['处理中', 'Running'],
  '離開設定': ['离开设置', 'Leave settings'], '尚有未儲存的設定，是否捨棄？': ['有未保存的设置，是否放弃？', 'Discard unsaved settings?'],
  '捨棄變更': ['放弃更改', 'Discard'], '繼續編輯': ['继续编辑', 'Keep editing'], '加入資料夾': ['添加文件夹', 'Add folders'],
  '執行檔': ['可执行文件', 'Executable'], '選擇 7-Zip 執行檔': ['选择 7-Zip 可执行文件', 'Choose 7-Zip executable'],
  '選擇 WinRAR 執行檔': ['选择 WinRAR 可执行文件', 'Choose WinRAR executable'],
  '請至少指定一個可用的解壓執行檔。': ['请至少指定一个可用的解压可执行文件。', 'Choose at least one available extraction executable.'],
  '7-Zip 路徑不存在，請重新選擇。': ['7-Zip 路径不存在，请重新选择。', '7-Zip path does not exist. Choose it again.'],
  'WinRAR 路徑不存在，請重新選擇。': ['WinRAR 路径不存在，请重新选择。', 'WinRAR path does not exist. Choose it again.'],
  '設定已儲存': ['设置已保存', 'Settings saved'], '工作仍在進行': ['任务仍在进行', 'Task in progress'],
  '取消目前工作後再關閉；已成功的結果會保留。': ['取消当前任务后再关闭；已成功的结果会保留。', 'Cancel the current task before closing. Successful results will be kept.'],
  '繼續工作': ['继续任务', 'Keep working'], '捨棄未儲存設定並關閉？': ['放弃未保存的设置并关闭？', 'Discard unsaved settings and close?'],
  '關閉視窗': ['关闭窗口', 'Close window'], '關閉': ['关闭', 'Close'],
  '瀏覽器僅供版面預覽。請使用 Start_Auto7z.bat 處理本機文件。': ['浏览器仅供界面预览。请使用 Start_Auto7z.bat 处理本机文件。', 'Browser layout preview only. Use Start_Auto7z.bat to process local files.'],
  '文件': ['文件', 'File'], '大小': ['大小', 'Size'], '狀態': ['状态', 'Status'],
  '此檢視尚無文件': ['此视图暂无文件', 'No files in this view'], '文件操作': ['文件操作', 'File actions'],
  '查看詳情': ['查看详情', 'View details'], '複製文件路徑': ['复制文件路径', 'Copy file path'],
  '上移': ['上移', 'Move up'], '下移': ['下移', 'Move down'], '重新加入待處理': ['重新加入待处理', 'Queue again'],
  '從佇列移除': ['从队列移除', 'Remove from queue'],
  '拖動排序；Alt+↑／↓ 移動，Shift+F10 開啟選單': ['拖动排序；Alt+↑／↓ 移动，Shift+F10 打开菜单', 'Drag to reorder; Alt+Up/Down to move; Shift+F10 for menu'],
  '準備就緒': ['准备就绪', 'Ready'], '處理完成': ['处理完成', 'Completed'],
  '正在掃描文件…': ['正在扫描文件…', 'Scanning files…'], '已取消；成功結果保留': ['已取消；成功结果保留', 'Cancelled; successful results kept'],
  '掃描已取消；已加入文件保留': ['扫描已取消；已添加文件保留', 'Scan cancelled; added files kept'],
  '正在取消，等待解壓進程退出…': ['正在取消，等待解压进程退出…', 'Cancelling; waiting for extraction process…'],
  '密碼數量': ['{count} 组', '{count} passwords'], '已處理數量': ['本轮已处理 {done} / {total}', 'Processed {done} / {total}'],
  '目前壓縮包': ['当前压缩包：{name}', 'Current archive: {name}'], '軟體進度': ['7-Zip 回报 {percent}%', '7-Zip reports {percent}%'],
  '結果統計': ['成功 {success} · 部分完成 {partial} · 失败 {failed} · 取消 {cancelled}', 'Success {success} · Partial {partial} · Failed {failed} · Cancelled {cancelled}'],
  '選取數量': ['移除 {count} 项', 'Remove {count} selected'], '排序文件': ['排序 {name}', 'Reorder {name}'], '項目數量': ['（{count} 项）', ' ({count} items)'],
  '最近結果': ['打开最近成功的结果：{path}', 'Open latest successful output: {path}'],
  'helpModes': ['添加文件或文件夹后选择处理方式。文件夹递归扫描，分卷只添加首卷。后缀可选择或自定义；修改后缀不会转换压缩格式。', 'Add files or folders and choose a mode. Folders are scanned recursively; only entry volumes are queued. Choose or enter an extension; renaming does not convert archive formats.'],
  'helpQueue': ['密码每行一组或用逗号分隔。解压成功项自动移出，未成功项保留重试。“打开文件夹”打开最近成功结果。右键可复制路径、重新排队或移除；清空列表不删除磁盘文件。可选的压缩文件删除行为在设置中控制。', 'Separate passwords by lines or commas. Successful extractions leave the queue; unfinished items remain for retry. Open folder shows the latest successful output. Right-click to copy paths, queue again or remove items. Clearing the list does not delete files. Optional archive deletion is controlled in Settings.'],
  'helpKeys': ['Ctrl+O 添加文件 · Ctrl+Shift+O 添加文件夹 · Ctrl+Enter 开始。拖动把手排序，Alt+↑／↓ 上下移动，Shift+F10 打开菜单。', 'Ctrl+O adds files · Ctrl+Shift+O adds folders · Ctrl+Enter starts. Drag the row handle to reorder, Alt+Up/Down to move, Shift+F10 for the menu.'],
};
const traditional: Record<string, string> = {
  '密碼數量': '{count} 組', '已處理數量': '本輪已處理 {done} / {total}', '目前壓縮包': '目前壓縮包：{name}',
  '軟體進度': '7-Zip 回報 {percent}%', '結果統計': '成功 {success} · 部分完成 {partial} · 失敗 {failed} · 取消 {cancelled}',
  '選取數量': '移除 {count} 項', '排序文件': '排序 {name}', '項目數量': '（{count} 項）', '最近結果': '開啟最近成功的結果：{path}',
  'helpModes': '加入文件或資料夾後選擇處理方式。資料夾遞迴掃描，分卷只加入首卷。後綴可選擇或自訂；修改後綴不會轉換壓縮格式。',
  'helpQueue': '密碼每行一組或用逗號分隔。解壓成功項自動移出，未成功項保留重試。「開啟資料夾」開啟最近成功結果。右鍵可複製路徑、重新排隊或移除；清空列表不刪除磁碟文件。選用的壓縮文件刪除行為在設定中控制。',
  'helpKeys': 'Ctrl+O 加入文件 · Ctrl+Shift+O 加入資料夾 · Ctrl+Enter 開始。拖動把手排序，Alt+↑／↓ 上下移動，Shift+F10 開啟選單。',
};
export function t(key: string, params: Record<string, string | number> = {}): string {
  const pair = messages[key];
  if (!pair && uiLanguage.value !== 'zh-TW') {
    const english = uiLanguage.value === 'en';
    const attempt = key.match(/^(.*) · (7z|winrar) · (無密碼|密碼候選 (\d+))$/);
    if (attempt) return `${attempt[1]} · ${attempt[2]} · ${attempt[4] ? (english ? `Password candidate ${attempt[4]}` : `密码候选 ${attempt[4]}`) : (english ? 'No password' : '无密码')}`;
    const elapsed = key.match(/^(.*) · 已用時 (\d+) 秒 · 可取消$/);
    if (elapsed) return `${t(elapsed[1])} · ${english ? 'Elapsed' : '已用时'} ${elapsed[2]}s · ${english ? 'Cancellable' : '可取消'}`;
    const level = key.match(/^第 (\d+) 層 · (.*)$/);
    if (level) return `${english ? 'Level' : '第'} ${level[1]}${english ? '' : ' 层'} · ${level[2]}`;
    const deleted = key.match(/^已刪除壓縮文件：(.*)$/);
    if (deleted) return `${english ? 'Deleted archive: ' : '已删除压缩文件：'}${deleted[1]}`;
    const missing = key.match(/^結果目錄不存在：(.*)$/);
    if (missing) return `${english ? 'Output folder no longer exists: ' : '结果目录不存在：'}${missing[1]}`;
    if (key === '尚無成功解壓的結果目錄') return english ? 'No successful extraction output yet' : '暂无成功解压的结果目录';
  }
  const text = uiLanguage.value === 'zh-TW' ? traditional[key] || key : pair?.[uiLanguage.value === 'en' ? 1 : 0] || key;
  return text.replace(/\{(\w+)\}/g, (match, name: string) => String(params[name] ?? match));
}
