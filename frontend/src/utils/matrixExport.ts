/**
 * 宝藏基质导出图的 Canvas 绘制模块。
 *
 * 这里只负责「把一组卡片画成一张图」，不感知任何应用状态：
 * 调用方把 profile、静态数据整理成普通对象传进来。
 * 这样布局计算能在 node 环境的单测里直接跑，无需 DOM。
 *
 * 视觉由「模板」驱动：配色、装饰层、卡片切角都从 MatrixExportTemplate
 * 读取，同一份数据套不同模板就能产出不同风格的图。模板是写死的常量，
 * 不跟随 Vuetify 主题——导出图是给别人看的成品，同一份数据在任何机器、
 * 任何主题下都应该产出同一张图。
 */

import Color from 'color'

/** 导出图里的一张卡片 */
export interface ExportCard {
  /** 'weapon' 画武器 icon + 基质小图；'custom' 只画放大的基质图 */
  kind: 'weapon' | 'custom'
  name: string
  /** 名称上方的小号注音行（内置武器放 ★ 星级）；缺省则该行留空 */
  nameRuby?: string
  /** 武器 icon 地址；自定义基质没有武器图，传 null */
  iconUrl: string | null
  /** 基质底板地址 */
  essenceBgUrl: string
  /** 技能属性图标地址 */
  skillIconUrl: string | null
  /** 物品识别色：内置武器用稀有度色，自定义基质用橙色。全图仅此一处保留高饱和 */
  tierColor: string
  levels: readonly [number, number, number]
  maxed: boolean
  /** 扫描到的基质枚数；缺省或非正数时不画角标 */
  badgeCount?: number
  /** 三词条中文名，如 ["攻击", "终结技充能效率", "巧技"] */
  traitNames?: string[]
  /** 未获得的条目：整张卡片降级到背景层 */
  dimmed?: boolean
}

/**
 * 一套导出图模板的全部视觉参数。
 *
 * 同一套布局数学适用于所有模板，模板只改「怎么看」不改「怎么排」：
 * 卡片尺寸、网格、页头页脚的高度全部共享，切模板时预览不会跳版式。
 */
export interface MatrixExportTemplate {
  /** 模板 id，用于选择器和 getExportTemplate 查询 */
  id: string
  /** 模板中文名，展示在选择器里 */
  name: string
  /** 一句话说明，展示在选择器 tooltip 里 */
  description: string
  /** 主色板 */
  ink: {
    /** 页面底 */
    bg: string
    /** 卡面 */
    surface: string
    /** 未获得卡片的卡面 */
    surfaceDim: string
    /** 基质底板的衬底 */
    plate: string
    /** 主文字 */
    text: string
    /** 次文字 */
    muted: string
    /** 结构线 */
    line: string
    /** 薄金属框的内衬线 */
    lineSoft: string
    /** 强调色：锚点/警示/重点（工业档案是工程黄） */
    accent: string
    /** 强调色底上的文字色 */
    accentInk: string
  }
  /** 未获得卡片专用的浅色文字 */
  dim: {
    text: string
    muted: string
    line: string
  }
  /** 三行词条方格的数据色 */
  pip: {
    /** 三行各自的激活色 */
    colors: readonly [string, string, string]
    /** 未激活方格 */
    idle: string
    /** 未获得卡片的未激活方格 */
    idleDim: string
  }
  /** 装饰层开关。所有装饰都是背景级元素，关掉只会让页面更素，不会影响数据可读性 */
  decorations: {
    /** 表面颗粒噪点（混凝土 / 旧纸质感） */
    noise: boolean
    /** 背景工业网格 */
    grid: boolean
    /** 页头衬底水墨字 */
    brushGlyph: boolean
    /** 水墨字字符（如 "基" / "墨"） */
    brushGlyphChar: string
    /** 页脚警示斜纹带 */
    hazardStripes: boolean
    /** 右上角一图流二维码标签 */
    qrTag: boolean
  }
  /** 卡片右上角的切角边长。工业面板用斜切，极简模板可调小接近直角 */
  cardChamfer: number
}

/** 工业档案：灰白混凝土底、工程黄锚点、蓝青数据。默认模板，全装饰开启 */
const INDUSTRIAL_TEMPLATE: MatrixExportTemplate = {
  id: 'industrial',
  name: '工业档案',
  description: '灰白混凝土、工程黄锚点、蓝青数据，冷静克制的档案质感',
  ink: {
    bg: '#e8e6e1',
    surface: 'rgba(244, 242, 238, 0.9)',
    surfaceDim: 'rgba(226, 224, 218, 0.72)',
    plate: '#faf8f4',
    text: '#1c1c1a',
    muted: '#6b6862',
    line: '#c4c0b8',
    lineSoft: '#dcd8d0',
    accent: '#e5b833',
    accentInk: '#3a2c00',
  },
  dim: { text: '#95918a', muted: '#adaaa3', line: '#d8d4cc' },
  pip: {
    colors: ['#2d5f8a', '#3d8b8b', '#5a6b7a'],
    idle: '#d3cfc7',
    idleDim: '#dfdcd5',
  },
  decorations: {
    noise: true,
    grid: true,
    brushGlyph: true,
    brushGlyphChar: '基',
    hazardStripes: true,
    qrTag: true,
  },
  cardChamfer: 9,
}

/** 暗夜终端：深色底、霓虹数据色、青绿强调，护眼且贴近终端机观感 */
const DARK_TEMPLATE: MatrixExportTemplate = {
  id: 'dark',
  name: '暗夜终端',
  description: '深色底、霓虹数据色与青绿强调，护眼的终端机质感',
  ink: {
    bg: '#0f1419',
    surface: 'rgba(20, 26, 32, 0.92)',
    surfaceDim: 'rgba(15, 20, 25, 0.8)',
    plate: '#1a2129',
    text: '#d8e0e8',
    muted: '#7c8894',
    line: '#2b3540',
    lineSoft: '#232c35',
    accent: '#3ddc97',
    accentInk: '#052e1f',
  },
  dim: { text: '#57626d', muted: '#46505a', line: '#262f38' },
  pip: {
    colors: ['#22d3ee', '#4ade80', '#a78bfa'],
    idle: '#2a333d',
    idleDim: '#212932',
  },
  decorations: {
    noise: true,
    grid: true,
    brushGlyph: false,
    brushGlyphChar: '基',
    hazardStripes: true,
    qrTag: true,
  },
  cardChamfer: 9,
}

/** 水墨卷轴：米白纸底、墨色文字、朱砂印章红，楷书水墨字衬底 */
const INK_TEMPLATE: MatrixExportTemplate = {
  id: 'ink',
  name: '水墨卷轴',
  description: '米白纸底、墨色文字与朱砂印章红，东方卷轴质感',
  ink: {
    bg: '#f2ecdf',
    surface: 'rgba(250, 247, 241, 0.92)',
    surfaceDim: 'rgba(240, 235, 226, 0.8)',
    plate: '#faf7f0',
    text: '#33291d',
    muted: '#85775f',
    line: '#c8bda6',
    lineSoft: '#ddd4c1',
    accent: '#a63d2f',
    accentInk: '#f6efe2',
  },
  dim: { text: '#a89b84', muted: '#b7ab94', line: '#d5ccb8' },
  pip: {
    colors: ['#3f6f8f', '#8a6a3b', '#5f5a6e'],
    idle: '#d9d0bc',
    idleDim: '#e2dac9',
  },
  decorations: {
    noise: true,
    grid: false,
    brushGlyph: true,
    brushGlyphChar: '墨',
    hazardStripes: false,
    qrTag: true,
  },
  cardChamfer: 4,
}

