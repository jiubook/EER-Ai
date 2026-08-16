<template>
  <v-dialog v-model="open" max-width="960" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-image-outline</v-icon>
        导出宝藏基质图片
      </v-card-title>

      <v-card-text>
        <!-- 导出范围：与页面顶部的筛选相互独立，避免互相污染 -->
        <div class="d-flex align-center gap-2 mb-2">
          <span class="text-body-2 text-medium-emphasis">导出星级：</span>
          <v-chip-group v-model="selectedRarities" column multiple>
            <v-chip color="primary" filter size="small" value="3" variant="outlined"> 3★ </v-chip>
            <v-chip color="primary" filter size="small" value="4" variant="outlined"> 4★ </v-chip>
            <v-chip color="primary" filter size="small" value="5" variant="outlined"> 5★ </v-chip>
            <v-chip color="primary" filter size="small" value="6" variant="outlined"> 6★ </v-chip>
            <v-chip color="primary" filter size="small" value="custom" variant="outlined">
              自定义
            </v-chip>
          </v-chip-group>
        </div>

        <div class="d-flex flex-wrap align-center ga-4 mb-1">
          <v-switch
            v-model="includeMaxed"
            color="primary"
            density="compact"
            hide-details
            label="包含满级武器（6/6/3）"
          />
          <v-switch
            v-model="onlyIncludedInCalculation"
            color="primary"
            density="compact"
            hide-details
            label="仅导出参与计算的条目"
          />
          <v-switch
            v-model="showBadges"
            color="primary"
            density="compact"
            hide-details
            label="显示扫描数量角标"
          />
        </div>
        <div class="text-caption text-medium-emphasis mb-4">
          角标来自本次运行的扫描结果，重启后清零；自定义基质无对应数据。
        </div>

        <v-alert v-if="totalCount === 0" border="start" type="warning" variant="tonal">
          当前筛选下没有可导出的条目。
        </v-alert>

        <template v-else>
          <div class="text-body-2 text-medium-emphasis mb-2">
            将导出 {{ totalCount }} 项（内置 {{ weaponCards.length }} / 自定义
            {{ customCards.length }}）
            <template v-if="renderInfo">
              · {{ renderInfo.width }} × {{ renderInfo.height }} @{{ renderInfo.scale }}x ·
              {{ renderInfo.sizeText }}
            </template>
          </div>

          <v-progress-linear v-if="rendering" color="primary" indeterminate />
          <img v-if="previewUrl" alt="宝藏基质导出预览" class="export-preview" :src="previewUrl" />
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false">关闭</v-btn>
        <v-btn
          :disabled="!previewUrl || rendering"
          :loading="copying"
          variant="tonal"
          @click="copyToClipboard"
        >
          复制到剪贴板
        </v-btn>
        <v-btn
          color="primary"
          :disabled="!previewUrl || rendering"
          :loading="saving"
          variant="flat"
          @click="saveToDisk"
        >
          保存并打开文件夹
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import type { TreasureMatrixEntry } from '@/composables/useProfiles'
import type { ExportCard, ExportTheme } from '@/utils/matrixExport'
import { computed, onUnmounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useCustomStats } from '@/composables/useCustomStats'
import { useProfiles } from '@/composables/useProfiles'
import { useToast } from '@/composables/useToast'
import { AFFIX_MAX_LEVEL, useWeaponStats } from '@/composables/useWeaponStats'
import { getItemIconUrl, getItemTierColor } from '@/utils/gameData/item'
import { useStaticData } from '@/utils/gameData/staticData'
import { fallbackCustomStatName, findCustomStat } from '@/utils/gameData/weapon'
import { renderMatrixExport } from '@/utils/matrixExport'

const open = defineModel<boolean>({ default: false })

const toast = useToast()
const theme = useTheme()
const { activeProfileName, treasureMatrix } = useProfiles()
const { customStats } = useCustomStats()
const { isCustomEntry, isWeaponMaxed, getWeaponPriority } = useWeaponStats()
const { weaponsMap, matrixIcons } = useStaticData()

/** 自定义基质在导出图里按 6★ 处理，与页面筛选口径一致 */
const CUSTOM_RARITY_KEY = 'custom'
/** 自定义基质卡片的底部色条 */
const CUSTOM_TIER_COLOR = '#ff7100'

const selectedRarities = ref<string[]>(['3', '4', '5', '6', CUSTOM_RARITY_KEY])
const includeMaxed = ref(true)
const onlyIncludedInCalculation = ref(false)
const showBadges = ref(false)

