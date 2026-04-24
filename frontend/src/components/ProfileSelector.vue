<template>
  <v-menu>
    <template #activator="{ props }">
      <v-btn prepend-icon="mdi-account-switch" variant="text" v-bind="props">
        {{ activeProfileName }}
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>
    <v-list density="compact">
      <v-list-subheader>切换账号</v-list-subheader>
      <v-list-item
        v-for="name in profileNames"
        :key="name"
        :active="name === activeProfileName"
        @click="onSwitch(name)"
      >
        <template #prepend>
          <v-icon :icon="name === activeProfileName ? 'mdi-account-check' : 'mdi-account'" />
        </template>
        <v-list-item-title>{{ name }}</v-list-item-title>
        <template #append>
          <div class="d-flex ga-1">
            <v-btn
              v-if="name !== 'default'"
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              @click.stop="startRename(name)"
            />
            <v-btn
              v-if="name !== 'default'"
              color="error"
              icon="mdi-delete"
              size="x-small"
              variant="text"
              @click.stop="startDelete(name)"
            />
          </div>
        </template>
      </v-list-item>
      <v-divider />
      <v-list-item @click="showNewProfileDialog = true">
        <template #prepend>
          <v-icon icon="mdi-plus" />
        </template>
        <v-list-item-title>新建账号</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>

  <!-- 新建账号对话框 -->
  <v-dialog v-model="showNewProfileDialog" max-width="400">
    <v-card>
      <v-card-title>新建账号</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="newProfileName"
          label="账号名称"
          :rules="[(v) => !!v.trim() || '名称不能为空']"
          variant="outlined"
          @keyup.enter="onCreate"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="showNewProfileDialog = false">取消</v-btn>
        <v-btn color="primary" :disabled="!newProfileName.trim()" @click="onCreate">
          创建
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 重命名对话框 -->
  <v-dialog v-model="showRenameDialog" max-width="400">
    <v-card>
      <v-card-title>重命名账号</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="renameNewName"
          label="新名称"
          :rules="[(v) => !!v.trim() || '名称不能为空']"
          variant="outlined"
          @keyup.enter="onRename"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="showRenameDialog = false">取消</v-btn>
        <v-btn color="primary" :disabled="!renameNewName.trim()" @click="onRename">
          确认
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 删除确认对话框 -->
  <v-dialog v-model="showDeleteConfirm" max-width="400">
    <v-card>
      <v-card-title class="text-error">确认删除</v-card-title>
      <v-card-text>
        确定要删除账号「{{ deleteTargetName }}」吗？此操作不可撤销。
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="showDeleteConfirm = false">取消</v-btn>
        <v-btn color="error" @click="onDelete">删除</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { useProfiles } from '@/composables/useProfiles'

const {
  activeProfileName,
  profileNames,
  fetchProfiles,
  switchProfile,
  renameProfile,
  deleteProfile,
} = useProfiles()

// 账号名称最大长度
const PROFILE_NAME_MAX_LEN = 32
// 账号名称非法字符正则表达式
const PROFILE_NAME_INVALID_RE = /[/\\\u0000\n\r\t]/

const showNewProfileDialog = ref(false)
const showRenameDialog = ref(false)
const showDeleteConfirm = ref(false)
const newProfileName = ref('')
const renameNewName = ref('')
const renameOldName = ref('')
const deleteTargetName = ref('')

/**
 * 验证账号名称是否合法。
 * @param name 账号名称
 * @returns 错误信息，如果合法则返回 null
 */
function validateProfileName(name: string): string | null {
  const trimmed = name.trim()
  if (!trimmed) return '名称不能为空'
  if (trimmed.length > PROFILE_NAME_MAX_LEN) return `名称不能超过 ${PROFILE_NAME_MAX_LEN} 个字符`
  if (PROFILE_NAME_INVALID_RE.test(trimmed)) return '名称包含非法字符'
  return null
}

onMounted(() => {
  fetchProfiles()
})

/**
 * 切换到指定账号。
 */
async function onSwitch(name: string) {
  try {
    await switchProfile(name)
  } catch (error: any) {
    alert(error.message || '切换失败')
  }
}

/**
 * 创建新账号。
 */
async function onCreate() {
  const name = newProfileName.value.trim()
  const validationError = validateProfileName(name)
  if (validationError) {
    alert(validationError)
    return
  }
  try {
    await switchProfile(name)
    showNewProfileDialog.value = false
    newProfileName.value = ''
  } catch (error_: any) {
    alert(error_.message || '创建失败')
  }
}

/**
 * 开始重命名账号。
 */
function startRename(name: string) {
  renameOldName.value = name
  renameNewName.value = name
  showRenameDialog.value = true
}

/**
 * 执行重命名操作。
 */
async function onRename() {
  const newName = renameNewName.value.trim()
  const validationError = validateProfileName(newName)
  if (validationError) {
    alert(validationError)
    return
  }
  try {
    await renameProfile(renameOldName.value, newName)
    showRenameDialog.value = false
  } catch (error_: any) {
    alert(error_.message || '重命名失败')
  }
}

/**
 * 开始删除账号。
 */
function startDelete(name: string) {
  deleteTargetName.value = name
  showDeleteConfirm.value = true
}

/**
 * 执行删除操作。
 */
async function onDelete() {
  try {
    await deleteProfile(deleteTargetName.value)
    showDeleteConfirm.value = false
  } catch (error: any) {
    alert(error.message || '删除失败')
  }
}
</script>
