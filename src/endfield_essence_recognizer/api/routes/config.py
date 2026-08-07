from fastapi import APIRouter, Body, Depends, HTTPException

from endfield_essence_recognizer.api.routes.profiles import get_profile_manager
from endfield_essence_recognizer.dependencies import get_user_setting_manager_dep
from endfield_essence_recognizer.exceptions import ConfigVersionMismatchError
from endfield_essence_recognizer.schemas.user_setting import UserSetting
from endfield_essence_recognizer.services.user_setting_manager import UserSettingManager

router = APIRouter(prefix="/config", tags=["user setting"])


@router.get("")
async def get_config(
    user_setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
) -> UserSetting:
    return user_setting_manager.get_user_setting_ref()


@router.post("")
async def post_config(
    new_config: UserSetting = Body(),
    user_setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
) -> UserSetting:
    try:
        user_setting_manager.update_from_user_setting(new_config)
    except ConfigVersionMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return user_setting_manager.get_user_setting_ref()


@router.post("/reset")
async def reset_config(
    user_setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
) -> UserSetting:
    """将所有设置重置为默认值。

    自定义基质会随配置清空，因此同时清理所有账号中残留的 `custom:` 引用，
    避免界面出现指向不存在基质的幽灵条目。
    """
    user_setting_manager.reset_to_default()
    get_profile_manager().remove_custom_stat_refs()
    return user_setting_manager.get_user_setting_ref()