const essenceCounts = ref<Record<string, number>>({})
const previewUrl = ref<string | null>(null)
const previewBlob = ref<Blob | null>(null)
const renderInfo = ref<{
  width: number
  height: number
  scale: number
  sizeText: string
} | null>(null)
const rendering = ref(false)
const copying = ref(false)
const saving = ref(false)

let renderToken = 0
let redrawTimer: ReturnType<typeof setTimeout> | undefined

/**
 * 解析条目的技能属性图标地址。
 *
 * 自定义基质从配置里取技能词条，内置武器从静态数据取；
 * 两者都没有匹配时回退到默认基质图标。
 */
function resolveSkillIconUrl(weaponId: string): string | null {
  const fallback = matrixIcons.value.defaultIcon || null
  const skillStatId = isCustomEntry(weaponId)
    ? findCustomStat(weaponId, customStats.value)?.stat.skill
    : weaponsMap.value.get(weaponId)?.skillStatId
  if (!skillStatId) return fallback
  return matrixIcons.value.skills[skillStatId] || fallback
}

/** 自定义基质的显示名，配置里没填时用兜底名 */
function resolveCustomName(entry: TreasureMatrixEntry): string {
  const found = findCustomStat(entry.weapon_id, customStats.value)
  if (!found) return entry.weapon_name || entry.weapon_id
  return found.stat.name || fallbackCustomStatName(found.index)
}

function matchesFilters(entry: TreasureMatrixEntry, rarityKey: string): boolean {
  if (!selectedRarities.value.includes(rarityKey)) return false
  if (!includeMaxed.value && isWeaponMaxed(entry.weapon_id)) return false
  if (onlyIncludedInCalculation.value && entry.include_in_calculation === false) return false
  return true
}

function toLevels(entry: TreasureMatrixEntry): [number, number, number] {
  return [
    Math.min(entry.affix1_level, AFFIX_MAX_LEVEL[0]),
    Math.min(entry.affix2_level, AFFIX_MAX_LEVEL[1]),
    Math.min(entry.affix3_level, AFFIX_MAX_LEVEL[2]),
  ]
}

const weaponCards = computed<ExportCard[]>(() => {
  const entries = treasureMatrix.value.filter((entry) => {
    if (isCustomEntry(entry.weapon_id)) return false
    // 丢弃静态数据里已不存在的武器，避免画出空白卡
    const weapon = weaponsMap.value.get(entry.weapon_id)
    if (!weapon) return false
    return matchesFilters(entry, String(weapon.rarity))
  })

  return entries
    .toSorted((a, b) => {
      const priorityDiff = getWeaponPriority(b.weapon_id) - getWeaponPriority(a.weapon_id)
      if (priorityDiff !== 0) return priorityDiff
      const rarityDiff =
        (weaponsMap.value.get(b.weapon_id)?.rarity ?? 0) -
        (weaponsMap.value.get(a.weapon_id)?.rarity ?? 0)
      if (rarityDiff !== 0) return rarityDiff
      return a.weapon_id.localeCompare(b.weapon_id)
    })
    .map((entry) => ({
      kind: 'weapon' as const,
      name: weaponsMap.value.get(entry.weapon_id)?.name ?? entry.weapon_name,
      iconUrl: getItemIconUrl(entry.weapon_id) ?? null,
      essenceBgUrl: matrixIcons.value.essenceBg,
      skillIconUrl: resolveSkillIconUrl(entry.weapon_id),
      tierColor: getItemTierColor(entry.weapon_id).hex(),
      levels: toLevels(entry),
      maxed: isWeaponMaxed(entry.weapon_id),
      badgeCount: showBadges.value ? essenceCounts.value[entry.weapon_id] : undefined,
    }))
})

const customCards = computed<ExportCard[]>(() =>
  treasureMatrix.value
    .filter((entry) => isCustomEntry(entry.weapon_id) && matchesFilters(entry, CUSTOM_RARITY_KEY))
    .map((entry) => ({
      kind: 'custom' as const,
      name: resolveCustomName(entry),
      iconUrl: null,
      essenceBgUrl: matrixIcons.value.essenceBg,
      skillIconUrl: resolveSkillIconUrl(entry.weapon_id),
      tierColor: CUSTOM_TIER_COLOR,
      levels: toLevels(entry),
      maxed: isWeaponMaxed(entry.weapon_id),
    })),
)

const totalCount = computed(() => weaponCards.value.length + customCards.value.length)

