/**
 * 账号管理组合式函数。
 *
 * 管理多账号及其宝藏基质配置。
 */

import { computed, ref } from 'vue'

export interface TreasureMatrixEntry {
  weapon_id: string
  weapon_name: string
  affix1_level: number
  affix2_level: number
  affix3_level: number
  include_in_calculation?: boolean
}

export interface ProfileData {
  version: number
  name: string
  treasure_matrix: TreasureMatrixEntry[]
  weapon_overview_filters?: {
    '3star': boolean
    '4star': boolean
    '5star': boolean
    '6star': boolean
  }
}

export interface ProfileCollection {
  version: number
  active_profile: string
  profiles: Record<string, ProfileData>
}

const collection = ref<ProfileCollection>({
  version: 1,
  active_profile: 'default',
  profiles: {},
})

const isLoaded = ref(false)

/** 最近一次操作错误信息（供 UI 展示） */
const lastError = ref<string | null>(null)

function _handleError(context: string, error: unknown): never {
  const message = error instanceof Error ? error.message : String(error)
  const fullMessage = `${context}: ${message}`
  // 生产环境使用统一的错误上报，而非 console.error
  lastError.value = fullMessage
  throw error instanceof Error ? error : new Error(fullMessage)
}

export function useProfiles() {
  const activeProfileName = computed(() => collection.value.active_profile)
  const activeProfile = computed(() => {
    const name = collection.value.active_profile
    return collection.value.profiles[name] ?? { version: 1, name, treasure_matrix: [] }
  })
  const profileNames = computed(() => Object.keys(collection.value.profiles))
  const treasureMatrix = computed(() => activeProfile.value.treasure_matrix)

  async function fetchProfiles() {
    try {
      const res = await fetch('/api/profiles')
      const data = await res.json()
      collection.value = data
      isLoaded.value = true
      lastError.value = null
    } catch (error) {
      _handleError('获取账号列表失败', error)
    }
  }

  async function switchProfile(name: string) {
    try {
      const res = await fetch('/api/profiles/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to switch profile')
      }
      await fetchProfiles()
    } catch (error) {
      _handleError('切换账号失败', error)
    }
  }

  async function renameProfile(oldName: string, newName: string) {
    try {
      const res = await fetch('/api/profiles/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_name: oldName, new_name: newName }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to rename profile')
      }
      await fetchProfiles()
    } catch (error) {
      _handleError('重命名账号失败', error)
    }
  }

  async function deleteProfile(name: string) {
    try {
      const res = await fetch('/api/profiles/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to delete profile')
      }
      await fetchProfiles()
    } catch (error) {
      _handleError('删除账号失败', error)
    }
  }

  async function updateTreasureMatrix(entries: TreasureMatrixEntry[]) {
    try {
      const res = await fetch('/api/profiles/treasure_matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries }),
      })
      if (!res.ok) throw new Error('Failed to update treasure matrix')
      await fetchProfiles()
    } catch (error) {
      _handleError('更新宝藏基质失败', error)
    }
  }

  async function addTreasureMatrixEntry(entry: TreasureMatrixEntry) {
    try {
      const res = await fetch('/api/profiles/treasure_matrix/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry),
      })
      if (!res.ok) throw new Error('Failed to add treasure matrix entry')
      await fetchProfiles()
    } catch (error) {
      _handleError('添加宝藏基质条目失败', error)
    }
  }

  async function removeTreasureMatrixEntry(weaponId: string) {
    try {
      const res = await fetch('/api/profiles/treasure_matrix/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weapon_id: weaponId }),
      })
      if (!res.ok) throw new Error('Failed to remove treasure matrix entry')
      await fetchProfiles()
    } catch (error) {
      _handleError('移除宝藏基质条目失败', error)
    }
  }

  async function getBatchFarmingRecommendations(
    items: Array<{
      weapon_id: string
      current_levels: [number, number, number]
      target_levels: [number, number, number]
    }>,
  ) {
    try {
      const res = await fetch('/api/profiles/farming_recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      })
      if (!res.ok) throw new Error('Failed to get farming recommendations')
      lastError.value = null
      return await res.json()
    } catch (error) {
      _handleError('批量获取刷取建议失败', error)
    }
  }

  async function updateWeaponOverviewFilters(filters: {
    '3star': boolean
    '4star': boolean
    '5star': boolean
    '6star': boolean
  }) {
    try {
      const res = await fetch('/api/profiles/weapon_overview_filters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters }),
      })
      if (!res.ok) throw new Error('Failed to update weapon overview filters')
      await fetchProfiles()
    } catch (error) {
      _handleError('更新武器总览过滤器失败', error)
    }
  }

  return {
    collection,
    isLoaded,
    lastError,
    activeProfileName,
    activeProfile,
    profileNames,
    treasureMatrix,
    fetchProfiles,
    switchProfile,
    renameProfile,
    deleteProfile,
    updateTreasureMatrix,
    addTreasureMatrixEntry,
    removeTreasureMatrixEntry,
    getBatchFarmingRecommendations,
    updateWeaponOverviewFilters,
  }
}
