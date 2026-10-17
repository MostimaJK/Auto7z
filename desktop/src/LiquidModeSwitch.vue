<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
const props = defineProps<{ modelValue: string; disabled?: boolean }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const modes = [{ value: 'extract', label: '遞迴解壓' }, { value: 'rename', label: '修改後綴' }, { value: 'restore', label: '改後綴並解壓' }];
const index = computed(() => Math.max(0, modes.findIndex(mode => mode.value === props.modelValue)));
const moving = ref(false);
let settle: ReturnType<typeof setTimeout>;
watch(index, () => { moving.value = false; requestAnimationFrame(() => moving.value = true); clearTimeout(settle); settle = setTimeout(() => moving.value = false, 560); });
onUnmounted(() => clearTimeout(settle));
function illuminate(event: PointerEvent) {
  const track = event.currentTarget as HTMLElement;
  const rect = track.getBoundingClientRect();
  track.style.setProperty('--light-x', `${event.clientX - rect.left}px`);
  track.style.setProperty('--light-y', `${event.clientY - rect.top}px`);
}
</script>

<template>
  <div class="liquid-mode" :class="{ 'is-moving': moving, 'is-disabled': disabled }" :style="{ '--selected': index }" @pointermove="illuminate">
    <span class="liquid-lens" aria-hidden="true"><span /></span>
    <el-radio-group :model-value="modelValue" :disabled="disabled" aria-label="處理方式" @update:model-value="(value: string | number | boolean | undefined) => emit('update:modelValue', String(value))">
      <el-radio-button v-for="mode in modes" :key="mode.value" :value="mode.value">{{ mode.label }}</el-radio-button>
    </el-radio-group>
  </div>
</template>

<style scoped>
.liquid-mode { --light-x: 25%; --light-y: 0px; position: relative; isolation: isolate; width: 428px; max-width: 100%; padding: 5px; border-radius: 999px; background: linear-gradient(120deg, #dce8f588, #ffffffb8 45%, #dce8f56b); border: 1px solid #b5c6da99; box-shadow: inset 0 1px 0 #fff, inset 0 -1px 0 #c3d2e74d, 0 3px 10px #26466e08; backdrop-filter: blur(16px) saturate(1.3); flex-shrink: 0; }
.liquid-mode::after { content: ''; pointer-events: none; position: absolute; inset: 0; border-radius: inherit; background: radial-gradient(150px 75px at var(--light-x) var(--light-y), #ffffffa6, transparent); opacity: 0; transition: opacity .2s; z-index: -1; }
.liquid-mode:hover::after { opacity: 1; }
.liquid-lens { position: absolute; left: 5px; top: 5px; bottom: 5px; width: calc((100% - 10px) / 3); border-radius: 999px; transform: translateX(calc(var(--selected) * 100%)); transition: transform 460ms cubic-bezier(.22, 1.1, .3, 1); background: linear-gradient(145deg, #ffffffd9, #c8e1ff94 60%, #e6f3ffba); border: 1px solid #fff; box-shadow: inset 0 1px 2px #fff, inset 0 -1px 2px #70a7e06b, 0 3px 8px #23496d26, 0 0 0 1px #87b4e42b; backdrop-filter: blur(12px) saturate(1.8); pointer-events: none; z-index: 0; }
.liquid-lens > span { position: absolute; inset: 1px; border-radius: inherit; background: linear-gradient(180deg, #fff7, transparent 45%, #5297ef12); }
.is-moving .liquid-lens > span { animation: liquid-settle 550ms ease-out; }
.liquid-mode:active:not(.is-disabled) .liquid-lens { scale: 1.035 1.06; }
.liquid-mode :deep(.el-radio-group) { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); width: 100%; position: relative; z-index: 1; }
.liquid-mode :deep(.el-radio-button) { min-width: 0; border-radius: 999px; }
.liquid-mode :deep(.el-radio-button__inner) { border: 0 !important; outline: none !important; border-radius: 999px !important; background: transparent !important; color: #46566c !important; box-shadow: none !important; width: 100%; min-height: 38px; padding: 11px 8px; font-size: 14px; transition: color .2s; }
.liquid-mode :deep(.el-radio-button.is-active .el-radio-button__inner) { color: #17498b !important; font-weight: 650; }
.liquid-mode :deep(.el-radio-button:hover .el-radio-button__inner) { color: #17498b !important; }
.liquid-mode :deep(.el-radio-button:focus-within) { outline: none; }
.liquid-mode :deep(.el-radio-button:has(input:focus-visible)) { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.is-disabled { opacity: .6; }
:global(html.dark .liquid-mode) { background: linear-gradient(120deg, #334863a3, #263448cc 55%, #3d516783); border-color: #647e9c70; box-shadow: inset 0 1px 0 #ffffff1a, 0 3px 12px #0002; }
:global(html.dark .liquid-mode .liquid-lens) { background: linear-gradient(145deg, #91b4df6e, #477fbc66 60%, #709fce73); border-color: #d3e9ff69; box-shadow: inset 0 1px 1px #ffffff4d, inset 0 -1px 2px #1f3d6599, 0 3px 10px #0004; }
:global(html.dark .liquid-mode .el-radio-button__inner) { color: #c4d1e2 !important; }
:global(html.dark .liquid-mode .el-radio-button.is-active .el-radio-button__inner), :global(html.dark .liquid-mode .el-radio-button:hover .el-radio-button__inner) { color: #fff !important; }
@keyframes liquid-settle { 0% { scale: 1.12 .92; filter: brightness(1.12); } 48% { scale: .98 1.035; } 100% { scale: 1; filter: brightness(1); } }
@media (max-width: 850px) { .liquid-mode { width: 380px; } }
@media (max-height: 620px) { .liquid-mode :deep(.el-radio-button__inner) { min-height: 32px; padding-top: 8px; padding-bottom: 8px; } }
@media (prefers-reduced-motion: reduce) { .liquid-lens { transition: none; } .is-moving .liquid-lens > span { animation: none; } .liquid-mode:active:not(.is-disabled) .liquid-lens { scale: 1; } }
@media (prefers-reduced-transparency: reduce), (forced-colors: active) { .liquid-mode, .liquid-lens { backdrop-filter: none; background: var(--surface); } .liquid-lens { border: 2px solid var(--el-color-primary); } .liquid-mode::after { display: none; } }
@media (prefers-reduced-transparency: reduce), (forced-colors: active) { :global(html.dark .liquid-mode), :global(html.dark .liquid-mode .liquid-lens) { backdrop-filter: none; background: var(--surface); } }
</style>
