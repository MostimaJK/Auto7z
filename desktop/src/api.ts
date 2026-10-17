import { invoke, isTauri } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export type Status = 'pending' | 'running' | 'success' | 'partial' | 'failed' | 'cancelled';
export interface Row { id: string; source: string; size: number; status: Status; output: string; detail: string; archive: string }
export interface ExtractionProgress { percent: number | null; archive: string; tool: string; attempt: number }
export interface State { rows: Row[]; busy: boolean; scanning: boolean; stopping: boolean; activity: string; current: string | null; completed: number; total: number; progress?: ExtractionProgress | null }
export interface Settings { path_7z: string; path_rar: string; max_recursion_depth: number; idle_timeout_seconds: number; timeout_7z_precheck: number; delete_after_extract: boolean; theme: 'system' | 'light' | 'dark' }
type Event = { event?: string; id?: number; ok?: boolean; data?: unknown; error?: string };
let seq = 0;
const pending = new Map<number, { resolve: (v: any) => void; reject: (e: Error) => void; timer: ReturnType<typeof setTimeout> }>();
export const native = isTauri();
export async function connect(onEvent: (event: string, data: any) => void) {
  if (!native) return () => {};
  const rejectAll = (reason: string) => {
    for (const p of pending.values()) { clearTimeout(p.timer); p.reject(new Error(reason)); }
    pending.clear();
    onEvent('error', reason);
  };
  const off = await listen<Event>('backend', ({ payload: e }) => {
    if (e.id !== undefined && pending.has(e.id)) {
      const p = pending.get(e.id)!; clearTimeout(p.timer); pending.delete(e.id);
      if (e.ok) p.resolve(e.data); else p.reject(new Error(e.error));
    } else if (e.event) onEvent(e.event, e.data);
  });
  const offExit = await listen<string>('backend-exit', ({ payload }) => rejectAll(payload));
  const offError = await listen<string>('backend-error', ({ payload }) => onEvent('error', payload));
  return () => { off(); offExit(); offError(); };
}
export async function rpc<T = any>(op: string, args: unknown = {}): Promise<T> {
  if (!native) throw new Error('請使用桌面啟動入口，以存取本機文件');
  return new Promise<T>((resolve, reject) => {
    const id = ++seq;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('引擎未回應，請重新啟動應用程式')); }, 15000);
    pending.set(id, { resolve, reject, timer });
    invoke('send', { message: { id, op, args } }).catch(e => {
      clearTimeout(timer); pending.delete(id); reject(new Error(String(e)));
    });
  });
}
