import type {
  EnergyAlluviumInfo,
  EnergyAlluviumListResponse,
  EssenceInfo,
  EssenceListResponse,
  MatrixIconResponse,
  RarityColorResponse,
  WeaponInfo,
  WeaponListResponse,
  WeaponTypeInfo,
  WeaponTypeListResponse,
} from '@/types/staticData'
import { ref } from 'vue'

const weaponsMap = ref<Map<string, WeaponInfo>>(new Map())
const weaponTypes = ref<WeaponTypeInfo[]>([])
const essencesMap = ref<Map<string, EssenceInfo>>(new Map())
const rarityColors = ref<Record<number, string>>({})
const matrixIcons = ref<MatrixIconResponse>({ essenceBg: '', skills: {} })
const energyAlluviums = ref<EnergyAlluviumInfo[]>([])
const isLoaded = ref(false)

/**
 * 辅助函数：检查 HTTP 响应状态码并解析 JSON
 */
async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText} (${url})`)
  }
  return res.json() as Promise<T>
}

async function fetchStaticData() {
  try {
    const [weaponsRes, weaponTypesRes, essencesRes, rarityColorsRes, matrixIconsRes, alluviumsRes] =
      await Promise.all([
        fetchJson<WeaponListResponse>(`/api/static/weapons`),
        fetchJson<WeaponTypeListResponse>(`/api/static/weapon_types`),
        fetchJson<EssenceListResponse>(`/api/static/essences`),
        fetchJson<RarityColorResponse>(`/api/static/rarity_colors`),
        fetchJson<MatrixIconResponse>(`/api/static/matrix_icons`),
        fetchJson<EnergyAlluviumListResponse>(`/api/static/energy_alluviums`),
      ])

    weaponsMap.value = new Map(weaponsRes.weapons.map((w) => [w.id, w]))
    weaponTypes.value = weaponTypesRes.weaponTypes
    essencesMap.value = new Map(essencesRes.items.map((e) => [e.id, e]))
    rarityColors.value = rarityColorsRes.colors
    matrixIcons.value = matrixIconsRes
    energyAlluviums.value = alluviumsRes.items
    isLoaded.value = true
  } catch (error) {
    console.error('Failed to fetch static data:', error)
  }
}

export function useStaticData() {
  return {
    weaponsMap,
    weaponTypes,
    essencesMap,
    rarityColors,
    matrixIcons,
    energyAlluviums,
    isLoaded,
    fetchStaticData,
  }
}