/** 极简白：纯白底、细线、单一蓝点缀，去掉全部装饰，适合打印与分享 */
const MINIMAL_TEMPLATE: MatrixExportTemplate = {
  id: 'minimal',
  name: '极简白',
  description: '纯白底、细线与单一蓝点缀，无装饰噪点，清爽干净',
  ink: {
    bg: '#ffffff',
    surface: 'rgba(255, 255, 255, 0.96)',
    surfaceDim: 'rgba(246, 246, 246, 0.92)',
    plate: '#fafafa',
    text: '#1a1a1a',
    muted: '#8a8a8a',
    line: '#e0e0e0',
    lineSoft: '#ececec',
    accent: '#2563eb',
    accentInk: '#ffffff',
  },
  dim: { text: '#b8b8b8', muted: '#c8c8c8', line: '#e6e6e6' },
  pip: {
    colors: ['#2563eb', '#0ea5e9', '#64748b'],
    idle: '#e5e7eb',
    idleDim: '#f0f0f0',
  },
  decorations: {
    noise: false,
    grid: false,
    brushGlyph: false,
    brushGlyphChar: '基',
    hazardStripes: false,
    qrTag: true,
  },
  cardChamfer: 6,
}

/** 游戏原风：深空蓝底、金色锚点、高饱和数据色，贴近游戏内 UI 的观感 */
const GAME_TEMPLATE: MatrixExportTemplate = {
  id: 'game',
  name: '游戏原风',
  description: '深空蓝底、金色锚点与高饱和数据色，贴近游戏内界面',
  ink: {
    bg: '#0d1b2a',
    surface: 'rgba(19, 33, 49, 0.94)',
    surfaceDim: 'rgba(14, 24, 36, 0.82)',
    plate: '#12202f',
    text: '#e8eef5',
    muted: '#8fa3b8',
    line: '#2a3f55',
    lineSoft: '#223349',
    accent: '#e8b54a',
    accentInk: '#2b2107',
  },
  dim: { text: '#5c7188', muted: '#4a5d72', line: '#233247' },
  pip: {
    colors: ['#4fc3f7', '#5eead4', '#a78bfa'],
    idle: '#243a50',
    idleDim: '#1c2c3e',
  },
  decorations: {
    noise: true,
    grid: true,
    brushGlyph: false,
    brushGlyphChar: '基',
    hazardStripes: true,
    qrTag: true,
  },
  cardChamfer: 9,
}

/** 全部模板，按选择器展示顺序排列。第一个是默认模板 */
export const EXPORT_TEMPLATES: readonly MatrixExportTemplate[] = [
  INDUSTRIAL_TEMPLATE,
  DARK_TEMPLATE,
  INK_TEMPLATE,
  MINIMAL_TEMPLATE,
  GAME_TEMPLATE,
]

/**
 * 按 id 查模板；未知 id 回退到默认的工业档案。
 *
 * @param id 模板 id。
 * @returns 匹配的模板；找不到时返回工业档案。
 */
export function getExportTemplate(id: string): MatrixExportTemplate {
  return EXPORT_TEMPLATES.find((template) => template.id === id) ?? INDUSTRIAL_TEMPLATE
}

/** 把 input.template（可能是 id 或模板对象）归一化成模板对象 */
function resolveTemplate(template?: MatrixExportTemplate | string): MatrixExportTemplate {
  if (!template) return INDUSTRIAL_TEMPLATE
  return typeof template === 'string' ? getExportTemplate(template) : template
}

export interface MatrixExportInput {
  /** 内置武器卡，调用方已排好序 */
  weapons: readonly ExportCard[]
  /** 自定义基质卡，永远画在最下方 */
  customs: readonly ExportCard[]
  /** 数据库名，画在页头的筛选栏里，如 "default · 宝藏基质" */
  title: string
  /** 归档时间等辅助信息，画在右上角档案抬头的末行 */
  subtitle: string
  /** 导出模板：传模板 id 或模板对象，缺省用工业档案 */
  template?: MatrixExportTemplate | string
  /** 像素倍率，默认 2；超出画布上限时内部自动降级 */
  scale?: number
  /** 网格列数，不传则按卡片总数自适应 */
  columns?: number
}

export interface MatrixExportResult {
  /** 导出图；正常是 WebP，浏览器不支持 WebP 编码时会回退成 PNG，看 blob.type */
  blob: Blob
  /** 预览用的 object URL，调用方负责 revoke */
  objectUrl: string
  /** CSS 像素尺寸（非设备像素） */
  width: number
  height: number
  /** 实际生效的倍率，可能因画布上限被降级 */
  scale: number
  /** 加载失败、已用占位图代替的图片数量 */
  missingImages: number
}

// --- 字体 ---

const FONT_STACK = '"HarmonyOS Sans SC", sans-serif'
/** 编号、英文标签、数值：等宽字体是工业档案观感的主要来源 */
const MONO_STACK = '"JetBrains Mono", "Fira Code", Consolas, monospace'
/** 背景水墨字：楷体做书法感，缺字时回退衬线 */
const BRUSH_STACK = '"KaiTi", "STKaiti", "SimSun", serif'

// --- 档案文案 ---

const BRAND_TITLE = '基质图鉴'
const BRAND_TITLE_EN = 'MATRIX CATALOG'
const ARCHIVE_ORG = '终末地基质档案'
const ARCHIVE_ORG_EN = 'ENDFIELD ESSENCE ARCHIVES'

// --- 署名与外链 ---

const PROJECT_NAME = '终末地基质小助手'
const PROJECT_REPO = 'github.com/Logical-Byte/endfield-essence-recognizer'
/** 页脚右下的署名：开发组织 · 本页作者 · 开源协议 */
const CREDIT_LINE = '逻辑元 LogicalByte · jiubook · AGPL-3.0'
const YITULIU_NAME = '终末地一图流'
const YITULIU_URL = 'ef.yituliu.cn'

/**
 * 一图流站点二维码的模块点阵（Version 2 / 纠错 M / 25×25）。
 *
 * 内容固定为 https://ef.yituliu.cn/，所以离线生成一次写死在这里：
 * 为导出图里的一个角标引入运行时 QR 依赖不划算，写死也顺带保证
 * 任何机器上画出的点阵完全一致。地址变更时用下面这段重新生成整块常量：
 *
 * ```
 * npm i qrcode --prefix /tmp/qrgen --no-save
 * NODE_PATH=/tmp/qrgen/node_modules node -e "const QR=require('qrcode');
 *   const q=QR.create('https://ef.yituliu.cn/',{errorCorrectionLevel:'M'});
 *   const n=q.modules.size;for(let y=0;y<n;y++){let r='';
 *   for(let x=0;x<n;x++)r+=q.modules.get(x,y)?'1':'0';console.log(r)}"
 * ```
 */
export const YITULIU_QR: readonly string[] = [
  '1111111011001111101111111',
  '1000001001001000001000001',
  '1011101010101010101011101',
  '1011101011001110101011101',
  '1011101010010000001011101',
  '1000001011010000101000001',
  '1111111010101010101111111',
  '0000000000001110000000000',
  '0011111100001100110111101',
  '1101100001110101110100001',
  '0110111001000111100001001',
  '1100110100010000001110000',
  '0000001000000101101001011',
  '0001110010101110111001110',
  '1110011010011010001100101',
  '0110010100111011100010110',
  '1100101101111101111110110',
  '0000000000100010100011101',
  '1111111010101000101011001',
  '1000001011110111100010011',
  '1011101010001011111111011',
  '1011101010100110010101111',
  '1011101010001000101011101',
  '1000001001101110001011001',
  '1111111000111011001011111',
]

