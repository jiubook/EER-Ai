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
  priority?: number
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
    'custom': boolean
  }
  weapon_priorities?: Record<string, number>
  switch_display_mode?: 'chip' | 'dot' | 'off'
}

export interface ProfileCollection {
  version: number
  active_profile: string
  profiles: Record<string, ProfileData>
}

interface FarmingRecommendation {
  weapon_id: string
  weapon_name: string
  current_levels: [number, number, number]
  target_levels: [number, number, number]
  total_expected_runs: number
  total_expected_essences: number
  affix_results: Array<{
    affix_name: string
    current_level: number
    target_level: number
    expected_attempts: number
    expected_essences_consumed: number
    expected_grease_gained: number
    expected_grease_used: number
    steps: Array<{
      from_level: number
      to_level: number
      success_prob: number
      grease_threshold: number
      expected_attempts: number
      expected_essences: number
      expected_grease_gained: number
      expected_grease_used: number
    }>
  }>
}

interface BatchFarmingItemResult {
  weapon_id: string
  recommendation: FarmingRecommendation | null
  error: string | null
}

const collection = ref<ProfileCollection>({
  version: 1,
  active_profile: 'default',
  profiles: {},
})

const isLoaded = ref(false)

/** 最近一次操作错误信息（供 UI 展示） */
const lastError = ref<string | null>(null)

function applyActiveProfile(profile: ProfileData) {
  const activeName = collection.value.active_profile
  const profileName = profile.name || activeName

  // 写操作接口已经返回最新 ProfileData；直接更新本地账号快照，避免再拉取整份 profiles。
  collection.value = {
    ...collection.value,
    active_profile: profileName,
    profiles: {
      ...collection.value.profiles,
      [profileName]: profile,
    },
  }
  isLoaded.value = true
  lastError.value = null
}

function _handleError(context: string, error: unknown): never {
  const message = error instanceof Error ? error.message : String(error)
  const fullMessage = `${context}: ${message}`
  // 生产环境使用统一的错误上报，而非 console.error
  lastError.value = fullMessage
  throw error instanceof Error ? error : new Error(fullMessage)
}

async function parseJsonResponse<T>(res: Response, fallbackMessage: string): Promise<T> {
  const text = await res.text()
  let body: unknown = null

  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body
      ? String((body as { detail?: unknown }).detail)
      : typeof body === 'string' && body
        ? body
        : fallbackMessage
    throw new Error(detail)
  }

  return body as T
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
      collection.value = await parseJsonResponse<ProfileCollection>(res, '获取账号列表失败')
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
        await parseJsonResponse<never>(res, 'Failed to switch profile')
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
        await parseJsonResponse<never>(res, 'Failed to rename profile')
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
        await parseJsonResponse<never>(res, 'Failed to delete profile')
      }
      await fetchProfiles()
    } catch (error) {
      _handleError('删除账号失败', error)
    }
  }

  async function clearProfileData(name?: string) {
    try {
      const res = await fetch('/api/profiles/clear_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(name === undefined ? {} : { name }),
      })
      if (!res.ok) {
        await parseJsonResponse<never>(res, 'Failed to clear profile data')
      }
      // 重新同步整份 collection：避免 applyActiveProfile 把 active_profile 误改成
      // 被清空的账号，并刷新 treasureMatrix/activeProfile 等派生计算属性。
      await fetchProfiles()
    } catch (error) {
      _handleError('清空账号数据失败', error)
    }
  }

  async function updateTreasureMatrix(entries: TreasureMatrixEntry[]) {
    try {
      const res = await fetch('/api/profiles/treasure_matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries }),
      })
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to update treasure matrix'))
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
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to add treasure matrix entry'))
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
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to remove treasure matrix entry'))
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
      const itemResults = await parseJsonResponse<BatchFarmingItemResult[]>(
        res,
        'Failed to get farming recommendations',
      )
      const failed = itemResults.filter((item) => item.error)
      if (failed.length > 0) {
        lastError.value = failed
          .map((item) => `${item.weapon_id}: ${item.error}`)
          .join('\n')
      } else {
        lastError.value = null
      }
      const recommendations = itemResults
        .map((item) => item.recommendation)
        .filter((item): item is FarmingRecommendation => item !== null)
      if (recommendations.length === 0 && failed.length > 0) {
        throw new Error(lastError.value ?? 'Failed to get farming recommendations')
      }
      return recommendations
    } catch (error) {
      _handleError('批量获取刷取建议失败', error)
    }
  }

  async function updateWeaponOverviewFilters(filters: {
    '3star': boolean
    '4star': boolean
    '5star': boolean
    '6star': boolean
    'custom': boolean
  }) {
    try {
      const res = await fetch('/api/profiles/weapon_overview_filters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters }),
      })
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to update weapon overview filters'))
    } catch (error) {
      _handleError('更新武器总览过滤器失败', error)
    }
  }

  async function updateSwitchDisplayMode(mode: 'chip' | 'dot' | 'off') {
    try {
      const res = await fetch('/api/profiles/switch_display_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to update switch display mode'))
    } catch (error) {
      _handleError('更新可切换提示显示模式失败', error)
    }
  }

  async function updateWeaponPriority(weaponId: string, priority: number) {
    try {
      const res = await fetch('/api/profiles/weapon_priority', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weapon_id: weaponId, priority }),
      })
      applyActiveProfile(await parseJsonResponse<ProfileData>(res, 'Failed to update weapon priority'))
    } catch (error) {
      _handleError('更新武器优先级失败', error)
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
    clearProfileData,
    updateTreasureMatrix,
    addTreasureMatrixEntry,
    removeTreasureMatrixEntry,
    getBatchFarmingRecommendations,
    updateWeaponOverviewFilters,
    updateSwitchDisplayMode,
    updateWeaponPriority,
  }
}
