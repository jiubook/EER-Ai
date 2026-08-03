/**
 * 自定义基质管理组合式函数。
 *
 * 管理自定义基质的 CRUD 操作，包括获取、保存、删除等。
 */

import type { TreasureMatrixEntry } from '@/composables/useProfiles'
import type { CustomStat } from '@/utils/gameData/weapon'
import { computed, ref } from 'vue'
import { useProfiles } from '@/composables/useProfiles'
import { useWeaponStats } from '@/composables/useWeaponStats'
import { useStaticData } from '@/utils/gameData/staticData'

/** 自定义宝藏基质属性配置列表（模块级单例，所有调用方共享同一份状态） */
const customStats = ref<CustomStat[]>([])

export function useCustomStats() {
  const {
    updateTreasureMatrix,
    addTreasureMatrixEntry,
    removeTreasureMatrixEntry,
    updateWeaponPriority,
  } = useProfiles()
  const { weaponsMap } = useStaticData()
  const { isWeaponOwned, isCustomEntry } = useWeaponStats()

  /** 自定义基质条目列表，用于武器总览展示 */
  const customMatrixEntries = computed(() => {
    return customStats.value
      .map((stat, index) => ({
        syntheticId: `custom_stat_${index}`,
        displayName: stat.name || `自定义基质 ${index + 1}`,
        index,
        skillStatId: stat.skill,
      }))
  })

  /**
   * 从后端获取配置中的自定义宝藏基质属性列表
   */
  async function fetchCustomStats() {
    try {
      const res = await fetch('/api/config')
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }
      const config = await res.json()
      customStats.value = config.treasure_essence_stats || []
    } catch (error) {
      console.error('获取自定义宝藏基质配置失败:', error)
    }
  }

  /**
   * 将自定义宝藏基质配置保存到后端
   */
  async function postCustomStatsUpdate(stats?: CustomStat[]) {
    const getRes = await fetch('/api/config')
    if (!getRes.ok) {
      throw new Error(`HTTP ${getRes.status}: ${getRes.statusText}`)
    }
    const currentConfig = await getRes.json()
    currentConfig.treasure_essence_stats = stats ?? customStats.value
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
   * 保存自定义基质（新建或编辑）
   */
  async function saveCustomEntry(params: {
    weaponId: string
    name: string
    attribute: string | null
    secondary: string | null
    skill: string | null
    affix1: number
    affix2: number
    affix3: number
    priority: number
    isOwned: boolean
    matrixEntryByWeaponId: Map<string, TreasureMatrixEntry>
    treasureMatrix: TreasureMatrixEntry[]
  }) {
    const { weaponId, name, attribute, secondary, skill, affix1, affix2, affix3, priority, isOwned, matrixEntryByWeaponId, treasureMatrix } = params

    if (weaponId === '__new_custom__') {
      // 新建模式：准备新条目数据
      const newEntry: CustomStat = {
        name: name || `自定义基质 ${customStats.value.length + 1}`,
        attribute,
        secondary,
        skill,
      }

      // 先发送请求，成功后再更新本地状态
      const tempStats = [...customStats.value, newEntry]
      await postCustomStatsUpdate(tempStats)

      // 请求成功，更新本地状态
      customStats.value.push(newEntry)

      // 只有标记为"已拥有"时才写入 profile
      if (isOwned) {
        const newIndex = customStats.value.length - 1
        const syntheticId = `custom_stat_${newIndex}`
        await addTreasureMatrixEntry({
          weapon_id: syntheticId,
          weapon_name: name || `自定义基质 ${newIndex + 1}`,
          affix1_level: affix1,
          affix2_level: affix2,
          affix3_level: affix3,
          priority,
          include_in_calculation: true,
        })
      }
    } else if (weaponId.startsWith('custom_stat_')) {
      // 编辑模式：准备更新数据
      const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
      if (customStats.value[index]) {
        const originalEntry = { ...customStats.value[index] }
        const updatedEntry: CustomStat = {
          ...originalEntry,
          name,
          attribute,
          secondary,
          skill,
        }

        // 先发送请求，成功后再更新本地状态
        const tempStats = [...customStats.value]
        tempStats[index] = updatedEntry
        await postCustomStatsUpdate(tempStats)

        // 请求成功，更新本地状态
        customStats.value[index] = updatedEntry
      }

      // 更新 profile 中的等级和优先级
      const entry = matrixEntryByWeaponId.get(weaponId)
      if (entry) {
        const originalEntry = { ...entry }
        entry.weapon_name = name
        entry.affix1_level = affix1
        entry.affix2_level = affix2
        entry.affix3_level = affix3
        entry.priority = priority

        try {
          await updateTreasureMatrix([...treasureMatrix])
          await updateWeaponPriority(weaponId, priority)
        } catch (profileError) {
          // 回滚本地状态
          Object.assign(entry, originalEntry)
          throw profileError
        }
      }
    }

    await fetchCustomStats()
  }

  /**
   * 确认删除自定义基质
   */
  async function confirmDeleteCustomEntry(params: {
    index: number
    treasureMatrix: TreasureMatrixEntry[]
  }) {
    const { index, treasureMatrix } = params
    const targetId = `custom_stat_${index}`

    // 1) 删除目标条目，并将所有索引 > index 的自定义条目前移一位
    const newMatrix = treasureMatrix
      .filter((e) => e.weapon_id !== targetId)
      .map((e) => {
        if (e.weapon_id.startsWith('custom_stat_')) {
          const cur = Number.parseInt(e.weapon_id.replace('custom_stat_', ''), 10)
          if (cur > index) return { ...e, weapon_id: `custom_stat_${cur - 1}` }
        }
        return e
      })

    // 2) 准备新的 config 数据（不修改本地状态）
    const tempStats = customStats.value.filter((_, i) => i !== index)

    // 3) 持久化：先 profile，再 config，最后回读配置
    await updateTreasureMatrix(newMatrix)
    await postCustomStatsUpdate(tempStats)

    // 4) 请求成功，更新本地状态
    customStats.value.splice(index, 1)
    await fetchCustomStats()
  }

  /**
   * 非自定义基质：从基质配置中移除
   */
  async function removeNonCustomEntry(weaponId: string) {
    await removeTreasureMatrixEntry(weaponId)
  }

  /**
   * 切换武器拥有状态（网格右键 / 详情弹窗共用）
   */
  async function toggleWeaponOwnership(weaponId: string) {
    if (isWeaponOwned(weaponId)) {
      await removeTreasureMatrixEntry(weaponId)
    } else {
      // 自定义条目使用配置中的名称，普通武器使用 weaponsMap 中的名称
      let weaponName: string
      if (isCustomEntry(weaponId)) {
        const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
        weaponName = customStats.value[index]?.name || `自定义基质 ${index + 1}`
      } else {
        const weapon = weaponsMap.value.get(weaponId)
        weaponName = weapon?.name || weaponId
      }
      await addTreasureMatrixEntry({
        weapon_id: weaponId,
        weapon_name: weaponName,
        affix1_level: 1,
        affix2_level: 1,
        affix3_level: 1,
        include_in_calculation: true,
      })
    }
  }

  // 导出 updateWeaponPriority 以便外部使用
  return {
    // 状态
    customStats,
    customMatrixEntries,

    // 操作方法
    fetchCustomStats,
    postCustomStatsUpdate,
    saveCustomEntry,
    confirmDeleteCustomEntry,
    removeNonCustomEntry,
    toggleWeaponOwnership,
    updateWeaponPriority,
  }
}