// --- 布局常量（CSS 像素）---
const PAGE_PAD = 26
const GAP = 14
const SECTION_GAP = 26
const HEADER_H = 148
const FOOTER_H = 66
const SECTION_HEAD_H = 34
const CARD_W = 260
const CARD_H = 144
const CARD_PAD = 12
const NAME_H = 22
/** 名称上方的注音行高度；不管有没有星级都占位，两类卡片的名称才对得齐 */
const RUBY_H = 11
const RUBY_FONTSIZE = 9
const ICON = 56
const MATRIX_ICON = 56
const PIP_W = 8
const PIP_H = 12
const PIP_GAP = 3
const PIP_ROW_GAP = 21
const BADGE_R = 10
const TRAIT_FONTSIZE = 12
/** 数据库筛选栏高度 */
const DB_BAR_H = 32
/** 二维码每个模块的边长 */
const QR_MODULE = 2
/** 二维码四周留出的静区模块数，太窄会影响识别 */
const QR_QUIET = 3
/** 二维码底板边长：点阵本体加两侧静区 */
const QR_BOX = (YITULIU_QR.length + QR_QUIET * 2) * QR_MODULE
/** 背景工业网格的间距 */
const GRID_STEP = 44

/** 各词条的方格数，与 useWeaponStats 的 AFFIX_MAX_LEVEL 保持一致 */
const AFFIX_PIP_COUNT = [6, 6, 3] as const

/**
 * 二维码底板与模块的固定色。
 *
 * 不用模板色：二维码要能被机器扫出来，必须保持「深模块 + 浅底板」的
 * 高对比。深色模板（暗夜终端、游戏原风）的 plate/text 是反过来的，
 * 跟模板走会让码失效，所以这里写死。
 */
const QR_PLATE = '#faf8f4'
const QR_MODULE_COLOR = '#1c1c1a'

/** 画布单边的设备像素上限，取远低于 Chromium 16384 的保守值 */
const MAX_DEVICE_PX = 8192

/**
 * 导出图的编码格式。
 *
 * PNG 对这张图格外不利：drawPaper 铺的颗粒层逐像素随机，几乎不可压缩，
 * 两千万像素能压出十几 MB。同一份内容换成 WebP 只有几 MB。
 */
const EXPORT_MIME = 'image/webp'

/**
 * WebP 质量。
 *
 * Chromium 只在质量严格等于 1 时走无损编码，小于 1 则是有损档位——有损能再
 * 小一个量级，代价是颗粒层被平滑掉一部分。想换档位只改这个常量，其余链路
 * 都按实际产出的 MIME 走，不必跟着动。
 */
const EXPORT_QUALITY = 1

/**
 * 按卡片总数选择网格列数。
 *
 * 两个区共用同一列数，网格才对得齐。
 */
export function pickColumns(cardCount: number): number {
  if (cardCount <= 3) return Math.max(1, cardCount)
  if (cardCount <= 8) return 3
  if (cardCount <= 18) return 4
  if (cardCount <= 40) return 5
  return 6
}

/**
 * 生成页脚的档案编号。
 *
 * 补零到三位，等宽字体下宽度稳定，条目数变化时页脚不会跳动。
 *
 * @param count 导出的条目总数。
 * @returns 形如 `EER-077-MATRIX` 的编号。
 */
export function buildArchiveNo(count: number): string {
  const safe = Number.isFinite(count) ? Math.max(0, Math.trunc(count)) : 0
  return `EER-${String(safe).padStart(3, '0')}-MATRIX`
}

/**
 * 计算画布尺寸与两个区各自的行数。
 *
 * 任一区为空时，该区连同区标题都不占高度。
 */
export function computeCanvasSize(
  weaponCount: number,
  customCount: number,
  columns: number,
): { width: number; height: number; weaponRows: number; customRows: number } {
  const cols = Math.max(1, columns)
  const weaponRows = Math.ceil(weaponCount / cols)
  const customRows = Math.ceil(customCount / cols)

  const width = PAGE_PAD * 2 + cols * CARD_W + (cols - 1) * GAP

  let height = PAGE_PAD + HEADER_H
  if (weaponRows > 0) {
    height += SECTION_HEAD_H + weaponRows * (CARD_H + GAP) - GAP
  }
  if (customRows > 0) {
    if (weaponRows > 0) height += SECTION_GAP
    height += SECTION_HEAD_H + customRows * (CARD_H + GAP) - GAP
  }
  height += SECTION_GAP + FOOTER_H + PAGE_PAD

  return { width, height, weaponRows, customRows }
}

/**
 * 图片缓存：只缓存加载成功的，失败的下次重试
 * （浏览器自己会缓存 404，重试成本很低）。
 */
const imageCache = new Map<string, HTMLImageElement>()

/** 加载单张图片；失败时返回 null，由调用方画占位图 */
async function loadImage(url: string): Promise<HTMLImageElement | null> {
  const cached = imageCache.get(url)
  if (cached) return cached

  const image = new Image()
  image.src = url
  try {
    // decode() 在 404 或解码失败时 reject，这里统一降级为 null
    await image.decode()
  } catch {
    return null
  }
  imageCache.set(url, image)
  return image
}

/** 并发预加载所有卡片用到的图片，返回 url -> 图片（失败为 null）的映射 */
async function preloadImages(
  cards: readonly ExportCard[],
): Promise<Map<string, HTMLImageElement | null>> {
  const urls = new Set<string>()
  for (const card of cards) {
    if (card.iconUrl) urls.add(card.iconUrl)
    if (card.essenceBgUrl) urls.add(card.essenceBgUrl)
    if (card.skillIconUrl) urls.add(card.skillIconUrl)
  }

  const entries = await Promise.all(
    [...urls].map(async (url) => [url, await loadImage(url)] as const),
  )
  return new Map(entries)
}

/**
 * 把 canvas 编码成 Blob；toBlob 是回调式的，这里包一层 Promise。
 *
 * 浏览器不认识请求的格式时，toBlob 会静默回退成 PNG 而不是报错，所以调用方
 * 得看 blob.type，不能假定拿到的就是自己要的格式。
 */
function canvasToBlob(
  canvas: HTMLCanvasElement,
  mimeType: string,
  quality?: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('画布导出失败'))
      },
      mimeType,
      quality,
    )
  })
}

/**
 * 把导出图重新编码成 PNG。
 *
 * 剪贴板专用：Chromium 的剪贴板写入只接受 image/png，塞 WebP 会抛
 * NotAllowedError。这里从已有的 Blob 解码重画，而不是让 renderMatrixExport
 * 一次产出两份——编码这么大的图要几百毫秒，筛选项每动一次都要重绘，
 * 不该为一个可能不会被点的按钮每次都付这个代价。
 *
 * @param blob 导出图 Blob；已经是 PNG 时原样返回。
 * @returns PNG 格式的 Blob。
 * @throws 解码失败或画布导出失败时抛出。
 */
export async function toPngBlob(blob: Blob): Promise<Blob> {
  if (blob.type === 'image/png') return blob

  const bitmap = await createImageBitmap(blob)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('无法创建画布上下文')
    ctx.drawImage(bitmap, 0, 0)
    return await canvasToBlob(canvas, 'image/png')
  } finally {
    bitmap.close()
  }
}

/** 以 rgba 形式取颜色的透明度变体 */
function withAlpha(color: string, alpha: number): string {
  return Color(color).alpha(alpha).string()
}

