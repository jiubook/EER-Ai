/**
 * 宝藏基质导入表格的解析与合并规划。
 *
 * 与 matrixExportTable.ts 互为反操作：那边把卡片写成本文，这里把它读回条目，
 * 并算出「合并 / 替换」之后要提交给后端的整表。解析与合并都不碰应用状态，
 * 输入是普通字符串与数组，所以能在 node 环境的单测里直接跑。
 *
 * 三条安全约定：
 * - 文件里「未获得」的行不导入：否则一次导入会把全部武器标成已拥有；
 * - 一行等级都读不出来的行直接跳过：猜出来的默认等级会把现有配置洗成 1；
 * - 未知武器、缺失的自定义基质一律跳过并计数，由 UI 报给用户，不静默吞掉。
 */

import type { TreasureMatrixEntry } from '@/composables/useProfiles'

/** 各槽位满级，与后端 schemas/profile.py 的 le 约束一致 */
const MAX_LEVELS = [6, 6, 3] as const

/** 自定义基质在矩阵里的 weapon_id 前缀，与后端 CUSTOM_ID_PREFIX 一致 */
const CUSTOM_ID_PREFIX = 'custom:'

/** 解析阶段的结构常量，与导出 CSV 的表头一一对应 */
const HEADER_WEAPON_ID = '武器ID'
const HEADER_NAME = '名称'
const HEADER_OWNED = '是否已获得'
const HEADER_CALCULATION = '参与计算'
const HEADER_PRIORITY = '优先级'
const HEADER_LEVELS = ['属性等级', '附加等级', '技能等级'] as const

/** 行被跳过的原因 */
export type ImportSkipReason =
  /** 缺 weapon_id 或等级一列都读不出来 */
  | 'invalid_row'
  /** 等级越界或不是整数 */
  | 'invalid_level'
  /** 文件里标记为未获得，不导入 */
  | 'not_owned'
  /** 内置武器 ID 不在当前静态数据里 */
  | 'unknown_weapon'
  /** 引用了本机不存在的自定义基质 */
  | 'missing_custom'

export interface ImportSkip {
  /** 1 起的行号：CSV 指数据行（表头算第 1 行），JSON 指 items 下标 + 1 */
  lineNumber: number
  weaponId: string
  reason: ImportSkipReason
}

/** 解析出来的一行，尚未与当前配置合并 */
export interface ImportRow {
  lineNumber: number
  weaponId: string
  /** 文件里记录的显示名，仅作参考；内置武器最终以静态数据为准 */
  name: string
  /** 各槽位等级；null 表示文件里没有该槽位（3★ 武器没有附加词条） */
  levels: readonly [number | null, number | null, number | null]
  /** 是否已获得；null 表示文件没写（按已获得处理） */
  owned: boolean | null
  /** 是否参与计算；null 表示文件没写，合并时沿用现有值 */
  includeInCalculation: boolean | null
  /** 优先级；null 表示文件没写，合并时沿用现有值 */
  priority: number | null
}

export interface ParsedImport {
  rows: ImportRow[]
  skipped: ImportSkip[]
}

/** 合并：按 weapon_id 覆盖，文件外的条目保留；替换：整表以文件为准 */
export type ImportMode = 'merge' | 'replace'

export interface ImportPlanInput {
  rows: readonly ImportRow[]
  skipped: readonly ImportSkip[]
  existing: readonly TreasureMatrixEntry[]
  /** 内置武器：weapon_id → 规范显示名 */
  builtinNames: ReadonlyMap<string, string>
  /** 本机存在的自定义基质：带 custom: 前缀的 weapon_id → 显示名 */
  customNames: ReadonlyMap<string, string>
  mode: ImportMode
}

export interface ImportPlan {
  /** 最终提交给后端的整表 */
  entries: TreasureMatrixEntry[]
  /** 文件里新增的条目 */
  added: TreasureMatrixEntry[]
  /** 文件里覆盖掉的条目 */
  updated: TreasureMatrixEntry[]
  /** 仅替换模式有：现有条目里不在文件中的，将被删除 */
  removed: TreasureMatrixEntry[]
  /** 被跳过的行（含解析阶段就跳过的） */
  skipped: ImportSkip[]
}

