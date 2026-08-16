from pydantic import BaseModel, Field


class TreasureMatrixExportRequest(BaseModel):
    image_base64: str = Field(
        description="PNG 图片内容的 base64 编码（不含 data URI 前缀）",
    )
    open_folder: bool = Field(
        default=True,
        description="保存成功后是否打开图片所在的文件夹",
    )


class TreasureMatrixExportResponse(BaseModel):
    success: bool
    message: str
    file_path: str | None = Field(
        default=None,
        description="保存的导出图片的完整路径",
    )
    file_name: str | None = Field(
        default=None,
        description="保存的导出图片文件名",
    )