/**
 * 把外部传入的颜色规范成 canvas 一定认得的字符串。
 *
 * canvas 对无效的 fillStyle 是静默忽略的——一个 undefined 会让整块内容
 * 不翼而飞，而不是报错。这里先过一遍 color 包（它把无效值兜底成黑色），
 * 让"取色取错了"至少表现为颜色不对。只有 tierColor 来自外部，需要这层兜底。
 */
function safeColor(color: string): string {
  try {
    return Color(color).string()
  } catch {
    return '#6b6862'
  }
}

/**
 * 把文字压进指定宽度：先按比例缩字号，到下限仍超宽则尾部截断加省略号。
 *
 * 思路与 utils/autoFontSizing.ts 一致，只是把 DOM 测量换成 measureText。
 * 返回前会把 ctx.font 留在最终字号上，调用方紧接着 fillText 即可。
 */
function fitText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxFontSize: number,
  minFontSize: number,
  weight = 700,
  family = FONT_STACK,
): string {
  ctx.font = `${weight} ${maxFontSize}px ${family}`
  const fullWidth = ctx.measureText(text).width
  if (fullWidth <= maxWidth) return text

  const scaled = Math.max((maxFontSize * maxWidth) / fullWidth, minFontSize)
  ctx.font = `${weight} ${scaled}px ${family}`
  if (ctx.measureText(text).width <= maxWidth) return text

  // 缩到下限仍放不下，只能截断
  let truncated = text
  while (truncated.length > 1 && ctx.measureText(`${truncated}…`).width > maxWidth) {
    truncated = truncated.slice(0, -1)
  }
  return `${truncated}…`
}

/**
 * 画带字距的文字并返回占用宽度。
 *
 * 等宽小字拉开字距是工业档案标签的主要观感来源。
 * letterSpacing 是 ctx 的全局状态，画完必须复位，否则后续文字全被撑开。
 */
function drawTracked(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  spacing: number,
): number {
  ctx.letterSpacing = `${spacing}px`
  const width = ctx.measureText(text).width
  ctx.fillText(text, x, y)
  ctx.letterSpacing = '0px'
  return width
}

/** 测量带字距文字的宽度，不绘制 */
function measureTracked(ctx: CanvasRenderingContext2D, text: string, spacing: number): number {
  ctx.letterSpacing = `${spacing}px`
  const width = ctx.measureText(text).width
  ctx.letterSpacing = '0px'
  return width
}

/** 画一条 1px 细线。canvas 的整数坐标落在像素边界上，偏移半像素才不发虚 */
function drawHairline(
  ctx: CanvasRenderingContext2D,
  color: string,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): void {
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(x1, y1 + 0.5)
  ctx.lineTo(x2, y2 + 0.5)
  ctx.stroke()
}

/**
 * 生成切角矩形路径。
 *
 * 工业面板的边缘是斜切而不是圆角，斜切边本身就是一种结构暗示。
 *
 * @param cut 切角边长；传 0 得到纯直角矩形。
 * @param corners 要切的角，顺序为左上、右上、右下、左下。
 */
function chamferPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  cut: number,
  corners: readonly [boolean, boolean, boolean, boolean] = [false, true, false, false],
): void {
  const [topLeft, topRight, bottomRight, bottomLeft] = corners
  const size = Math.max(0, Math.min(cut, width / 2, height / 2))

  ctx.beginPath()
  ctx.moveTo(x + (topLeft ? size : 0), y)
  ctx.lineTo(x + width - (topRight ? size : 0), y)
  if (topRight) ctx.lineTo(x + width, y + size)
  ctx.lineTo(x + width, y + height - (bottomRight ? size : 0))
  if (bottomRight) ctx.lineTo(x + width - size, y + height)
  ctx.lineTo(x + (bottomLeft ? size : 0), y + height)
  if (bottomLeft) ctx.lineTo(x, y + height - size)
  ctx.lineTo(x, y + (topLeft ? size : 0))
  if (topLeft) ctx.lineTo(x + size, y)
  ctx.closePath()
}

/** 按 object-fit: cover 的规则把图片画进目标矩形 */
function drawImageCover(
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight)
  const drawW = image.naturalWidth * scale
  const drawH = image.naturalHeight * scale
  ctx.drawImage(image, x + (width - drawW) / 2, y + (height - drawH) / 2, drawW, drawH)
}

/** 图片缺失时的占位块 */
function drawImagePlaceholder(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  x: number,
  y: number,
  size: number,
): void {
  ctx.fillStyle = withAlpha(theme.ink.text, 0.06)
  ctx.fillRect(x, y, size, size)

  ctx.strokeStyle = withAlpha(theme.ink.text, 0.16)
  ctx.lineWidth = 1
  ctx.strokeRect(x + 0.5, y + 0.5, size - 1, size - 1)

  ctx.fillStyle = withAlpha(theme.ink.text, 0.3)
  ctx.font = `700 ${Math.round(size * 0.3)}px ${MONO_STACK}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('?', x + size / 2, y + size / 2)
}

// --- 背景层 ---

/**
 * 生成噪点贴图，用作混凝土 / 旧纸的表面颗粒。
 *
 * 用确定性的 xorshift 而不是 Math.random：同一份数据在任何机器上
 * 都应产出逐像素一致的图，随机噪点会破坏这个保证。
 *
 * @param size 贴图边长，会以此为周期平铺。
 */
function makeNoiseTile(size: number): HTMLCanvasElement {
  const tile = document.createElement('canvas')
  tile.width = size
  tile.height = size
  const tileCtx = tile.getContext('2d')!
  const imageData = tileCtx.createImageData(size, size)
  const pixels = imageData.data

  let seed = 0x9e_37_79_b9
  for (let offset = 0; offset < pixels.length; offset += 4) {
    // xorshift32
    seed ^= seed << 13
    seed >>>= 0
    seed ^= seed >>> 17
    seed ^= seed << 5
    seed >>>= 0

    const value = seed / 0xff_ff_ff_ff
    // 一半暗点一半亮点：只压暗会发脏，只提亮会发灰，明暗混合才像水泥面
    const dark = value < 0.5
    const level = dark ? value * 2 : (value - 0.5) * 2
    pixels[offset] = dark ? 0 : 255
    pixels[offset + 1] = pixels[offset]!
    pixels[offset + 2] = pixels[offset]!
    pixels[offset + 3] = Math.round(level * (dark ? 12 : 16))
  }

  tileCtx.putImageData(imageData, 0, 0)
  return tile
}

/**
 * 铺满整页的纸面：底色 + 工业网格 + 表面颗粒。
 *
 * 三层全部压到几乎看不见的程度——它们只负责让大面积留白不显得空，
 * 一旦影响到数据识别就是过头了。网格和颗粒按模板开关。
 */
function drawPaper(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  width: number,
  height: number,
): void {
  ctx.fillStyle = theme.ink.bg
  ctx.fillRect(0, 0, width, height)

  // 工业网格
  if (theme.decorations.grid) {
    ctx.strokeStyle = withAlpha(theme.ink.text, 0.026)
    ctx.lineWidth = 1
    ctx.beginPath()
    for (let x = GRID_STEP; x < width; x += GRID_STEP) {
      ctx.moveTo(x + 0.5, 0)
      ctx.lineTo(x + 0.5, height)
    }
    for (let y = GRID_STEP; y < height; y += GRID_STEP) {
      ctx.moveTo(0, y + 0.5)
      ctx.lineTo(width, y + 0.5)
    }
    ctx.stroke()
  }

  // 表面颗粒
  if (theme.decorations.noise) {
    const pattern = ctx.createPattern(makeNoiseTile(96), 'repeat')
    if (pattern) {
      ctx.fillStyle = pattern
      ctx.fillRect(0, 0, width, height)
    }
  }
}

/**
 * 页头衬底的水墨字。
 *
 * 东方元素退到背景层：只留一个笔画结构，透明度压到几乎与底色同色，
 * 靠 clip 让它被页头区裁掉一截，像盖印时压到了纸边。字符取自模板，
 * 水墨卷轴用「墨」、工业档案用「基」。
 */
function drawBrushGlyph(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  ctx.save()
  ctx.beginPath()
  ctx.rect(x, y, width, height)
  ctx.clip()

  ctx.fillStyle = withAlpha(theme.ink.text, 0.035)
  ctx.font = `400 ${Math.round(height * 1.35)}px ${BRUSH_STACK}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(theme.decorations.brushGlyphChar, x + width * 0.26, y + height * 0.42)

  ctx.restore()
}