/**
 * 从当前 Vuetify 主题取出绘制需要的颜色，canvas 读不到 CSS 变量。
 *
 * 必须走 computedThemes 而不是 current：v-app 会调用 provideTheme，
 * 而它把 current 指向未经计算的原始 themes（vuetify theme.js:375），
 * 那里没有自动生成的 on-* 系列颜色，取出来会是 undefined。
 */
function currentTheme(): ExportTheme {
  const colors = theme.computedThemes.value[theme.name.value]!.colors
  return {
    primary: colors.primary!,
    onPrimary: colors['on-primary']!,
    background: colors.background!,
    surface: colors.surface!,
    onSurface: colors['on-surface']!,
  }
}

function releasePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  previewBlob.value = null
  renderInfo.value = null
}

/** 拉取扫描数量；失败不阻断导出，角标退化为关闭 */
async function loadEssenceCounts() {
  try {
    const res = await fetch('/api/weapon_essence_counts')
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
    const result = await res.json()
    essenceCounts.value = result.counts ?? {}
  } catch (error) {
    essenceCounts.value = {}
    toast.reportError('获取扫描数量失败', error)
  }
  // 有数据才默认打开，否则用户会看到一个"打开了却什么也没变"的开关
  showBadges.value = Object.values(essenceCounts.value).some((count) => count > 0)
}

async function regenerate() {
  if (totalCount.value === 0) {
    releasePreview()
    return
  }

  const token = ++renderToken
  rendering.value = true
  try {
    const result = await renderMatrixExport({
      weapons: weaponCards.value,
      customs: customCards.value,
      title: `${activeProfileName.value} · 宝藏基质`,
      subtitle: `${new Date().toLocaleString('zh-CN')} · 共 ${totalCount.value} 项`,
      theme: currentTheme(),
    })

    // 期间又触发了新一轮渲染，丢弃这次的结果
    if (token !== renderToken) {
      URL.revokeObjectURL(result.objectUrl)
      return
    }

    releasePreview()
    previewUrl.value = result.objectUrl
    previewBlob.value = result.blob
    renderInfo.value = {
      width: result.width,
      height: result.height,
      scale: result.scale,
      sizeText: `${Math.round(result.blob.size / 1024)} KB`,
    }
    if (result.missingImages > 0) {
      toast.warning(`${result.missingImages} 个图标加载失败，已用占位图代替`)
    }
  } catch (error) {
    if (token === renderToken) releasePreview()
    toast.reportError('生成导出图片失败', error)
  } finally {
    if (token === renderToken) rendering.value = false
  }
}

/** 防抖重绘：筛选项连点时只跑最后一次 */
function scheduleRegenerate() {
  clearTimeout(redrawTimer)
  redrawTimer = setTimeout(() => void regenerate(), 200)
}

async function copyToClipboard() {
  const blob = previewBlob.value
  if (!blob) return

  if (typeof ClipboardItem === 'undefined' || !navigator.clipboard?.write) {
    toast.error('当前环境不支持写入剪贴板，请改用「保存并打开文件夹」')
    return
  }

  copying.value = true
  try {
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    toast.success('已复制到剪贴板')
  } catch (error) {
    toast.reportError('复制到剪贴板失败', error)
  } finally {
    copying.value = false
  }
}

/** 把 Blob 转成不含前缀的 base64；大图不能用 fromCharCode 展开，会爆调用栈 */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      const dataUrl = reader.result as string
      resolve(dataUrl.slice(dataUrl.indexOf(',') + 1))
    })
    reader.addEventListener('error', () => reject(reader.error))
    reader.readAsDataURL(blob)
  })
}

async function saveToDisk() {
  const blob = previewBlob.value
  if (!blob) return

  saving.value = true
  try {
    const res = await fetch('/api/export/treasure_matrix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: await blobToBase64(blob),
        open_folder: true,
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
    const data = await res.json()
    if (!data.success) throw new Error(data.message)
    toast.success(`已保存到 ${data.file_path}`)
  } catch (error) {
    toast.reportError('保存导出图片失败', error)
  } finally {
    saving.value = false
  }
}

watch(open, (opened) => {
  if (opened) {
    void loadEssenceCounts().then(regenerate)
  } else {
    clearTimeout(redrawTimer)
    releasePreview()
  }
})

watch(
  [selectedRarities, includeMaxed, onlyIncludedInCalculation, showBadges, treasureMatrix],
  () => {
    if (open.value) scheduleRegenerate()
  },
  { deep: true },
)

onUnmounted(() => {
  clearTimeout(redrawTimer)
  releasePreview()
})
</script>

<style lang="scss" scoped>
.export-preview {
  display: block;
  width: 100%;
  max-height: 52vh;
  object-fit: contain;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 8px;
}
</style>
