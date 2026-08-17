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
          <!-- 单向绑定：勾选「自定义」时要先弹确认，双向绑定拦不住这次点击 -->
          <v-chip-group
            column
            :model-value="selectedRarities"
            multiple
            @update:model-value="onRaritySelectionChange"
          >
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
            v-model="includeUnowned"
            color="primary"
            density="compact"
            :disabled="onlyIncludedInCalculation"
            hide-details
            label="未获得的武器/基质"
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
          未获得的条目按 0/6·0/6·0/3
          置灰展示；角标来自本次运行的扫描结果，重启后清零，自定义基质无对应数据。
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

  <!-- 自定义基质可能有几百枚，一次全画会卡住界面，开启前先确认 -->
  <v-dialog v-model="showCustomConfirm" max-width="460">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="warning">mdi-alert-outline</v-icon>
        加入自定义基质
      </v-card-title>
      <v-card-text>
        当前配置中有 {{ customStats.length }} 枚自定义基质。
        <br />
        全部绘制会长时间占用主线程，数量多时界面可能明显卡顿甚至短暂无响应。确认加入导出？
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showCustomConfirm = false">取消</v-btn>
        <v-btn color="warning" variant="flat" @click="confirmIncludeCustom">确认加入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import type { TreasureMatrixEntry } from '@/composables/useProfiles'
import type { ExportCard } from '@/utils/matrixExport'
import { computed, onUnmounted, ref, watch } from 'vue'
import { useCustomStats } from '@/composables/useCustomStats'
import { useProfiles } from '@/composables/useProfiles'
import { useToast } from '@/composables/useToast'
import { AFFIX_MAX_LEVEL, useWeaponStats } from '@/composables/useWeaponStats'
import { getItemIconUrl, getItemTierColor } from '@/utils/gameData/item'
import { useStaticData } from '@/utils/gameData/staticData'
import {
  fallbackCustomStatName,
  findCustomStat,
  getGemTagName,
  getStatsForWeapon,
  toCustomStatId,
} from '@/utils/gameData/weapon'
import { renderMatrixExport } from '@/utils/matrixExport'

const open = defineModel<boolean>({ default: false })

const toast = useToast()
const { activeProfileName, treasureMatrix } = useProfiles()
const { customStats } = useCustomStats()
const { isCustomEntry, isWeaponMaxed, isWeaponOwned } = useWeaponStats()
const { weaponsMap, weaponTypes, matrixIcons } = useStaticData()

/** 自定义基质在导出图里按 6★ 处理，与页面筛选口径一致 */
const CUSTOM_RARITY_KEY = 'custom'
/** 自定义基质卡片的底部色条 */
const CUSTOM_TIER_COLOR = '#ff7100'
/** 未获得条目的词条等级：三条全为 0 */
const UNOWNED_LEVELS = [0, 0, 0] as const

// 自定义基质默认不勾选：批量添加之后配置里可能有几百枚，
// 默认全画出来会让弹窗一打开就卡住。
const selectedRarities = ref<string[]>(['3', '4', '5', '6'])
const includeMaxed = ref(true)
const includeUnowned = ref(true)
const onlyIncludedInCalculation = ref(false)
const showBadges = ref(false)
const showCustomConfirm = ref(false)

/** 等待用户确认时暂存的目标选择，确认后才写回 selectedRarities */
let pendingRarities: string[] = []

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

/**
 * 获取武器的三词条中文名。
 *
 * 自定义基质从配置里读取，内置武器从静态数据读取；
 * 返回 ["攻击", "终结技充能效率", "巧技"] 这样的数组。
 */
function getTraitNames(weaponId: string): string[] {
  // 自定义基质：从配置中读取
  if (isCustomEntry(weaponId)) {
    const found = findCustomStat(weaponId, customStats.value)
    if (!found) return []
    const stat = found.stat
    const parts: string[] = []
    if (stat.attribute) parts.push(getGemTagName(stat.attribute))
    if (stat.secondary) parts.push(getGemTagName(stat.secondary))
    if (stat.skill) parts.push(getGemTagName(stat.skill))
    return parts
  }

  // 内置武器：从静态数据读取
  const stats = getStatsForWeapon(weaponId)
  const parts: string[] = []
  if (stats.attribute) parts.push(getGemTagName(stats.attribute))
  if (stats.secondary) parts.push(getGemTagName(stats.secondary))
  if (stats.skill) parts.push(getGemTagName(stats.skill))
  return parts
}

/**
 * 星级 chip 的选择变更入口。
 *
 * 勾选「自定义」时先弹确认再生效：确认前 selectedRarities 保持不变，
 * chip 也就不会亮起来，取消/ESC/点遮罩都无需额外回滚。
 */
function onRaritySelectionChange(value: unknown) {
  const next = value as string[]
  if (next.includes(CUSTOM_RARITY_KEY) && !selectedRarities.value.includes(CUSTOM_RARITY_KEY)) {
    pendingRarities = next
    showCustomConfirm.value = true
    return
  }
  selectedRarities.value = next
}

function confirmIncludeCustom() {
  selectedRarities.value = pendingRarities
  showCustomConfirm.value = false
}

/** 已获得条目要额外过的两个开关；星级筛选在各自的 computed 里判断 */
function passesToggles(entry: TreasureMatrixEntry): boolean {
  if (!includeMaxed.value && isWeaponMaxed(entry.weapon_id)) return false
  if (onlyIncludedInCalculation.value && entry.include_in_calculation === false) return false
  return true
}