/** 去掉 UTF-8 BOM 与首尾空白：Excel 另存的 CSV 通常带 BOM */
function stripBom(text: string): string {
  return text.replace(/^\uFEFF/, '')
}

/**
 * 切分 CSV 为二维单元格。
 *
 * 只实现导入需要的最小集：双引号包裹、"" 转义、CRLF/LF 行尾、字段内换行。
 * 不引第三方 CSV 依赖——只为读回自己导出的文件，不值得为它增加一个依赖。
 */
function splitCsvRows(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false

  for (let index = 0; index < text.length; index++) {
    const char = text[index]!
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          cell += '"'
          index++
        } else {
          quoted = false
        }
      } else {
        cell += char
      }
      continue
    }
    if (char === '"') {
      quoted = true
      continue
    }
    if (char === ',') {
      row.push(cell)
      cell = ''
      continue
    }
    if (char === '\r') continue
    if (char === '\n') {
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
      continue
    }
    cell += char
  }

  if (cell !== '' || row.length > 0) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

/** 「是/否」表头的布尔解析；空值表示文件没写 */
function parseFlag(raw: string | undefined): boolean | null {
  const text = (raw ?? '').trim().toLowerCase()
  if (text === '') return null
  if (text === '是' || text === 'true' || text === '1') return true
  if (text === '否' || text === 'false' || text === '0') return false
  return null
}

/** 等级解析：空 → null；越界或非整数 → 'invalid' */
function parseLevel(raw: string | undefined, maxLevel: number): number | null | 'invalid' {
  const text = (raw ?? '').trim()
  if (text === '') return null
  if (!/^\d+$/.test(text)) return 'invalid'
  const value = Number(text)
  return value < 1 || value > maxLevel ? 'invalid' : value
}

/** 优先级解析：非法值按「未设置」处理，不值得因此丢掉整行等级数据 */
function parsePriority(raw: string | undefined): number | null {
  const text = (raw ?? '').trim()
  if (!/^\d+$/.test(text)) return null
  return Number(text)
}

/** 按表头名定位列，缺列时返回 undefined——列顺序变了也不会错位 */
function columnIndex(header: readonly string[], name: string): number | undefined {
  const index = header.findIndex((cell) => cell.trim() === name)
  return index === -1 ? undefined : index
}

function cellAt(cells: readonly string[], index: number | undefined): string | undefined {
  return index === undefined ? undefined : cells[index]
}

function parseCsv(text: string): ParsedImport {
  const rows = splitCsvRows(text).filter((cells) => cells.some((cell) => cell.trim() !== ''))
  const header = rows.shift()
  if (!header) return { rows: [], skipped: [] }

  const weaponIdColumn = columnIndex(header, HEADER_WEAPON_ID)
  if (weaponIdColumn === undefined) {
    throw new Error(`CSV 缺少「${HEADER_WEAPON_ID}」列，无法确定要导入哪把武器`)
  }

  const nameColumn = columnIndex(header, HEADER_NAME)
  const ownedColumn = columnIndex(header, HEADER_OWNED)
  const calculationColumn = columnIndex(header, HEADER_CALCULATION)
  const priorityColumn = columnIndex(header, HEADER_PRIORITY)
  const levelColumns = HEADER_LEVELS.map((name) => columnIndex(header, name))

  const parsed: ParsedImport = { rows: [], skipped: [] }

  for (const [rowIndex, cells] of rows.entries()) {
    // 表头占第 1 行，数据行从第 2 行起
    const lineNumber = rowIndex + 2
    const weaponId = (cellAt(cells, weaponIdColumn) ?? '').trim()
    if (!weaponId) {
      parsed.skipped.push({ lineNumber, weaponId: '', reason: 'invalid_row' })
      continue
    }

    const owned = parseFlag(cellAt(cells, ownedColumn))
    if (owned === false) {
      parsed.skipped.push({ lineNumber, weaponId, reason: 'not_owned' })
      continue
    }

    const levels: [number | null, number | null, number | null] = [null, null, null]
    let levelInvalid = false
    for (const [slot, column] of levelColumns.entries()) {
      const value = parseLevel(cellAt(cells, column), MAX_LEVELS[slot]!)
      if (value === 'invalid') {
        levelInvalid = true
        break
      }
      levels[slot] = value
    }

    if (levelInvalid) {
      parsed.skipped.push({ lineNumber, weaponId, reason: 'invalid_level' })
      continue
    }
    if (levels.every((level) => level === null)) {
      parsed.skipped.push({ lineNumber, weaponId, reason: 'invalid_row' })
      continue
    }

    parsed.rows.push({
      lineNumber,
      weaponId,
      name: (cellAt(cells, nameColumn) ?? '').trim(),
      levels,
      owned,
      includeInCalculation: parseFlag(cellAt(cells, calculationColumn)),
      priority: parsePriority(cellAt(cells, priorityColumn)),
    })
  }

  return parsed
}