/** 工业警示斜纹带，用作页脚的分隔元素 */
function drawHazardStripes(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  if (width <= 0) return

  ctx.save()
  ctx.beginPath()
  ctx.rect(x, y, width, height)
  ctx.clip()

  ctx.strokeStyle = withAlpha(theme.ink.accent, 0.5)
  ctx.lineWidth = 3
  ctx.beginPath()
  // 45° 斜线，起点往左多退一个 height 才能让左边缘也被斜线覆盖满
  for (let offset = -height; offset < width + height; offset += 9) {
    ctx.moveTo(x + offset, y + height)
    ctx.lineTo(x + offset + height, y)
  }
  ctx.stroke()

  ctx.restore()
}

// --- 页头与页脚 ---

/**
 * 数据库筛选栏：把「哪个配置的哪类数据、共多少条」压成一条工业面板。
 *
 * 它承接大标题之后的信息层级——先知道看的是什么库，再进入具体条目。
 */
function drawDatabaseBar(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  title: string,
  count: number,
  x: number,
  y: number,
  width: number,
): void {
  chamferPath(ctx, x, y, width, DB_BAR_H, 8, [false, true, false, true])
  ctx.fillStyle = withAlpha(theme.ink.text, 0.05)
  ctx.fill()
  ctx.strokeStyle = theme.ink.line
  ctx.lineWidth = 1
  ctx.stroke()

  // 两端的强调色端块：整条栏的视觉夹持点
  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(x, y + 6, 4, DB_BAR_H - 12)
  ctx.fillRect(x + width - 4, y + 6, 4, DB_BAR_H - 12)

  const midY = y + DB_BAR_H / 2

  // 右端：条目数。先画右侧才能算出左侧标题的可用宽度
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'right'
  ctx.fillStyle = theme.ink.text
  ctx.font = `800 15px ${MONO_STACK}`
  const countText = String(count)
  const countWidth = ctx.measureText(countText).width
  ctx.fillText(countText, x + width - 14, midY)

  ctx.fillStyle = theme.ink.muted
  ctx.font = `500 9px ${MONO_STACK}`
  const itemsRight = x + width - 14 - countWidth - 8
  const itemsWidth = measureTracked(ctx, 'ITEMS', 1.5)
  ctx.textAlign = 'left'
  drawTracked(ctx, 'ITEMS', itemsRight - itemsWidth, midY, 1.5)

  // 左端：DATABASE 标签 + 竖分隔 + 库名
  ctx.fillStyle = theme.ink.muted
  ctx.font = `500 9px ${MONO_STACK}`
  const labelX = x + 16
  const labelWidth = drawTracked(ctx, 'DATABASE', labelX, midY, 2)

  const dividerX = labelX + labelWidth + 12
  ctx.strokeStyle = theme.ink.line
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(dividerX + 0.5, y + 8)
  ctx.lineTo(dividerX + 0.5, y + DB_BAR_H - 8)
  ctx.stroke()

  const titleX = dividerX + 12
  const titleMaxWidth = itemsRight - 16 - titleX
  ctx.fillStyle = theme.ink.text
  const titleText = fitText(ctx, title, Math.max(40, titleMaxWidth), 13, 9)
  ctx.fillText(titleText, titleX, midY)
}

/**
 * 右上角的一图流二维码，做成档案里贴的资料标。
 *
 * 底板固定用浅色、模块固定用深色，保证任何模板下都能被扫码识别
 * （深色模板的 plate/text 是反色的，不能直接跟模板走）。四角强调色
 * 角标与卡片上的基质图标同一套语言。
 */
function drawQrTag(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  x: number,
  y: number,
): void {
  chamferPath(ctx, x, y, QR_BOX, QR_BOX, 6, [false, true, false, true])
  ctx.fillStyle = QR_PLATE
  ctx.fill()
  ctx.strokeStyle = theme.ink.line
  ctx.lineWidth = 1
  ctx.stroke()

  // 模块点阵，从静区之后开始铺
  ctx.fillStyle = QR_MODULE_COLOR
  const originX = x + QR_QUIET * QR_MODULE
  const originY = y + QR_QUIET * QR_MODULE
  for (const [row, bits] of YITULIU_QR.entries()) {
    for (const [column, bit] of [...bits].entries()) {
      if (bit === '1') {
        ctx.fillRect(originX + column * QR_MODULE, originY + row * QR_MODULE, QR_MODULE, QR_MODULE)
      }
    }
  }

  const tick = 7
  ctx.strokeStyle = theme.ink.accent
  ctx.lineWidth = 2
  ctx.beginPath()
  for (const [cornerX, cornerY, dirX, dirY] of [
    [x, y, 1, 1],
    [x + QR_BOX, y, -1, 1],
    [x + QR_BOX, y + QR_BOX, -1, -1],
    [x, y + QR_BOX, 1, -1],
  ] as const) {
    ctx.moveTo(cornerX + dirX * tick, cornerY)
    ctx.lineTo(cornerX, cornerY)
    ctx.lineTo(cornerX, cornerY + dirY * tick)
  }
  ctx.stroke()

  // 站点名与地址：二维码扫不了时还能手打
  ctx.textAlign = 'right'
  ctx.textBaseline = 'top'
  ctx.fillStyle = theme.ink.muted
  ctx.font = `500 9px ${FONT_STACK}`
  ctx.fillText(YITULIU_NAME, x + QR_BOX, y + QR_BOX + 4)
  ctx.fillStyle = withAlpha(theme.ink.muted, 0.75)
  ctx.font = `400 8px ${MONO_STACK}`
  ctx.fillText(YITULIU_URL, x + QR_BOX, y + QR_BOX + 15)
}

/**
 * 档案抬头：机构名 + 英文 + 细线 + 归档时间。
 *
 * @param maxWidth 可用宽度；窄图里二维码和大标题会挤掉它，压不进就整块不画，
 *   宁可少一行辅助信息也不要和旁边的元素叠在一起。
 */
function drawArchiveStamp(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  timestamp: string,
  right: number,
  y: number,
  maxWidth: number,
): void {
  if (maxWidth < 90) return

  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'

  ctx.fillStyle = theme.ink.muted
  ctx.font = `700 12px ${FONT_STACK}`
  ctx.fillText(ARCHIVE_ORG, right, y + 8)

  ctx.fillStyle = withAlpha(theme.ink.muted, 0.75)
  ctx.font = `500 9px ${MONO_STACK}`
  const enWidth = Math.min(measureTracked(ctx, ARCHIVE_ORG_EN, 1.6), maxWidth)
  ctx.textAlign = 'left'
  drawTracked(ctx, ARCHIVE_ORG_EN, right - enWidth, y + 25, 1.6)

  const lineLeft = right - Math.min(Math.max(enWidth, 150), maxWidth)
  drawHairline(ctx, theme.ink.line, lineLeft, y + 35, right, y + 35)
  // 线左端的强调色起点，与左侧品牌区的竖线呼应
  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(lineLeft, y + 33, 14, 2)

  ctx.fillStyle = withAlpha(theme.ink.muted, 0.8)
  ctx.font = `400 9px ${MONO_STACK}`
  ctx.textAlign = 'right'
  ctx.fillText(timestamp, right, y + 47)
}

