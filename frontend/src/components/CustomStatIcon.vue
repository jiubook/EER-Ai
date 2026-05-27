<template>
  <div
    class="custom-entry-icon"
    :class="{ 'custom-entry-icon-small': small }"
  >
    <v-icon class="custom-entry-icon-svg" color="#ff5a36" :size="small ? 24 : 36">mdi-diamond-stone</v-icon>
    <div class="custom-entry-gradient" />
    <div class="custom-entry-tier-bar" />
    <div v-if="!hideName" ref="nameContainerRef" class="custom-entry-name-bar">
      <span ref="nameRef" class="custom-entry-name-text">{{ name }}</span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { useTemplateRef, watch } from 'vue'
import { updateText } from '@/utils/autoFontSizing'

interface Props {
  name: string
  small?: boolean
  hideName?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  small: false,
  hideName: false,
})

const nameContainerRef = useTemplateRef<HTMLDivElement>('nameContainerRef')
const nameRef = useTemplateRef<HTMLSpanElement>('nameRef')

watch([() => props.name, nameRef], () => {
  if (nameRef.value) {
    updateText(nameRef.value, (nameContainerRef.value?.clientWidth || 96) * 0.95, 6, 14)
  }
})
</script>

<style lang="scss" scoped>
.custom-entry-icon {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  border: 2px solid rgba(255, 113, 0, 0.5);
  border-bottom: none;
  background: linear-gradient(
    135deg,
    rgba(255, 113, 0, 0.15),
    rgba(255, 113, 0, 0.05)
  );
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.custom-entry-icon-svg {
  z-index: 1;
}

.custom-entry-gradient {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: linear-gradient(
    to bottom,
    transparent 0%,
    transparent 70%,
    rgba(255, 113, 0, 0.3) 100%
  );
}

.custom-entry-tier-bar {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 4%;
  background-color: #FF7100;
}

.custom-entry-name-bar {
  position: absolute;
  bottom: 4%;
  width: 100%;
  pointer-events: none;
  text-align: center;
  line-height: 1;
}

.custom-entry-name-text {
  display: inline-block;
  font-weight: 500;
  font-size: 0.65rem;
  text-shadow: 0 0 4px rgb(var(--v-theme-surface));
  -webkit-text-stroke: 1px rgb(var(--v-theme-surface));
  paint-order: stroke fill;
}
</style>