/** 槽位解析：接受 0/1/2、attribute/secondary/skill 以及中文槽位名 */
function toSlotIndex(raw: unknown): number | null {
  if (typeof raw === 'number') {
    return Number.isInteger(raw) && raw >= 0 && raw <= 2 ? raw : null
  }
  if (typeof raw === 'string') {
    const text = raw.trim().toLowerCase()
    if (text === 'attribute' || text === '属性') return 0
    if (text === 'secondary' || text === '附加') return 1
    if (text === 'skill' || text === '技能') return 2
  }
  return null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null
}

function parseJsonItem(
  item: unknown,
  lineNumber: number,
): { row: ImportRow } | { skip: ImportSkip } {
  const record = asRecord(item)
  if (!record) {
    return { skip: { lineNumber, weaponId: '', reason: 'invalid_row' } }
  }

  const weaponId = typeof record.weapon_id === 'string' ? record.weapon_id.trim() : ''
  if (!weaponId) {
    return { skip: { lineNumber, weaponId: '', reason: 'invalid_row' } }
  }

  const owned = typeof record.owned === 'boolean' ? record.owned : null
  if (owned === false) {
    return { skip: { lineNumber, weaponId, reason: 'not_owned' } }
  }

  const levels: [number | null, number | null, number | null] = [null, null, null]
  const traits = Array.isArray(record.traits) ? record.traits : []
  for (const trait of traits) {
    const traitRecord = asRecord(trait)
    if (!traitRecord) continue
    const slot = toSlotIndex(traitRecord.slot)
    if (slot === null) continue
    const level = traitRecord.level
    if (
      typeof level !== 'number' ||
      !Number.isInteger(level) ||
      level < 1 ||
      level > MAX_LEVELS[slot]!
    ) {
      return { skip: { lineNumber, weaponId, reason: 'invalid_level' } }
    }
    levels[slot] = level
  }

  if (levels.every((level) => level === null)) {
    return { skip: { lineNumber, weaponId, reason: 'invalid_row' } }
  }

  const priority = record.priority
  return {
    row: {
      lineNumber,
      weaponId,
      name: typeof record.name === 'string' ? record.name.trim() : '',
      levels,
      owned,
      includeInCalculation:
        typeof record.include_in_calculation === 'boolean' ? record.include_in_calculation : null,
      priority:
        typeof priority === 'number' && Number.isInteger(priority) && priority >= 0
          ? priority
          : null,
    },
  }
}

function parseJson(text: string): ParsedImport {
  let payload: unknown
  try {
    payload = JSON.parse(text)
  } catch (error) {
    throw new Error(`JSON 解析失败：${error instanceof Error ? error.message : String(error)}`)
  }

  const container = asRecord(payload)
  const items = Array.isArray(payload) ? payload : (container?.items ?? null)
  if (!Array.isArray(items)) {
    throw new TypeError('JSON 里找不到 items 数组，这不是宝藏基质导出文件')
  }

  const parsed: ParsedImport = { rows: [], skipped: [] }
  for (const [index, item] of items.entries()) {
    const result = parseJsonItem(item, index + 1)
    if ('skip' in result) parsed.skipped.push(result.skip)
    else parsed.rows.push(result.row)
  }
  return parsed
}