/** 画整个页头区：品牌块 + 档案抬头 + 二维码 + 数据库栏 */
function drawHeader(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  input: MatrixExportInput,
  count: number,
  x: number,
  y: number,
  width: number,
): void {
  if (theme.decorations.brushGlyph) {
    drawBrushGlyph(ctx, theme, x, y, width, HEADER_H - DB_BAR_H - 24)
  }

  // 大标题左侧的强调色竖线：全图第一个视觉锚点
  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(x, y + 2, 4, 30)

  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = theme.ink.text
  ctx.font = `800 27px ${FONT_STACK}`
  ctx.fillText(BRAND_TITLE, x + 15, y + 17)

  ctx.fillStyle = theme.ink.muted
  ctx.font = `500 10px ${MONO_STACK}`
  drawTracked(ctx, BRAND_TITLE_EN, x + 16, y + 41, 3.4)

  // 标题下的强调色短横线，收住整个品牌块
  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(x + 16, y + 51, 38, 3)

  const qrX = x + width - QR_BOX
  if (theme.decorations.qrTag) {
    drawQrTag(ctx, theme, qrX, y)
  }

  // 品牌块右边界固定按大标题宽度估，抬头从这里往右排
  const stampRight = qrX - 18
  drawArchiveStamp(ctx, theme, input.subtitle, stampRight, y, stampRight - (x + 145))

  drawDatabaseBar(ctx, theme, input.title, count, x, y + HEADER_H - DB_BAR_H - 22, width)
}

/**
 * 页脚：上行是标识与档案编号，下行是仓库地址与署名。
 *
 * 两行各自左右对齐、中间留空，窄图里也只是间距变小，不会互相压字。
 */
function drawFooter(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  count: number,
  x: number,
  y: number,
  width: number,
): void {
  drawHairline(ctx, theme.ink.line, x, y, x + width, y)
  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(x, y, 38, 2)

  const mainY = y + 22
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'left'

  ctx.fillStyle = theme.ink.text
  ctx.font = `800 12px ${MONO_STACK}`
  const brandWidth = drawTracked(ctx, 'EER', x, mainY, 1.5)

  ctx.fillStyle = theme.ink.muted
  ctx.font = `500 10px ${FONT_STACK}`
  const nameX = x + brandWidth + 10
  const nameWidth = ctx.measureText(`· ${PROJECT_NAME}`).width
  ctx.fillText(`· ${PROJECT_NAME}`, nameX, mainY)

  // 右侧档案编号
  ctx.textAlign = 'right'
  ctx.fillStyle = theme.ink.text
  ctx.font = `700 11px ${MONO_STACK}`
  const archiveNo = buildArchiveNo(count)
  const archiveWidth = ctx.measureText(archiveNo).width
  ctx.fillText(archiveNo, x + width, mainY)

  ctx.fillStyle = theme.ink.muted
  ctx.font = `400 9px ${FONT_STACK}`
  const labelRight = x + width - archiveWidth - 8
  ctx.fillText('档案编号', labelRight, mainY)
  const labelWidth = ctx.measureText('档案编号').width

  if (theme.decorations.hazardStripes) {
    const stripeLeft = nameX + nameWidth + 22
    const stripeRight = labelRight - labelWidth - 22
    drawHazardStripes(ctx, theme, stripeLeft, mainY - 5, stripeRight - stripeLeft, 10)
  }

  // 下行：左仓库、右署名，各占一半宽度
  const creditY = y + 47
  const half = (width - 16) / 2

  ctx.textAlign = 'left'
  ctx.fillStyle = withAlpha(theme.ink.muted, 0.8)
  ctx.fillText(fitText(ctx, PROJECT_REPO, half, 9, 7, 400, MONO_STACK), x, creditY)

  ctx.textAlign = 'right'
  ctx.fillStyle = theme.ink.muted
  ctx.fillText(fitText(ctx, CREDIT_LINE, half, 9, 7, 500), x + width, creditY)
}

// --- 卡片 ---

/**
 * 一张卡片实际使用的色值。
 *
 * 未获得的条目不是简单地整体调低透明度，而是换一套压向背景的色板：
 * 名称、边框、方格各自降到刚好还能辨认的程度，扫一眼就能把
 * 「已拥有 = 前景 / 未拥有 = 背景」分开，不用去读数字。
 */
interface CardInk {
  surface: string
  border: string
  borderInner: string
  name: string
  ruby: string
  trait: string
  pipIdle: string
  /** 位图（武器图、基质图）的绘制透明度 */
  imageAlpha: number
}

function cardInk(theme: MatrixExportTemplate, dimmed: boolean): CardInk {
  if (dimmed) {
    return {
      surface: theme.ink.surfaceDim,
      border: theme.dim.line,
      borderInner: 'transparent',
      name: theme.dim.text,
      ruby: theme.dim.muted,
      trait: theme.dim.muted,
      pipIdle: theme.pip.idleDim,
      imageAlpha: 0.4,
    }
  }
  return {
    surface: theme.ink.surface,
    border: theme.ink.line,
    borderInner: theme.ink.lineSoft,
    name: theme.ink.text,
    ruby: withAlpha(theme.ink.text, 0.32),
    trait: theme.ink.muted,
    pipIdle: theme.pip.idle,
    imageAlpha: 1,
  }
}

/**
 * 画武器 icon：图片 + 底部稀有度色条 + 细边框。
 *
 * 对应 ItemIcon.vue 的层叠结构，但去掉了发光渐变——工业面板上的
 * 缩略图就该是块平的铭牌图，稀有度只靠底部那条色带表达。
 */
function drawWeaponIcon(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  image: HTMLImageElement | null,
  card: ExportCard,
  ink: CardInk,
  x: number,
  y: number,
  size: number,
): void {
  if (!image) {
    drawImagePlaceholder(ctx, theme, x, y, size)
    return
  }

  const tierColor = safeColor(card.tierColor)

  ctx.save()
  ctx.beginPath()
  ctx.rect(x, y, size, size)
  ctx.clip()

  ctx.fillStyle = withAlpha(theme.ink.text, 0.04)
  ctx.fillRect(x, y, size, size)

  ctx.globalAlpha = ink.imageAlpha
  if (card.dimmed) ctx.filter = 'grayscale(1)'
  drawImageCover(ctx, image, x, y, size, size)
  ctx.filter = 'none'
  ctx.globalAlpha = 1

  // 底部稀有度色条：全图仅有的几处高饱和之一，负责物品识别
  const barHeight = Math.max(2, size * 0.055)
  ctx.fillStyle = card.dimmed ? withAlpha(tierColor, 0.35) : tierColor
  ctx.fillRect(x, y + size - barHeight, size, barHeight)

  ctx.restore()

  ctx.strokeStyle = ink.border
  ctx.lineWidth = 1
  ctx.strokeRect(x + 0.5, y + 0.5, size - 1, size - 1)
}

/**
 * 画基质图：底板 + 技能图标 + 强调色框体 + 四角角标。
 *
 * 对应 CustomStatIcon.vue 的层叠结构，技能图标沿用 translate(5%, -5%) 的偏移。
 * 框体和角标是卡片内的第二视觉锚点——先看到名称，再被引到这枚核心基质上。
 *
 * @param accent 底部识别条的颜色：内置武器用强调色，自定义基质用它自己的橙。
 */
