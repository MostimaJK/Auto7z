import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  FluentProvider, webLightTheme, webDarkTheme, tokens, Button, Badge,
  Field, Input, Textarea, Select, Checkbox, ProgressBar, Spinner,
  Table, TableHeader, TableBody, TableRow, TableHeaderCell, TableCell, TableSelectionCell,
  TabList, Tab, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem,
  Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions,
  Accordion, AccordionItem, AccordionHeader, AccordionPanel, MessageBar, MessageBarBody, MessageBarActions,
} from '@fluentui/react-components';
import {
  AddRegular, FolderOpenRegular, SettingsRegular, WeatherMoonRegular, WeatherSunnyRegular,
  PlayRegular, DismissRegular, ArrowClockwiseRegular, DeleteRegular,
  DocumentRegular, BoxRegular, QuestionCircleRegular, CopyRegular, ChevronDownRegular,
} from '@fluentui/react-icons';
import { open } from '@tauri-apps/plugin-dialog';
import { getCurrentWebview } from '@tauri-apps/api/webview';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { connect, native, rpc, type State, type Settings } from './api';
import './styles.css';

const empty: State = { rows: [], busy: false, scanning: false, stopping: false, current: null, activity: '準備就緒', completed: 0, total: 0 };
const defaults: Settings = { path_7z: '', path_rar: '', max_recursion_depth: 20, idle_timeout_seconds: 0, timeout_7z_precheck: 30, delete_after_extract: false, theme: 'system' };
const labels = { pending: '待處理', running: '處理中', success: '成功', partial: '部分完成', failed: '失敗', cancelled: '已取消' };
const statusColors = { pending: 'subtle', running: 'brand', success: 'success', partial: 'warning', failed: 'danger', cancelled: 'informative' } as const;
const name = (p: string) => p.split(/[\\/]/).pop() || p;
const bytes = (v: number) => v < 1024 ? `${v} B` : v < 1048576 ? `${(v / 1024).toFixed(1)} KB` : v < 1073741824 ? `${(v / 1048576).toFixed(1)} MB` : `${(v / 1073741824).toFixed(1)} GB`;

