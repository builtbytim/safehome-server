from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import SettingsConfigDict


class UploadImageOutput(BaseModel):
    url: str
    public_id: str = Field(alias="publicId")
    secure_url: str = Field(alias="secureUrl")

    model_config = SettingsConfigDict(populate_by_name=True)


class UploadImageInput(BaseModel):
    image: str
    folder: str
    public_id: str = Field(alias="publicId")
    upload_preset: str = Field(alias="uploadPreset")

    model_config = SettingsConfigDict(populate_by_name=True)
