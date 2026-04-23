/**
 * Profile management composable.
 *
 * Manages multi-account profiles with their treasure matrix configurations.
 */

import { computed, ref } from 'vue'

export interface TreasureMatrixEntry {
  weapon_id: string
  weapon_name: string
  affix1_level: number
  affix2_level: number
  affix3_level: number
}

export interface ProfileData {
  version: number
  name: string
  treasure_matrix: TreasureMatrixEntry[]
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
    } catch (error) {
      console.error('Failed to fetch profiles:', error)
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
      console.error('Failed to switch profile:', error)
      throw error
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
      console.error('Failed to rename profile:', error)
      throw error
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
      console.error('Failed to delete profile:', error)
      throw error
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
      console.error('Failed to update treasure matrix:', error)
      throw error
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
      console.error('Failed to add treasure matrix entry:', error)
      throw error
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
      console.error('Failed to remove treasure matrix entry:', error)
      throw error
    }
  }

  async function getFarmingRecommendation(
    weaponId: string,
    currentLevels: [number, number, number],
    targetLevels: [number, number, number],
  ) {
    try {
      const res = await fetch('/api/profiles/farming_recommendation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          weapon_id: weaponId,
          current_levels: currentLevels,
          target_levels: targetLevels,
        }),
      })
      if (!res.ok) throw new Error('Failed to get farming recommendation')
      return await res.json()
    } catch (error) {
      console.error('Failed to get farming recommendation:', error)
      throw error
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
      return await res.json()
    } catch (error) {
      console.error('Failed to get farming recommendations:', error)
      throw error
    }
  }

  return {
    collection,
    isLoaded,
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
    getFarmingRecommendation,
    getBatchFarmingRecommendations,
  }
}
