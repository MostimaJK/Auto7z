<script setup lang="ts">
import { t } from './i18n';
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
const props = defineProps<{ modelValue: string; disabled?: boolean; items?: readonly { value: string; label: string; disabled?: boolean }[]; label?: string; compact?: boolean }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const modes = computed(() => props.items || [{ value: 'extract', label: t('遞迴解壓') }, { value: 'rename', label: t('修改後綴') }, { value: 'restore', label: t('修改後綴並解壓') }]);
const track = ref<HTMLElement>();
const indicator = ref({ translate: '0px', width: '0px' });
const measured = ref(false);
let observer: ResizeObserver | undefined;
function measure() {
  const index = modes.value.findIndex(mode => mode.value === props.modelValue);
  const item = track.value?.querySelectorAll<HTMLElement>('.el-radio-button')[index];
  if (!item || !track.value) return;
  const bounds = item.getBoundingClientRect();
  if (!bounds.width) return; // Keep the last position while another page hides the workspace.
  indicator.value = { translate: `${bounds.left - track.value.getBoundingClientRect().left}px`, width: `${bounds.width}px` };
  measured.value = true;
}
watch([() => props.modelValue, modes], () => nextTick(measure));
onMounted(() => {
  observer = new ResizeObserver(measure);
  if (track.value) observer.observe(track.value);
  void document.fonts.ready.then(measure);
  measure();
});
onUnmounted(() => observer?.disconnect());
</script>

<template>
  <div ref="track" class="mode-switch" :class="{ 'is-disabled': disabled, 'is-compact': compact }">
    <span v-show="measured" class="mode-switch__selection" :style="indicator" aria-hidden="true" />
    <el-radio-group :model-value="modelValue" :disabled="disabled" class="mode-switch__options" :aria-label="label || t('處理方式')" @update:model-value="(value: string | number | boolean | undefined) => emit('update:modelValue', String(value))">
      <el-radio-button v-for="mode in modes" :key="mode.value" :value="mode.value" :disabled="'disabled' in mode && !!mode.disabled">{{ mode.label }}</el-radio-button>
    </el-radio-group>
  </div>
</template>

<style scoped>
.mode-switch { --segment-track: #e9edf6; --segment-fill: #fff; --segment-edge: var(--accent-line); --segment-text: #596579; --segment-selected-text: var(--accent-ink); position: relative; isolation: isolate; background: var(--segment-track); border-radius: 10px; width: fit-content; max-width: 100%; flex-shrink: 0; }
.mode-switch__selection { position: absolute; left: 0; top: 0; height: 100%; background: var(--segment-fill); border: 2px solid var(--segment-edge); border-radius: 12px; pointer-events: none; transition: translate 200ms cubic-bezier(0, 0, .2, 1), width 200ms cubic-bezier(0, 0, .2, 1); }
.mode-switch :deep(.el-radio-group) { display: flex; flex-wrap: nowrap; position: relative; z-index: 1; }
.mode-switch :deep(.el-radio-button) { border-radius: 12px; }
.mode-switch :deep(.el-radio-button__inner) { display: block; width: 100%; min-height: 40px; padding: 13px 16px; border: 0 !important; outline: none !important; border-radius: 12px !important; background: transparent !important; box-shadow: none !important; color: var(--segment-text) !important; font-size: 14px; font-weight: 400; transition: color 120ms ease, transform 120ms ease; }
.mode-switch :deep(.el-radio-button.is-active .el-radio-button__inner) { color: var(--segment-selected-text) !important; }
.mode-switch :deep(.el-radio-button:hover .el-radio-button__inner) { color: var(--segment-selected-text) !important; }
.mode-switch:not(.is-disabled) :deep(.el-radio-button:active .el-radio-button__inner) { transform: scale(.97); }
.mode-switch :deep(.el-radio-button:focus-within) { outline: none; }
.mode-switch :deep(.el-radio-button:has(input:focus-visible)) { outline: 2px solid var(--el-color-primary); outline-offset: 3px; }
.is-disabled { opacity: .5; }
:global(html.dark .mode-switch) { --segment-track: #272f40; --segment-fill: #202d4b; --segment-text: #bec8db; }
.is-compact :deep(.el-radio-button__inner) { min-height: 36px; padding: 11px 16px; }
@media (max-height: 620px) { .mode-switch :deep(.el-radio-button__inner) { min-height: 36px; padding-top: 11px; padding-bottom: 11px; } }
@media (prefers-reduced-motion: reduce) { .mode-switch__selection, .mode-switch :deep(.el-radio-button__inner) { transition: none; } .mode-switch:not(.is-disabled) :deep(.el-radio-button:active .el-radio-button__inner) { transform: none; } }
@media (forced-colors: active) { .mode-switch { background: Canvas; } .mode-switch__selection { background: Highlight; border-color: Highlight; } .mode-switch :deep(.el-radio-button__inner) { color: ButtonText !important; } .mode-switch :deep(.el-radio-button.is-active .el-radio-button__inner) { color: HighlightText !important; } }
</style>