function App() {
  const [state, setState] = useState(empty);
  const live = useRef(state); live.current = state;
  const [settings, setSettings] = useState(defaults);
  const [draft, setDraft] = useState(defaults);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const [mode, setMode] = useState('extract');
  const modeRef = useRef(mode); modeRef.current = mode;
  const [extension, setExtension] = useState('.zip');
  const [engineMode, setEngineMode] = useState('auto');
  const [passwords, setPasswords] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [focused, setFocused] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [dialog, setDialog] = useState<'settings' | 'help' | 'close' | null>(null);
  const settingsButton = useRef<HTMLButtonElement>(null);
  const helpButton = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const showDialog = (value: 'settings' | 'help' | 'close') => { returnFocus.current = value === 'settings' ? settingsButton.current : value === 'help' ? helpButton.current : document.activeElement as HTMLElement; setDialog(value); };
  useEffect(() => { if (!dialog) { const frame = requestAnimationFrame(() => { if (returnFocus.current?.isConnected) returnFocus.current.focus(); }); return () => cancelAnimationFrame(frame); } }, [dialog]);
  const [working, setWorking] = useState(false);
  const [drag, setDrag] = useState(false);
  const [systemDark, setSystemDark] = useState(matchMedia('(prefers-color-scheme: dark)').matches);
  const busy = state.busy || state.scanning || working;
  const dark = settings.theme === 'dark' || (settings.theme === 'system' && systemDark);
  useEffect(() => {
    if (native && ready) void getCurrentWindow().setTheme(dark ? 'dark' : 'light').catch(e => setError(String(e)));
  }, [dark, ready]);
  const row = state.rows.find(r => r.id === focused);
  const candidates = passwords.split(/[\n,，]/).map(p => p.trim()).filter(Boolean);
  const retry = state.rows.some(r => ['failed', 'partial', 'cancelled'].includes(r.status));
  const canStart = state.rows.some(r => r.status !== 'success');
  const shown = state.rows.filter(r => filter === 'all' || (filter === 'pending' ? ['pending', 'running'].includes(r.status) : !['pending', 'running'].includes(r.status)));
  const done = state.rows.filter(r => !['pending', 'running'].includes(r.status));
  const successes = state.rows.filter(r => r.status === 'success').length;
  const attempt = async (task: () => Promise<unknown>) => {
    try { setWorking(true); await task(); } catch (e) { setError(String(e instanceof Error ? e.message : e)); } finally { setWorking(false); }
  };
  const addPaths = async (paths: string[]) => { await rpc('add', { paths, include_all: modeRef.current !== 'extract' }); };
  const pick = (folder = false) => attempt(async () => {
    const paths = await open({ directory: folder, multiple: true, title: folder ? '加入資料夾' : '加入文件' });
    if (paths) await addPaths(Array.isArray(paths) ? paths : [paths]);
  });
  const start = () => attempt(async () => {
    setError('');
    await rpc('start', { mode, extension, passwords: candidates, engine_mode: engineMode });
  });
  const remove = (ids: string[]) => attempt(async () => {
    await rpc('remove', { ids }); setSelected([]); if (focused && ids.includes(focused)) setFocused(null);
  });
  useEffect(() => {
    let disposed = false;
    const cleanups: (() => void)[] = [];
    (async () => {
      const off = await connect((event, data) => {
        if (disposed) return;
        if (event === 'state') setState(data);
        if (event === 'activity') setState(s => ({ ...s, activity: data }));
        if (event === 'log') setLogs(l => [...l.slice(-1999), `${new Date().toLocaleTimeString('zh-TW')}  ${data}`]);
        if (event === 'error') setError(data);
      });
      if (disposed) { off(); return; } cleanups.push(off);
      if (!native) { setError('瀏覽器僅供介面預覽。請執行 Start_Auto7z_Fluent.bat 使用本機解壓功能。'); return; }
      const init = await rpc<{ settings: Settings; state: State; warning: string }>('init');
      if (disposed) return;
      setSettings(init.settings); setState(init.state); setReady(true); if (init.warning) setError(init.warning);
      cleanups.push(await getCurrentWebview().onDragDropEvent(({ payload }) => {
        setDrag(payload.type === 'enter' || payload.type === 'over');
        if (payload.type === 'drop') {
          setDrag(false);
          if (!live.current.busy && !live.current.scanning) void attempt(() => addPaths(payload.paths));
        }
      }));
      cleanups.push(await getCurrentWindow().onCloseRequested(event => {
        if (live.current.busy || live.current.scanning) { event.preventDefault(); showDialog('close'); }
      }));
    })().catch(e => setError(String(e)));
    const media = matchMedia('(prefers-color-scheme: dark)');
    const change = () => setSystemDark(media.matches); media.addEventListener('change', change);
    return () => { disposed = true; cleanups.forEach(off => off()); media.removeEventListener('change', change); };
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'o' && !busy && ready && !dialog) { e.preventDefault(); void pick(e.shiftKey); }
      if (e.ctrlKey && e.key === 'Enter' && canStart && !busy && !dialog) { e.preventDefault(); start(); }
    };
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key);
  });
  const save = () => attempt(async () => { const value = await rpc<Settings>('save', draft); setSettings(value); setDialog(null); });
  const cycleTheme = () => attempt(async () => { const value = await rpc<Settings>('save', { ...settings, theme: dark ? 'light' : 'dark' }); setSettings(value); });
  const addMenu = (primary = false) => <Menu><MenuTrigger disableButtonEnhancement><Button appearance={primary ? 'primary' : 'secondary'} icon={<AddRegular />} disabled={busy || !ready}>加入<ChevronDownRegular /></Button></MenuTrigger><MenuPopover><MenuList><MenuItem icon={<DocumentRegular />} onClick={() => pick()}>文件 <span className="shortcut">Ctrl+O</span></MenuItem><MenuItem icon={<FolderOpenRegular />} onClick={() => pick(true)}>資料夾 <span className="shortcut">Ctrl+Shift+O</span></MenuItem></MenuList></MenuPopover></Menu>;
  const theme = { ...(dark ? webDarkTheme : webLightTheme), fontFamilyBase: "'Segoe UI', 'Microsoft JhengHei UI', 'Microsoft JhengHei', sans-serif" };
  return <FluentProvider theme={theme} style={{ '--canvas': tokens.colorNeutralBackground2, '--surface': tokens.colorNeutralBackground1, '--line': tokens.colorNeutralStroke2, '--text': tokens.colorNeutralForeground1, '--muted': tokens.colorNeutralForeground2, '--accent': tokens.colorBrandForeground1, '--selected': tokens.colorNeutralBackground1Selected, '--danger': tokens.colorPaletteRedForeground1 } as React.CSSProperties}>
    <main className={`shell ${drag ? 'dragging' : ''}`}>
      <header className="app-header"><div className="identity"><BoxRegular /><h1>Auto7z</h1><Badge appearance="tint" color="informative">Fluent</Badge></div><div className="header-actions"><Button appearance="subtle" icon={dark ? <WeatherSunnyRegular /> : <WeatherMoonRegular />} aria-label={dark ? '切換淺色主題' : '切換深色主題'} title="切換主題" disabled={busy || !ready} onClick={cycleTheme} /><Button ref={settingsButton} appearance="subtle" icon={<SettingsRegular />} disabled={busy || !ready} onClick={() => { setDraft({ ...settings }); setError(''); showDialog('settings'); }}>設定</Button></div></header>
      {error && !dialog && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody><MessageBarActions containerAction={<Button appearance="transparent" icon={<DismissRegular />} aria-label="關閉錯誤" onClick={() => setError('')} />} /></MessageBar>}
      <section className="workspace" aria-label="文件工作區">
        <div className="work-heading"><h2>文件佇列</h2><span className="muted">{state.rows.length} 個文件</span><div className="grow" />{state.scanning && <Spinner size="tiny" label="掃描中" />}{state.rows.length > 0 && addMenu()}</div>
        <div className="task-options"><Field label="處理方式" orientation="horizontal"><Select value={mode} disabled={busy || done.length > 0} onChange={e => setMode(e.target.value)}><option value="extract">遞迴解壓</option><option value="restore">還原後綴並解壓</option><option value="rename">只修改後綴</option></Select></Field>{mode !== 'extract' && <Field label="目標後綴" orientation="horizontal"><Input aria-label="目標後綴" className="extension" value={extension} disabled={busy} onChange={(_, d) => setExtension(d.value)} /></Field>}{mode !== 'rename' && <Field label="引擎" orientation="horizontal"><Select value={engineMode} disabled={busy} onChange={e => setEngineMode(e.target.value)}><option value="auto">自動</option><option value="7z">7-Zip</option><option value="winrar">WinRAR</option></Select></Field>}</div>
        {state.rows.length > 0 && <div className="collection-toolbar"><TabList selectedValue={filter} onTabSelect={(_, d) => setFilter(String(d.value))} size="small"><Tab value="all">全部</Tab><Tab value="pending">待處理</Tab><Tab value="results">結果 {done.length > 0 && `(${done.length})`}</Tab></TabList><div className="grow" />{selected.length > 0 ? <Button appearance="subtle" icon={<DeleteRegular />} disabled={busy} onClick={() => remove(selected)}>移除 {selected.length} 項</Button> : state.rows.length > 0 && <Button appearance="subtle" disabled={busy} onClick={() => remove(state.rows.map(r => r.id))}>清空佇列</Button>}</div>}
        <div className="work-body">
          {state.rows.length === 0 ? <div className="empty"><div className="empty-symbol"><FolderOpenRegular /></div><h3>加入要處理的文件</h3><p className="muted">將文件或資料夾拖入此處</p>{addMenu(true)}<Button ref={helpButton} appearance="transparent" icon={<QuestionCircleRegular />} onClick={() => showDialog('help')}>使用說明</Button></div> : <>
            <div className="file-region"><Table aria-label="文件佇列" size="medium"><TableHeader><TableRow><TableSelectionCell aria-label="全選" checked={shown.length > 0 && shown.every(r => selected.includes(r.id)) ? true : shown.some(r => selected.includes(r.id)) ? 'mixed' : false} onClick={() => setSelected(shown.every(r => selected.includes(r.id)) ? [] : shown.map(r => r.id))} /><TableHeaderCell>文件</TableHeaderCell><TableHeaderCell className="size-cell">大小</TableHeaderCell><TableHeaderCell className="status-cell">狀態</TableHeaderCell></TableRow></TableHeader><TableBody>{shown.map((r, i) => <TableRow key={r.id} tabIndex={0} aria-label={`${name(r.source)}，${labels[r.status]}`} appearance={r.id === focused ? 'brand' : 'none'} onClick={() => setFocused(r.id)} onKeyDown={e => { if (e.key === 'Enter') setFocused(r.id); if (e.key === ' ') { e.preventDefault(); setSelected(s => s.includes(r.id) ? s.filter(id => id !== r.id) : [...s, r.id]); } if (['ArrowDown', 'ArrowUp'].includes(e.key)) { e.preventDefault(); const next = e.currentTarget.parentElement?.children[i + (e.key === 'ArrowDown' ? 1 : -1)] as HTMLElement; next?.focus(); } }}><TableSelectionCell checked={selected.includes(r.id)} aria-label={`選取 ${name(r.source)}`} onClick={e => { e.stopPropagation(); setSelected(s => s.includes(r.id) ? s.filter(id => id !== r.id) : [...s, r.id]); }} /><TableCell><div className="file-cell"><DocumentRegular /><div><div className="file-name">{name(r.source)}</div><div className="file-path">{r.source}</div></div></div></TableCell><TableCell className="size-cell">{bytes(r.size)}</TableCell><TableCell className="status-cell"><Badge appearance="tint" color={statusColors[r.status]}>{labels[r.status]}</Badge></TableCell></TableRow>)}</TableBody></Table>{shown.length === 0 && <p className="filter-empty muted">此檢視尚無文件</p>}</div>
            {row && <aside className="details" aria-label="文件詳情"><div className="detail-title"><h3>文件詳情</h3><Button appearance="subtle" icon={<DismissRegular />} aria-label="關閉文件詳情" onClick={() => setFocused(null)} /></div><Field label="來源"><Textarea readOnly value={row.source} resize="vertical" /></Field>{row.archive && row.archive !== row.source && <Field label="目前原包"><Textarea readOnly value={row.archive} resize="vertical" /></Field>}<Badge appearance="tint" color={statusColors[row.status]}>{labels[row.status]}</Badge>{row.output && <Field label="結果目錄"><Textarea readOnly value={row.output} resize="vertical" /></Field>}{row.detail && <Field label="處理訊息"><Textarea readOnly value={row.detail} resize="vertical" /></Field>}<Button icon={<FolderOpenRegular />} disabled={row.status === 'pending' || row.status === 'running'} onClick={() => attempt(() => rpc('open', { id: row.id }))}>{row.output ? '開啟結果目錄' : '開啟來源位置'}</Button></aside>}
          </>}
        </div>
        {mode !== 'rename' && <Accordion collapsible className="password-options"><AccordionItem value="password"><AccordionHeader size="small">候選密碼{candidates.length ? ` · ${new Set(candidates).size} 組` : ' · 未設定'}</AccordionHeader><AccordionPanel><Field label="候選密碼" hint="每行一組，或以逗號分隔；僅保留在本次工作階段。"><Textarea value={passwords} disabled={busy} onChange={(_, d) => setPasswords(d.value)} resize="vertical" placeholder="留空時嘗試無密碼解壓" /></Field></AccordionPanel></AccordionItem></Accordion>}
        <footer className="task-footer"><div className="task-status" role="status" aria-live="polite"><div className="status-line"><strong>{state.activity}</strong>{state.total > 0 && <span>本輪已處理 {state.completed} / {state.total}</span>}</div>{state.busy && <><ProgressBar aria-label="目前文件活動，位元組進度未知" /><span className="muted">目前文件：{name(state.rows.find(r => r.id === state.current)?.source || '')} · 位元組進度未知</span></>}{!state.busy && done.length > 0 && <span className="muted">成功 {successes} · 部分完成 {done.filter(r => r.status === 'partial').length} · 失敗 {done.filter(r => r.status === 'failed').length} · 取消 {done.filter(r => r.status === 'cancelled').length}</span>}</div>{(state.busy || state.scanning) ? <Button icon={<DismissRegular />} disabled={state.stopping || working} onClick={() => attempt(() => rpc('cancel'))}>{state.stopping ? '正在取消…' : '取消'}</Button> : <Button appearance="primary" icon={retry ? <ArrowClockwiseRegular /> : <PlayRegular />} disabled={!ready || busy || !canStart} onClick={start}>{retry ? '重試未成功項目' : mode === 'rename' ? '修改後綴' : '開始解壓'}</Button>}</footer>
      </section>
      <Accordion collapsible className="logs"><AccordionItem value="logs"><AccordionHeader size="small">工作日誌{logs.length ? ` · ${logs.length} 筆` : ''}</AccordionHeader><AccordionPanel><div className="log-tools"><span className="muted">最近 2,000 筆 · 可選取與複製</span><Button size="small" appearance="subtle" icon={<CopyRegular />} onClick={() => attempt(() => navigator.clipboard.writeText(logs.join('\n')))}>複製</Button></div><Textarea aria-label="完整工作日誌" readOnly value={logs.join('\n')} resize="vertical" className="log-text" /></AccordionPanel></AccordionItem></Accordion>
      <Dialog open={dialog !== null} onOpenChange={(_, d) => { if (!d.open && !working) setDialog(null); }}><DialogSurface className="dialog-surface"><DialogBody><DialogTitle>{dialog === 'settings' ? '設定' : dialog === 'close' ? '工作仍在進行' : '使用說明'}</DialogTitle><DialogContent className="dialog-content">{error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}{dialog === 'settings' ? <div className="settings-fields"><Field label="外觀"><Select value={draft.theme} onChange={e => setDraft({ ...draft, theme: e.target.value as Settings['theme'] })}><option value="system">跟隨系統</option><option value="light">淺色</option><option value="dark">深色</option></Select></Field>{(['path_7z', 'path_rar'] as const).map(key => <Field key={key} label={key === 'path_7z' ? '7-Zip 路徑' : 'WinRAR 路徑（選用）'}><div className="path-input"><Input value={draft[key]} onChange={(_, d) => setDraft({ ...draft, [key]: d.value })} /><Button onClick={() => attempt(async () => { const p = await open({ multiple: false, directory: false, filters: [{ name: '執行檔', extensions: ['exe'] }] }); if (typeof p === 'string') setDraft(s => ({ ...s, [key]: p })); })}>瀏覽</Button></div></Field>)}{([{ key: 'max_recursion_depth', label: '遞迴層數上限', min: 1, max: 100 }, { key: 'timeout_7z_precheck', label: '目錄預檢逾時（秒）', min: 3, max: 300 }, { key: 'idle_timeout_seconds', label: '停滯保護（秒，0 為關閉）', min: 0, max: 86400 }] as const).map(f => <Field key={f.key} label={f.label}><Input type="number" min={f.min} max={f.max} value={String(draft[f.key])} onChange={(_, d) => setDraft({ ...draft, [f.key]: Number(d.value) })} /></Field>)}<Checkbox label="成功解壓後刪除內層壓縮包" checked={draft.delete_after_extract} onChange={(_, d) => setDraft({ ...draft, delete_after_extract: d.checked === true })} /><p className="muted">最外層原包始終保留。同名結果另建目錄。設定與舊版分開儲存。</p></div> : dialog === 'close' ? <p>關閉將取消目前工作，保留已成功的結果。取消後再關閉視窗。</p> : <div className="help"><p>加入文件或資料夾，選擇處理方式後開始。資料夾會遞迴掃描；只加入分卷的首卷。</p><p>還原後綴模式可處理偽裝副檔名。只修改後綴會直接改名，遇到同名文件時停止該項，不會覆蓋。</p><p>選取文件列可查看完整路徑、錯誤與結果。重試略過成功項目，部分完成的內層錯誤可查看處理訊息。</p><p>Ctrl+O 加入文件 · Ctrl+Shift+O 加入資料夾 · Ctrl+Enter 開始 · 方向鍵移動文件列 · 空白鍵選取 · Enter 查看詳情。</p></div>}</DialogContent><DialogActions>{dialog === 'settings' ? <><Button disabled={working} onClick={() => setDialog(null)}>取消</Button><Button appearance="primary" disabled={working} onClick={save}>儲存</Button></> : dialog === 'close' ? <><Button onClick={() => setDialog(null)}>繼續工作</Button><Button appearance="primary" disabled={working} onClick={() => attempt(async () => { await rpc('cancel'); setDialog(null); })}>取消工作</Button></> : <Button appearance="primary" onClick={() => setDialog(null)}>知道了</Button>}</DialogActions></DialogBody></DialogSurface></Dialog>
    </main>
  </FluentProvider>;
}
createRoot(document.getElementById('root')!).render(<App />);