function drawEssenceIcon(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  bgImage: HTMLImageElement | null,
  skillImage: HTMLImageElement | null,
  ink: CardInk,
  accent: string,
  dimmed: boolean,
  x: number,
  y: number,
  size: number,
): void {
  if (!bgImage && !skillImage) {
    drawImagePlaceholder(ctx, theme, x, y, size)
    return
  }

  ctx.save()
  ctx.beginPath()
  ctx.rect(x, y, size, size)
  ctx.clip()

  ctx.fillStyle = theme.ink.plate
  ctx.fillRect(x, y, size, size)

  ctx.globalAlpha = ink.imageAlpha
  if (dimmed) ctx.filter = 'grayscale(1)'
  if (bgImage) drawImageCover(ctx, bgImage, x, y, size, size)
  if (skillImage) {
    drawImageCover(ctx, skillImage, x + size * 0.05, y - size * 0.05, size, size)
  }
  ctx.filter = 'none'
  ctx.globalAlpha = 1

  const barHeight = Math.max(2, size * 0.055)
  ctx.fillStyle = dimmed ? withAlpha(accent, 0.35) : accent
  ctx.fillRect(x, y + size - barHeight, size, barHeight)

  ctx.restore()

  // 强调色框体
  const frameColor = dimmed ? withAlpha(theme.ink.accent, 0.3) : theme.ink.accent
  ctx.strokeStyle = frameColor
  ctx.lineWidth = 1.5
  ctx.strokeRect(x + 0.75, y + 0.75, size - 1.5, size - 1.5)

  // 四角角标：把「这是核心基质」再点一次，不靠加粗边框硬顶
  const tick = 7
  ctx.strokeStyle = frameColor
  ctx.lineWidth = 2
  ctx.beginPath()
  for (const [cornerX, cornerY, dirX, dirY] of [
    [x, y, 1, 1],
    [x + size, y, -1, 1],
    [x + size, y + size, -1, -1],
    [x, y + size, 1, -1],
  ] as const) {
    ctx.moveTo(cornerX + dirX * tick, cornerY)
    ctx.lineTo(cornerX, cornerY)
    ctx.lineTo(cornerX, cornerY + dirY * tick)
  }
  ctx.stroke()
}

/**
 * 画一行方格能量条。
 *
 * 直角实心块、无发光：色块长度本身就是可读的量，扫一眼就知道高低，
 * 不必真去读 6/6 那个数字。未激活块只降对比度、不消失，槽位总数才留得住。
 */
function drawPipRow(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  level: number,
  pipCount: number,
  activeColor: string,
  ink: CardInk,
  dimmed: boolean,
  x: number,
  y: number,
): void {
  for (let index = 0; index < pipCount; index++) {
    const pipX = x + index * (PIP_W + PIP_GAP)
    const active = index < level

    ctx.fillStyle = active ? (dimmed ? withAlpha(activeColor, 0.32) : activeColor) : ink.pipIdle
    ctx.fillRect(pipX, y, PIP_W, PIP_H)
  }

  ctx.fillStyle = dimmed ? ink.trait : withAlpha(theme.ink.text, 0.62)
  ctx.font = `700 10px ${MONO_STACK}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(`${level}/${pipCount}`, x + pipCount * (PIP_W + PIP_GAP) + 5, y + PIP_H / 2)
}

/**
 * 满级标记：强调色双线框 + 右上切角实心三角。
 *
 * 页面上用的是彩虹环，但彩虹渐变落在灰白工业底上会盖过所有数据。
 * 这里改用「已认证」式的强调色标识，纳入全图统一的强调色锚点体系。
 */
function drawMaxedMark(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const chamfer = theme.cardChamfer
  chamferPath(ctx, x + 1, y + 1, width - 2, height - 2, chamfer - 1)
  ctx.strokeStyle = theme.ink.accent
  ctx.lineWidth = 1.5
  ctx.stroke()

  chamferPath(ctx, x + 3.5, y + 3.5, width - 7, height - 7, chamfer - 3)
  ctx.strokeStyle = withAlpha(theme.ink.accent, 0.32)
  ctx.lineWidth = 1
  ctx.stroke()

  // 右上切角处的实心三角，等同档案上的「已归档」戳
  ctx.fillStyle = theme.ink.accent
  ctx.beginPath()
  ctx.moveTo(x + width - chamfer - 8, y + 1)
  ctx.lineTo(x + width - 1, y + chamfer + 8)
  ctx.lineTo(x + width - 1, y + chamfer)
  ctx.lineTo(x + width - chamfer, y + 1)
  ctx.closePath()
  ctx.fill()
}

/** 扫描数量角标：强调色切角方块 + 深色数字 */
function drawBadge(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  count: number,
  centerX: number,
  centerY: number,
): void {
  const size = BADGE_R * 2
  chamferPath(ctx, centerX - BADGE_R, centerY - BADGE_R, size, size, 5, [true, false, true, false])
  ctx.fillStyle = theme.ink.accent
  ctx.fill()

  ctx.fillStyle = theme.ink.accentInk
  ctx.font = `700 10px ${MONO_STACK}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(count > 99 ? '99+' : String(count), centerX, centerY)
}

/**
 * 处理词条名称：去掉"提升"后缀以缩短显示长度。
 *
 * "攻击力提升" → "攻击"
 * "终结技充能效率提升" → "终结技充能效率"
 * "巧技" → "巧技"（无"提升"则保持不变）
 */
function shortenTraitName(name: string): string {
  if (name.endsWith('提升')) {
    return name.slice(0, -2)
  }
  return name
}

/**
 * 画一整张卡片。
 *
 * 内部视觉顺序刻意做成 名称 → 武器 → 核心基质 → 数据：
 * 星级虽然靠上但压得最淡，第一眼落到的应该是名字。
 */