/**
 * 解析导入文本，按内容而不是扩展名判断格式。
 *
 * 用户把 JSON 存成 .csv（或反过来）是常事，内容嗅探比看文件名可靠：
 * 以 `{` 或 `[` 开头就是 JSON，其余按 CSV 处理。
 *
 * @throws Error 结构性问题（不是 JSON、缺武器ID列、找不到 items）时抛出，
 *   消息直接面向用户展示；行级问题走 skipped 返回，不中断整批。
 */
export function parseImportText(text: string): ParsedImport {
  const trimmed = stripBom(text).trimStart()
  if (trimmed === '') throw new Error('文件是空的')
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return parseJson(trimmed)
  return parseCsv(trimmed)
}

/**
 * 合并解析结果与现有配置，算出最终要提交的整表。
 *
 * 文件里没写的字段（参与计算、优先级）沿用现有条目，避免用一份旧文件把
 * 用户手设的优先级洗成 0；文件里写了 0 就按 0 处理——那正是导出时的状态。
 */
export function buildImportPlan(input: ImportPlanInput): ImportPlan {
  const existingById = new Map(input.existing.map((entry) => [entry.weapon_id, entry] as const))
  const skipped = [...input.skipped]

  // 同一把武器在文件里出现多次时以最后一行为准，避免提交出重复条目
  const incoming = new Map<string, TreasureMatrixEntry>()
  for (const row of input.rows) {
    const name = input.builtinNames.get(row.weaponId) ?? input.customNames.get(row.weaponId)
    if (name === undefined) {
      skipped.push({
        lineNumber: row.lineNumber,
        weaponId: row.weaponId,
        reason: row.weaponId.startsWith(CUSTOM_ID_PREFIX) ? 'missing_custom' : 'unknown_weapon',
      })
      continue
    }

    const previous = existingById.get(row.weaponId)
    incoming.set(row.weaponId, {
      weapon_id: row.weaponId,
      weapon_name: name,
      affix1_level: row.levels[0] ?? 1,
      affix2_level: row.levels[1] ?? 1,
      affix3_level: row.levels[2] ?? 1,
      include_in_calculation: row.includeInCalculation ?? previous?.include_in_calculation ?? true,
      priority: row.priority ?? previous?.priority ?? 0,
    })
  }

  const added = [...incoming.values()].filter((entry) => !existingById.has(entry.weapon_id))
  const updated = [...incoming.values()].filter((entry) => existingById.has(entry.weapon_id))

  if (input.mode === 'merge') {
    const replaced = new Map(incoming)
    const entries = input.existing.map((entry) => replaced.get(entry.weapon_id) ?? { ...entry })
    entries.push(...added)
    return { entries, added, updated, removed: [], skipped }
  }

  const keptIds = new Set(incoming.keys())
  return {
    entries: [...incoming.values()],
    added,
    updated,
    removed: input.existing.filter((entry) => !keptIds.has(entry.weapon_id)),
    skipped,
  }
}

/**
 * 把账号当前的矩阵写成可再次导入的 JSON 快照。
 *
 * 用导入格式而不是原始 dump：回滚时直接把这份文件按「替换」模式导回去即可，
 * 不需要另写一套恢复逻辑。`owned` 恒为 true——矩阵里的条目本来就代表已拥有。
 *
 * @param profile 账号名称
 * @param entries 该账号当前的宝藏基质条目
 * @param exportedAt ISO 8601 时间戳
 * @returns JSON 文本（带缩进，末尾换行）
 */
export function entriesToBackupJson(
  profile: string,
  entries: readonly TreasureMatrixEntry[],
  exportedAt: string,
): string {
  const payload = {
    profile,
    exported_at: exportedAt,
    count: entries.length,
    items: entries.map((entry) => ({
      weapon_id: entry.weapon_id,
      name: entry.weapon_name,
      owned: true,
      include_in_calculation: entry.include_in_calculation ?? true,
      priority: entry.priority ?? 0,
      traits: [
        { slot: 'attribute', level: entry.affix1_level },
        { slot: 'secondary', level: entry.affix2_level },
        { slot: 'skill', level: entry.affix3_level },
      ],
    })),
  }
  return `${JSON.stringify(payload, null, 2)}\n`
}
