/**
 * 重合检测组合式函数。
 *
 * 检测自定义基质与内置武器的重合并处理。
 */

import type { TreasureMatrixEntry } from '@/composables/useProfiles'
import type { CustomStat } from '@/utils/gameData/weapon'
import { ref } from 'vue'
import { useProfiles } from '@/composables/useProfiles'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'

export interface OverlapItem {
  customIndex: number
  customName: string
  customWeaponId: string
  matchedWeaponId: string
  matchedWeaponName: string
  action: 'ignore' | 'suppress' | 'switch' | 'delete'
}

/** 重合检测的物品列表（模块级单例，所有调用方共享同一份状态） */
const overlapItems = ref<OverlapItem[]>([])

/** 重合检测弹窗是否显示 */
const overlapDialog = ref(false)

/** 重合检测的等级比较结果（按 overlapItems 索引缓存） */
const overlapCompareResults = ref<Map<number, number>>(new Map())

export function useOverlapDetection() {
  const { updateTreasureMatrix } = useProfiles()
  const { weaponsMap, essencesMap } = useStaticData()

  /**
   * 将自定义宝藏基质配置保存到后端
   */
  async function postCustomStatsUpdate(stats: CustomStat[]) {
    const getRes = await fetch('/api/config')
    if (!getRes.ok) {
      throw new Error(`HTTP ${getRes.status}: ${getRes.statusText}`)
    }
    const currentConfig = await getRes.json()
    currentConfig.treasure_essence_stats = stats
    const postRes = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig),
    })
    if (!postRes.ok) {
      throw new Error(`HTTP ${postRes.status}: ${postRes.statusText}`)
    }
  }

  /**
   * 检查自定义基质与内置武器的词条重合
   * 匹配规则：三个槽位完全相等（含 null 对 null）
   * 检查范围：所有 config 中配置的自定义基质，无论是否在 profiles 中拥有
   */
  function checkCustomOverlap(customStats: CustomStat[], matrixEntryByWeaponId: ReadonlyMap<string, TreasureMatrixEntry>) {
    const items: OverlapItem[] = []
    for (const [i, stat] of customStats.entries()) {
      if (!stat) continue
      // 跳过已勾选"不再提示"的
      if (stat.no_prompt_switch) continue
      // 跳过属性全为空的条目（已被切换清空）
      if (!stat.attribute && !stat.secondary && !stat.skill) continue

      const syntheticId = `custom_stat_${i}`

      // 遍历所有内置武器，查找三词条完全匹配
      for (const [weaponId, weapon] of weaponsMap.value.entries()) {
        if (
          weapon.attributeStatId === stat.attribute &&
          weapon.secondaryStatId === stat.secondary &&
          weapon.skillStatId === stat.skill
        ) {
          items.push({
            customIndex: i,
            customName: stat.name || `自定义基质 ${i + 1}`,
            customWeaponId: syntheticId,
            matchedWeaponId: weaponId,
            matchedWeaponName: weapon.name,
            action: 'ignore',
          })
        }
      }
    }
    if (items.length === 0) return
    overlapItems.value = items
    overlapDialog.value = true
    fetchOverlapCompareResults({
      matrixEntryByWeaponId,
      customStats,
    })
  }

  /**
   * 从后端批量获取重合检测的等级比较结果
   */
  async function fetchOverlapCompareResults(params: {
    matrixEntryByWeaponId: ReadonlyMap<string, TreasureMatrixEntry>
    customStats: CustomStat[]
  }) {
    const { matrixEntryByWeaponId, customStats } = params
    if (overlapItems.value.length === 0) return

    try {
      const results = new Map<number, number>()
      const res = await fetch('/api/profiles/compare_levels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: overlapItems.value.map((item) => {
            const customEntry = matrixEntryByWeaponId.get(item.customWeaponId)
            const matchedEntry = matrixEntryByWeaponId.get(item.matchedWeaponId)
            return {
              current_levels: [
                customEntry?.affix1_level ?? 0,
                customEntry?.affix2_level ?? 0,
                customEntry?.affix3_level ?? 0,
              ],
              existing_levels: [
                matchedEntry?.affix1_level ?? 0,
                matchedEntry?.affix2_level ?? 0,
                matchedEntry?.affix3_level ?? 0,
              ],
              stat_types: resolveStatTypes(item.customWeaponId, customStats),
            }
          }),
        }),
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }
      const data = await res.json()
      for (let i = 0; i < overlapItems.value.length; i++) {
        results.set(i, data.results?.[i] ?? 0)
      }
      overlapCompareResults.value = results
    } catch (error) {
      console.error('获取等级比较结果失败:', error)
    }
  }

  /**
   * 解析武器 ID 对应的三个槽位词条类型
   * 返回 ["ATTRIBUTE", "SECONDARY", "SKILL"] 或对应的 null
   */
  function resolveStatTypes(weaponId: string, customStats: CustomStat[]): (string | null)[] {
    if (weaponId.startsWith('custom_stat_')) {
      const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
      const stat = customStats[index]
      return [
        stat?.attribute ? essencesMap.value.get(stat.attribute)?.type ?? null : null,
        stat?.secondary ? essencesMap.value.get(stat.secondary)?.type ?? null : null,
        stat?.skill ? essencesMap.value.get(stat.skill)?.type ?? null : null,
      ]
    }
    const weapon = weaponsMap.value.get(weaponId)
    return [
      weapon?.attributeStatId ? 'ATTRIBUTE' : null,
      weapon?.secondaryStatId ? 'SECONDARY' : null,
      weapon?.skillStatId ? 'SKILL' : null,
    ]
  }

  /**
   * 获取预计算的比较结果：1（自定义更优）/ 0（相等）/ -1（内置更优）
   */
  function getOverlapCompareResult(item: OverlapItem): number {
    const idx = overlapItems.value.indexOf(item)
    return overlapCompareResults.value.get(idx) ?? 0
  }

  /**
   * 一键选择：根据比较结果自动选择动作
   */
  function autoSelectOverlap() {
    for (let i = 0; i < overlapItems.value.length; i++) {
      const item = overlapItems.value[i]
      if (!item) continue
      const cmp = overlapCompareResults.value.get(i) ?? 0
      if (cmp < 0) {
        item.action = 'delete'   // 自定义更小 → 删除自定义
      } else if (cmp === 0) {
        item.action = 'ignore'   // 相等 → 忽略
      } else {
        item.action = 'switch'   // 自定义更大 → 切换到内置
      }
    }
  }

  /**
   * 获取重合检测中某个武器 ID 的属性词条文本（含等级）
   */
  function getOverlapTooltipText(weaponId: string, params: {
    matrixEntryByWeaponId: ReadonlyMap<string, TreasureMatrixEntry>
    customStats: CustomStat[]
  }): string {
    const { matrixEntryByWeaponId, customStats } = params
    const entry = matrixEntryByWeaponId.get(weaponId)
    const levels: [number, number, number] = [
      entry?.affix1_level ?? 0,
      entry?.affix2_level ?? 0,
      entry?.affix3_level ?? 0,
    ]

    let statIds: (string | null)[] = []
    if (weaponId.startsWith('custom_stat_')) {
      const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
      const stat = customStats[index]
      statIds = [stat?.attribute ?? null, stat?.secondary ?? null, stat?.skill ?? null]
    } else {
      const weapon = weaponsMap.value.get(weaponId)
      statIds = [weapon?.attributeStatId ?? null, weapon?.secondaryStatId ?? null, weapon?.skillStatId ?? null]
    }

    const parts: string[] = []
    for (let i = 0; i < 3; i++) {
      const sid = statIds[i]
      if (sid) {
        parts.push(`${getGemTagName(sid)} Lv.${levels[i]}`)
      }
    }
    return parts.join('、') || '无属性'
  }

  /**
   * 确认重合操作
   */
  async function confirmOverlapActions(params: {
    customStats: CustomStat[]
    treasureMatrix: TreasureMatrixEntry[]
    matrixEntryByWeaponId: ReadonlyMap<string, TreasureMatrixEntry>
  }) {
    const { customStats, matrixEntryByWeaponId, treasureMatrix } = params

    // 记录需要删除的自定义基质索引
    const indicesToDelete: number[] = []
    // 记录是否有 suppress 操作需要更新配置
    let hasSuppress = false

    // 第一轮：收集所有修改，不修改本地状态
    for (const item of overlapItems.value) {
      if (item.action === 'ignore') continue

      const stat = customStats[item.customIndex]
      if (!stat) continue

      if (item.action === 'suppress') {
        hasSuppress = true
      }

      if (item.action === 'switch' || item.action === 'delete') {
        indicesToDelete.push(item.customIndex)
      }
    }

    // 从大到小排序删除，避免索引偏移问题
    indicesToDelete.sort((a, b) => b - a)

    // 构建新的 treasure_matrix（一次性完成所有 switch 和 delete 操作）
    const toRemove = new Set(
      overlapItems.value
        .filter((i) => i.action === 'switch' || i.action === 'delete')
        .map((i) => i.customWeaponId),
    )
    let newTreasureMatrix = treasureMatrix.filter((e) => !toRemove.has(e.weapon_id))

    // 处理 switch 操作：追加内置武器条目
    for (const item of overlapItems.value) {
      if (item.action !== 'switch') continue

      const entry = matrixEntryByWeaponId.get(item.customWeaponId)
      if (entry) {
        const weapon = weaponsMap.value.get(item.matchedWeaponId)
        newTreasureMatrix.push({
          weapon_id: item.matchedWeaponId,
          weapon_name: weapon?.name || item.matchedWeaponName,
          affix1_level: entry.affix1_level,
          affix2_level: entry.affix2_level,
          affix3_level: entry.affix3_level,
          include_in_calculation: entry.include_in_calculation ?? true,
        })
      }
    }

    // 准备新的 config 数据（不修改本地状态）
    let tempStats = [...customStats]
    for (const index of indicesToDelete) {
      tempStats = tempStats.filter((_, i) => i !== index)
    }

    // 更新 suppress 标记
    if (hasSuppress) {
      for (const item of overlapItems.value) {
        if (item.action === 'suppress' && tempStats[item.customIndex]) {
          const stat = tempStats[item.customIndex]!
          tempStats[item.customIndex] = { ...stat, no_prompt_switch: true }
        }
      }
    }

    // 更新 treasure_matrix 中所有引用后续自定义基质的索引
    if (indicesToDelete.length > 0) {
      newTreasureMatrix = newTreasureMatrix.map((e) => {
        if (e.weapon_id.startsWith('custom_stat_')) {
          const currentIndex = Number.parseInt(e.weapon_id.replace('custom_stat_', ''), 10)
          // 计算删除后的新索引
          let newIndex = currentIndex
          for (const deletedIndex of indicesToDelete) {
            if (currentIndex > deletedIndex) {
              newIndex--
            }
          }
          if (newIndex !== currentIndex) {
            return { ...e, weapon_id: `custom_stat_${newIndex}` }
          }
        }
        return e
      })
    }

    // 第二轮：一次性提交所有修改到后端
    if (indicesToDelete.length > 0) {
      await updateTreasureMatrix(newTreasureMatrix)
    }
    if (hasSuppress || indicesToDelete.length > 0) {
      await postCustomStatsUpdate(tempStats)
    }

    return { indicesToDelete, hasSuppress, tempStats }
  }

  return {
    // 状态
    overlapItems,
    overlapDialog,
    overlapCompareResults,

    // 检测方法
    checkCustomOverlap,
    fetchOverlapCompareResults,
    getOverlapCompareResult,
    autoSelectOverlap,
    getOverlapTooltipText,

    // 操作方法
    confirmOverlapActions,
  }
}