/** 是否绘制未获得的条目：「仅导出参与计算」开启时它们本就不参与计算，一律排除 */
const showUnowned = computed(() => includeUnowned.value && !onlyIncludedInCalculation.value)

function toLevels(entry: TreasureMatrixEntry): [number, number, number] {
  return [
    Math.min(entry.affix1_level, AFFIX_MAX_LEVEL[0]),
    Math.min(entry.affix2_level, AFFIX_MAX_LEVEL[1]),
    Math.min(entry.affix3_level, AFFIX_MAX_LEVEL[2]),
  ]
}

/**
 * weapon_id → 所属武器类型的 sortOrder。
 *
 * 后端已按 sortOrder 排好（单手剑→双手剑→长柄武器→手铳→施术单元），
 * 这里仍显式读 sortOrder 而不是数组下标，接口顺序万一变了也不会静默错位。
 */
const weaponTypeOrder = computed(() => {
  const order = new Map<string, number>()
  for (const weaponType of weaponTypes.value) {
    for (const weaponId of weaponType.weaponIds) {
      order.set(weaponId, weaponType.sortOrder)
    }
  }
  return order
})

/**
 * 内置武器区的卡片。
 *
 * 排序：武器类型（单手剑→…→施术单元）→ 稀有度降序（6★→3★）→ id 升序。
 * 已获得与未获得走同一条序列，未获得的穿插在已获得之间而不是堆在最后。
 * 只遍历静态数据里的武器，账号里指向已下线 ID 的条目自然被丢弃，避免画出空白卡。
 */
const weaponCards = computed<ExportCard[]>(() => {
  const entryByWeaponId = new Map(
    treasureMatrix.value.map((entry) => [entry.weapon_id, entry] as const),
  )
  const weapons = [...weaponsMap.value.values()].toSorted((a, b) => {
    // 不属于任何类型的武器（类型数据缺失时）沉到最末尾
    const typeA = weaponTypeOrder.value.get(a.id) ?? Number.POSITIVE_INFINITY
    const typeB = weaponTypeOrder.value.get(b.id) ?? Number.POSITIVE_INFINITY
    if (typeA !== typeB) return typeA - typeB
    if (a.rarity !== b.rarity) return b.rarity - a.rarity
    return a.id.localeCompare(b.id)
  })

  const cards: ExportCard[] = []
  for (const weapon of weapons) {
    if (!selectedRarities.value.includes(String(weapon.rarity))) continue

    const entry = entryByWeaponId.get(weapon.id)
    if (entry ? !passesToggles(entry) : !showUnowned.value) continue

    cards.push({
      kind: 'weapon',
      name: weapon.name,
      nameRuby: '★'.repeat(weapon.rarity),
      iconUrl: getItemIconUrl(weapon.id) ?? null,
      essenceBgUrl: matrixIcons.value.essenceBg,
      skillIconUrl: resolveSkillIconUrl(weapon.id),
      tierColor: getItemTierColor(weapon.id).hex(),
      levels: entry ? toLevels(entry) : UNOWNED_LEVELS,
      maxed: isWeaponMaxed(weapon.id),
      // 未获得的武器不画角标：扫到的基质还没有落到具体武器上
      badgeCount: entry && showBadges.value ? essenceCounts.value[weapon.id] : undefined,
      traitNames: getTraitNames(weapon.id),
      dimmed: entry === undefined,
    })
  }
  return cards
})

const ownedCustomCards = computed<ExportCard[]>(() => {
  if (!selectedRarities.value.includes(CUSTOM_RARITY_KEY)) return []
  return treasureMatrix.value
    .filter((entry) => isCustomEntry(entry.weapon_id) && passesToggles(entry))
    .map((entry) => ({
      kind: 'custom' as const,
      name: resolveCustomName(entry),
      iconUrl: null,
      essenceBgUrl: matrixIcons.value.essenceBg,
      skillIconUrl: resolveSkillIconUrl(entry.weapon_id),
      tierColor: CUSTOM_TIER_COLOR,
      levels: toLevels(entry),
      maxed: isWeaponMaxed(entry.weapon_id),
      traitNames: getTraitNames(entry.weapon_id),
    }))
})

/** 未获得的自定义基质：配置里有、但账号里没写入 treasure_matrix 的那些 */
const unownedCustomCards = computed<ExportCard[]>(() => {
  if (!selectedRarities.value.includes(CUSTOM_RARITY_KEY) || !showUnowned.value) return []

  return customStats.value
    .map((stat, index) => ({
      weaponId: toCustomStatId(stat),
      name: stat.name || fallbackCustomStatName(index),
    }))
    .filter((item) => !isWeaponOwned(item.weaponId))
    .map((item) => ({
      kind: 'custom' as const,
      name: item.name,
      iconUrl: null,
      essenceBgUrl: matrixIcons.value.essenceBg,
      skillIconUrl: resolveSkillIconUrl(item.weaponId),
      tierColor: CUSTOM_TIER_COLOR,
      levels: UNOWNED_LEVELS,
      maxed: false,
      traitNames: getTraitNames(item.weaponId),
      dimmed: true,
    }))
})

const customCards = computed<ExportCard[]>(() => [
  ...ownedCustomCards.value,
  ...unownedCustomCards.value,
])

const totalCount = computed(() => weaponCards.value.length + customCards.value.length)

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
      // 条目数由绘制模块自己从卡片数量算，这里只给归档时间
      subtitle: new Date().toLocaleString('zh-CN'),
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
  [
    selectedRarities,
    includeMaxed,
    includeUnowned,
    onlyIncludedInCalculation,
    showBadges,
    treasureMatrix,
  ],
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