function drawCard(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  card: ExportCard,
  images: Map<string, HTMLImageElement | null>,
  x: number,
  y: number,
): void {
  const ink = cardInk(theme, card.dimmed === true)
  const dimmed = card.dimmed === true
  const chamfer = theme.cardChamfer

  // 无条件成对 save/restore：filter/globalAlpha 是全局状态，
  // 漏掉 restore 会让后面所有卡片跟着变样。
  ctx.save()

  // 卡面：薄金属铭牌——直角为主，只切右上角
  chamferPath(ctx, x, y, CARD_W, CARD_H, chamfer)
  ctx.fillStyle = ink.surface
  ctx.fill()
  ctx.strokeStyle = ink.border
  ctx.lineWidth = 1
  ctx.stroke()

  // 内衬线：一圈退进 3px 的更淡描边，做出金属框的厚度
  if (ink.borderInner !== 'transparent') {
    chamferPath(ctx, x + 3, y + 3, CARD_W - 6, CARD_H - 6, chamfer - 3)
    ctx.strokeStyle = ink.borderInner
    ctx.lineWidth = 1
    ctx.stroke()
  }

  const nameMaxWidth = CARD_W - CARD_PAD * 2

  // 注音行：星级压到名称上方，透明度低到不与名称抢视线
  if (card.nameRuby) {
    const rubyText = fitText(ctx, card.nameRuby, nameMaxWidth, RUBY_FONTSIZE, 7)
    ctx.fillStyle = ink.ruby
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(rubyText, x + CARD_W / 2, y + CARD_PAD + RUBY_H / 2)
  }

  // 名称：卡片内最重的文字
  const nameText = fitText(ctx, card.name, nameMaxWidth, 15, 10, 800)
  ctx.fillStyle = ink.name
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(nameText, x + CARD_W / 2, y + CARD_PAD + RUBY_H + NAME_H / 2)

  const bodyY = y + CARD_PAD + RUBY_H + NAME_H + 4
  const iconImage = card.iconUrl ? (images.get(card.iconUrl) ?? null) : null
  const bgImage = card.essenceBgUrl ? (images.get(card.essenceBgUrl) ?? null) : null
  const skillImage = card.skillIconUrl ? (images.get(card.skillIconUrl) ?? null) : null

  let pipX: number
  if (card.kind === 'weapon') {
    const iconX = x + CARD_PAD
    drawWeaponIcon(ctx, theme, iconImage, card, ink, iconX, bodyY, ICON)

    const essenceX = iconX + ICON + 10
    const essenceY = bodyY + (ICON - MATRIX_ICON) / 2
    drawEssenceIcon(
      ctx,
      theme,
      bgImage,
      skillImage,
      ink,
      theme.ink.accent,
      dimmed,
      essenceX,
      essenceY,
      MATRIX_ICON,
    )
    pipX = essenceX + MATRIX_ICON + 12

    if (card.badgeCount && card.badgeCount > 0) {
      drawBadge(ctx, theme, card.badgeCount, iconX + ICON, bodyY)
    }
  } else {
    // 自定义基质没有武器图，基质图放大占据 icon 的位置；
    // 底条保留它自己的橙，作为「这是自定义项」的识别色
    const essenceX = x + CARD_PAD
    drawEssenceIcon(
      ctx,
      theme,
      bgImage,
      skillImage,
      ink,
      safeColor(card.tierColor),
      dimmed,
      essenceX,
      bodyY,
      ICON,
    )
    pipX = essenceX + ICON + 12
  }

  // 三行方格能量条
  for (let slot = 0; slot < 3; slot++) {
    drawPipRow(
      ctx,
      theme,
      card.levels[slot] ?? 0,
      AFFIX_PIP_COUNT[slot]!,
      theme.pip.colors[slot]!,
      ink,
      dimmed,
      pipX,
      bodyY + slot * PIP_ROW_GAP,
    )
  }

  // 底部词条名
  if (card.traitNames && card.traitNames.length > 0) {
    const traitText = card.traitNames.map((name) => shortenTraitName(name)).join(' · ')
    const traitMaxWidth = CARD_W - CARD_PAD * 2
    const traitY = y + CARD_H - CARD_PAD - 4
    ctx.fillStyle = ink.trait
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    const fittedText = fitText(ctx, traitText, traitMaxWidth, TRAIT_FONTSIZE, 10, 400)
    ctx.fillText(fittedText, x + CARD_W / 2, traitY)
  }

  if (card.maxed && !dimmed) drawMaxedMark(ctx, theme, x, y, CARD_W, CARD_H)

  ctx.restore()
}

/**
 * 画区标题，返回下一个可用的 y 坐标。
 *
 * 结构与页头同源：强调色块起头、中英双行、延伸线收尾、右端计数。
 */
function drawSectionHeader(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  text: string,
  textEn: string,
  count: number,
  x: number,
  y: number,
  width: number,
): number {
  const midY = y + SECTION_HEAD_H / 2 + 2

  ctx.fillStyle = theme.ink.accent
  ctx.fillRect(x, midY - 7, 4, 14)

  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = theme.ink.text
  ctx.font = `700 14px ${FONT_STACK}`
  const titleWidth = ctx.measureText(text).width
  ctx.fillText(text, x + 12, midY)

  ctx.fillStyle = withAlpha(theme.ink.muted, 0.75)
  ctx.font = `500 9px ${MONO_STACK}`
  const enX = x + 12 + titleWidth + 10
  const enWidth = drawTracked(ctx, textEn, enX, midY + 1, 1.8)

  // 右端计数，先测宽度才能定延伸线的终点
  ctx.textAlign = 'right'
  ctx.fillStyle = theme.ink.muted
  ctx.font = `700 10px ${MONO_STACK}`
  const countText = `${count} ITEMS`
  const countWidth = ctx.measureText(countText).width
  ctx.fillText(countText, x + width, midY)

  drawHairline(
    ctx,
    theme.ink.line,
    enX + enWidth + 12,
    midY - 1,
    x + width - countWidth - 12,
    midY - 1,
  )

  return y + SECTION_HEAD_H
}

/** 画一个网格区，返回下一个可用的 y 坐标 */
function drawGrid(
  ctx: CanvasRenderingContext2D,
  theme: MatrixExportTemplate,
  cards: readonly ExportCard[],
  images: Map<string, HTMLImageElement | null>,
  columns: number,
  y: number,
): number {
  for (const [index, card] of cards.entries()) {
    const row = Math.floor(index / columns)
    const column = index % columns
    drawCard(ctx, theme, card, images, PAGE_PAD + column * (CARD_W + GAP), y + row * (CARD_H + GAP))
  }

  const rows = Math.ceil(cards.length / columns)
  return y + rows * (CARD_H + GAP) - GAP
}

/**
 * 把宝藏基质卡片渲染成一张导出图。
 *
 * @param input 卡片数据、页头文案与所选模板。
 * @returns 导出图 Blob（WebP，不支持时回退 PNG）、预览用 object URL 及实际尺寸。
 * @throws 卡片为空、或画布导出失败时抛出。
 */
export async function renderMatrixExport(input: MatrixExportInput): Promise<MatrixExportResult> {
  const { weapons, customs } = input
  const allCards = [...weapons, ...customs]
  if (allCards.length === 0) {
    throw new Error('没有可导出的条目')
  }

  const theme = resolveTemplate(input.template)
  const columns = input.columns ?? pickColumns(allCards.length)
  const { width, height } = computeCanvasSize(weapons.length, customs.length, columns)

  const images = await preloadImages(allCards)
  let missingImages = 0
  for (const image of images.values()) {
    if (!image) missingImages++
  }

  // 固定倍率而非跟随 devicePixelRatio：同一份数据在任何机器上都应产出同样的图
  const requestedScale = input.scale ?? 2
  const scale = Math.max(1, Math.min(requestedScale, MAX_DEVICE_PX / Math.max(width, height)))

  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法创建画布上下文')

  // 缩放一次之后，下面所有布局数学都按 CSS 像素来写
  ctx.scale(scale, scale)

  drawPaper(ctx, theme, width, height)

  const gridWidth = width - PAGE_PAD * 2
  drawHeader(ctx, theme, input, allCards.length, PAGE_PAD, PAGE_PAD, gridWidth)

  let cursorY = PAGE_PAD + HEADER_H

  if (weapons.length > 0) {
    cursorY = drawSectionHeader(
      ctx,
      theme,
      '内置武器',
      'BUILT-IN WEAPONS',
      weapons.length,
      PAGE_PAD,
      cursorY,
      gridWidth,
    )
    cursorY = drawGrid(ctx, theme, weapons, images, columns, cursorY)
  }

  if (customs.length > 0) {
    if (weapons.length > 0) cursorY += SECTION_GAP
    cursorY = drawSectionHeader(
      ctx,
      theme,
      '自定义基质',
      'CUSTOM MATRICES',
      customs.length,
      PAGE_PAD,
      cursorY,
      gridWidth,
    )
    cursorY = drawGrid(ctx, theme, customs, images, columns, cursorY)
  }

  drawFooter(ctx, theme, allCards.length, PAGE_PAD, cursorY + SECTION_GAP, gridWidth)

  const blob = await canvasToBlob(canvas, EXPORT_MIME, EXPORT_QUALITY)
  return {
    blob,
    objectUrl: URL.createObjectURL(blob),
    width,
    height,
    scale,
    missingImages,
  }
}
