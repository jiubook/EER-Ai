<template>
  <div class="matrix-export">
    <v-card density="compact" variant="outlined">
      <v-card-title class="text-subtitle-2 d-flex align-center">
        <v-icon class="mr-2" size="small">mdi-download</v-icon>
        导出数据
      </v-card-title>

      <v-card-text class="pa-2">
        <div class="d-flex flex-column gap-2">
          <!-- 导出为 CSV -->
          <v-btn
            block
            color="primary"
            :loading="exportingCSV"
            prepend-icon="mdi-file-delimited"
            size="small"
            variant="tonal"
            @click="exportCSV"
          >
            导出为 CSV
          </v-btn>

          <!-- 导出为 JSON -->
          <v-btn
            block
            color="secondary"
            :loading="exportingJSON"
            prepend-icon="mdi-code-json"
            size="small"
            variant="tonal"
            @click="exportJSON"
          >
            导出为 JSON
          </v-btn>

          <!-- 导出为图片 -->
          <v-btn
            block
            color="accent"
            :disabled="!targetElement"
            :loading="exportingImage"
            prepend-icon="mdi-image"
            size="small"
            variant="tonal"
            @click="exportImage"
          >
            导出为图片
          </v-btn>

          <!-- 导出说明 -->
          <div class="text-caption text-grey mt-2">
            <div class="d-flex align-center mb-1">
              <v-icon class="mr-1" size="x-small">mdi-information-outline</v-icon>
              导出说明
            </div>
            <ul class="export-tips">
              <li>CSV: 可在 Excel 中打开分析</li>
              <li>JSON: 包含完整数据结构</li>
              <li>图片: 截取当前矩阵视图</li>
            </ul>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// ============================================================================
// 类型定义
// ============================================================================

interface MatrixCellData {
  code: string
  weapon_id: string | null
  weapon_name: string | null
  weapon_rarity: number | null
  weapon_type: string | null
  attribute_id: string
  attribute_name: string
  attribute_level: number
  secondary_id: string
  secondary_name: string
  secondary_level: number
  skill_id: string
  skill_name: string
  skill_level: number
  owned: boolean
  is_max_level: boolean
}

// ============================================================================
// Props
// ============================================================================

const props = defineProps<{
  targetElement?: HTMLElement
  matrixData?: Record<string, MatrixCellData>
}>()

// ============================================================================
// 状态
// ============================================================================

const exportingCSV = ref(false)
const exportingJSON = ref(false)
const exportingImage = ref(false)

// ============================================================================
// 方法
// ============================================================================

async function exportCSV() {
  exportingCSV.value = true
  try {
    // 获取矩阵数据
    let data = props.matrixData
    if (!data) {
      const response = await fetch('/api/profiles/matrix_view')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const result = await response.json()
      data = result.matrix
    }

    // 构建CSV内容
    const headers = [
      '编码',
      '基础属性',
      '基础属性等级',
      '附加属性',
      '附加属性等级',
      '技能属性',
      '技能属性等级',
      '武器ID',
      '武器名称',
      '武器稀有度',
      '武器类型',
      '已拥有',
      '满级',
    ]

    const rows = Object.values(data || {}).map(cell => [
      cell.code,
      cell.attribute_name,
      cell.attribute_level,
      cell.secondary_name,
      cell.secondary_level,
      cell.skill_name,
      cell.skill_level,
      cell.weapon_id || '',
      cell.weapon_name || '',
      cell.weapon_rarity || '',
      cell.weapon_type || '',
      cell.owned ? '是' : '否',
      cell.is_max_level ? '是' : '否',
    ])

    // 添加BOM以支持中文
    const BOM = '﻿'
    const csvContent = BOM + headers.join(',') + '\n' + rows.map(row => row.join(',')).join('\n')

    // 下载文件
    downloadFile(csvContent, '宝藏基质矩阵.csv', 'text/csv;charset=utf-8;')
  } catch (error) {
    console.error('Failed to export CSV:', error)
  } finally {
    exportingCSV.value = false
  }
}

async function exportJSON() {
  exportingJSON.value = true
  try {
    // 获取矩阵数据
    let data = props.matrixData
    if (!data) {
      const response = await fetch('/api/profiles/matrix_view')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const result = await response.json()
      data = result.matrix
    }

    // 构建JSON内容
    const jsonContent = JSON.stringify(data, null, 2)

    // 下载文件
    downloadFile(jsonContent, '宝藏基质矩阵.json', 'application/json;charset=utf-8;')
  } catch (error) {
    console.error('Failed to export JSON:', error)
  } finally {
    exportingJSON.value = false
  }
}

async function exportImage() {
  if (!props.targetElement) {
    console.warn('No target element provided for image export')
    return
  }

  exportingImage.value = true
  try {
    // 动态导入html2canvas
    const html2canvas = (await import('html2canvas')).default

    // 截取元素
    const canvas = await html2canvas(props.targetElement, {
      backgroundColor: '#ffffff',
      scale: 2, // 提高清晰度
      useCORS: true,
      logging: false,
    })

    // 转换为图片并下载
    const image = canvas.toDataURL('image/png')
    const link = document.createElement('a')
    link.href = image
    link.download = '宝藏基质矩阵.png'
    link.click()
  } catch (error) {
    console.error('Failed to export image:', error)
    alert('导出图片失败，请确保已安装html2canvas库')
  } finally {
    exportingImage.value = false
  }
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.matrix-export {
  width: 100%;
}

.export-tips {
  padding-left: 16px;
  margin: 0;
}

.export-tips li {
  margin-bottom: 4px;
}
</style>
