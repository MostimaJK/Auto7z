<script setup lang="ts">
import { t } from './i18n';
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import type { Row } from './api';
const props = defineProps<{ rows: Row[]; shown: Row[]; selected: Row[]; busy: boolean; active: boolean; statuses: Record<Row['status'], string>; statusTypes: Record<Row['status'], 'primary' | 'success' | 'warning' | 'danger' | 'info'>; name: (p: string) => string; size: (n: number) => string }>();
const emit = defineEmits<{ select: [rows: Row[]]; detail: [row: Row]; remove: [ids: string[]]; reorder: [ids: string[]]; requeue: [ids: string[]]; copy: [path: string]; open: [row: Row] }>();
const root = ref<HTMLElement>();
const menuEl = ref<HTMLElement>();
const menu = ref<{ row: Row; x: number; y: number; focus: HTMLElement | null } | null>(null);
const drag = ref<{ id: string; target: string; after: boolean; pointer: number; y: number; moved: boolean } | null>(null);
const contextIds = computed(() => menu.value && props.selected.some(r => r.id === menu.value!.row.id) ? props.selected.map(r => r.id) : menu.value ? [menu.value.row.id] : []);
const contextIndex = computed(() => props.rows.findIndex(r => r.id === menu.value?.row.id));
function closeMenu(restore = false) { const focus = menu.value?.focus; menu.value = null; if (restore) focus?.focus(); }
async function context(row: Row, _column: unknown, event: MouseEvent) {
  event.preventDefault();
  menu.value = { row, x: event.clientX, y: event.clientY, focus: event.target instanceof HTMLElement ? event.target.closest<HTMLElement>('button') : null };
  await nextTick();
  if (!menuEl.value || !menu.value) return;
  const bounds = menuEl.value.getBoundingClientRect();
  menu.value.x = Math.max(8, Math.min(menu.value.x, innerWidth - bounds.width - 8));
  menu.value.y = Math.max(8, Math.min(menu.value.y, innerHeight - bounds.height - 8));
  menuEl.value.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
}
function action(fn: () => void) { fn(); closeMenu(true); }
function keyboardContext(row: Row, event: KeyboardEvent) {
  const target = event.currentTarget as HTMLElement;
  const bounds = target.getBoundingClientRect();
  void context(row, null, { preventDefault() {}, clientX: bounds.right, clientY: bounds.bottom, target } as unknown as MouseEvent);
}
function move(id: string, delta: number) {
  if (props.busy) return;
  const ids = props.rows.map(r => r.id), index = ids.indexOf(id), target = index + delta;
  if (index < 0 || target < 0 || target >= ids.length) return;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  emit('reorder', ids);
}
function menuKey(event: KeyboardEvent) {
  if (event.key === 'Escape' || event.key === 'Tab') { closeMenu(true); return; }
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const buttons = [...menuEl.value!.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
  buttons[event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus();
}
function begin(row: Row, event: PointerEvent) {
  if (props.busy || event.button !== 0) return;
  closeMenu();
  drag.value = { id: row.id, target: row.id, after: false, pointer: event.pointerId, y: event.clientY, moved: false };
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
}
function pointerMove(event: PointerEvent) {
  const d = drag.value;
  if (!d || event.pointerId !== d.pointer) return;
  if (Math.abs(event.clientY - d.y) > 4) d.moved = true;
  if (!d.moved) return;
  event.preventDefault();
  const row = document.elementFromPoint(event.clientX, event.clientY)?.closest('tr');
  const id = row?.querySelector<HTMLElement>('[data-queue-id]')?.dataset.queueId;
  if (id && row && root.value?.contains(row)) { d.target = id; const rect = row.getBoundingClientRect(); d.after = event.clientY > rect.top + rect.height / 2; }
  const scroll = root.value?.querySelector<HTMLElement>('.el-scrollbar__wrap');
  if (scroll) { const rect = scroll.getBoundingClientRect(); if (event.clientY < rect.top + 28) scroll.scrollTop -= 14; else if (event.clientY > rect.bottom - 28) scroll.scrollTop += 14; }
}
function finish(event: PointerEvent) {
  const d = drag.value;
  if (!d || d.pointer !== event.pointerId) return;
  drag.value = null;
  if (props.busy || !d.moved || d.id === d.target) return;
  const ids = props.rows.map(r => r.id).filter(id => id !== d.id);
  const index = ids.indexOf(d.target);
  if (index >= 0) { ids.splice(index + Number(d.after), 0, d.id); emit('reorder', ids); }
}
function rowClass({ row }: { row: Row }) { return drag.value?.moved && drag.value.target === row.id ? (drag.value.after ? 'drop-after' : 'drop-before') : ''; }
function outside(event: PointerEvent) { if (menu.value && !menuEl.value?.contains(event.target as Node)) closeMenu(); }
function cancelDrag() { drag.value = null; }
function key(event: KeyboardEvent) { if (event.key === 'Escape') cancelDrag(); }
function dismiss() { closeMenu(); cancelDrag(); }
watch(() => [props.active, props.busy], dismiss);
watch(() => props.rows, rows => { if (menu.value && !rows.some(r => r.id === menu.value!.row.id)) closeMenu(); });
onMounted(() => { window.addEventListener('pointerdown', outside); window.addEventListener('keydown', key); window.addEventListener('blur', dismiss); window.addEventListener('resize', dismiss); });
onUnmounted(() => { window.removeEventListener('pointerdown', outside); window.removeEventListener('keydown', key); window.removeEventListener('blur', dismiss); window.removeEventListener('resize', dismiss); });
</script>

<template>
  <div ref="root" class="table-region" @scroll.capture="closeMenu()">
    <el-table :data="shown" height="100%" row-key="id" :row-class-name="rowClass" highlight-current-row @selection-change="(rows: Row[]) => emit('select', rows)" @row-click="(row: Row) => emit('detail', row)" @row-contextmenu="context" :empty-text="t('此檢視尚無文件')">
      <el-table-column type="selection" width="44" reserve-selection />
      <el-table-column width="38" label="" class-name="drag-column"><template #default="{ row }"><button class="queue-grip" :data-queue-id="row.id" :disabled="busy" :aria-label="t('排序文件', { name: name(row.source) })" :title="t('拖動排序；Alt+↑／↓ 移動，Shift+F10 開啟選單')" @click.stop @pointerdown.stop="begin(row, $event)" @pointermove="pointerMove" @pointerup="finish" @pointercancel="cancelDrag" @lostpointercapture="cancelDrag" @keydown.alt.up.prevent="move(row.id, -1)" @keydown.alt.down.prevent="move(row.id, 1)" @keydown.shift.f10.prevent="keyboardContext(row, $event)"><svg viewBox="0 0 16 20" width="16" height="20" fill="currentColor" aria-hidden="true"><circle v-for="(point, i) in [[5,4],[11,4],[5,10],[11,10],[5,16],[11,16]]" :key="i" :cx="point[0]" :cy="point[1]" r="1.4" /></svg></button></template></el-table-column>
      <el-table-column :label="t('文件')" min-width="240"><template #default="{ row }"><button class="file-button" @click.stop="emit('detail', row)" @contextmenu.stop="context(row, null, $event)"><span class="file-name">{{ name(row.archive || row.source) }}</span><span class="file-path">{{ row.archive || row.source }}</span></button></template></el-table-column>
      <el-table-column :label="t('大小')" width="96" class-name="size-column"><template #default="{ row }">{{ size(row.size) }}</template></el-table-column>
      <el-table-column :label="t('狀態')" width="108"><template #default="{ row }"><el-tag :type="statusTypes[row.status as Row['status']]" effect="light" round>{{ statuses[row.status as Row['status']] }}</el-tag></template></el-table-column>
    </el-table>
    <Teleport to="body"><div v-if="menu" ref="menuEl" class="queue-menu" role="menu" :aria-label="t('文件操作')" :style="{ left: `${menu.x}px`, top: `${menu.y}px` }" @keydown="menuKey" @contextmenu.prevent>
      <el-button text role="menuitem" @click="action(() => emit('detail', menu!.row))">{{ t('查看詳情') }}</el-button>
      <el-button text role="menuitem" @click="action(() => emit('copy', menu!.row.archive || menu!.row.source))">{{ t('複製文件路徑') }}</el-button>
      <el-button text role="menuitem" @click="action(() => emit('open', menu!.row))">{{ t('開啟資料夾') }}</el-button>
      <div class="menu-divider" role="separator" />
      <el-button text role="menuitem" :disabled="busy || contextIndex === 0" @click="action(() => move(menu!.row.id, -1))">{{ t('上移') }}</el-button>
      <el-button text role="menuitem" :disabled="busy || contextIndex === rows.length - 1" @click="action(() => move(menu!.row.id, 1))">{{ t('下移') }}</el-button>
      <el-button text role="menuitem" :disabled="busy" @click="action(() => emit('requeue', contextIds))">{{ t('重新加入待處理') }}{{ contextIds.length > 1 ? t('項目數量', { count: contextIds.length }) : '' }}</el-button>
      <div class="menu-divider" role="separator" />
      <el-button text role="menuitem" :disabled="busy" @click="action(() => emit('remove', contextIds))">{{ t('從佇列移除') }}{{ contextIds.length > 1 ? t('項目數量', { count: contextIds.length }) : '' }}</el-button>
    </div></Teleport>
  </div>
</template>
