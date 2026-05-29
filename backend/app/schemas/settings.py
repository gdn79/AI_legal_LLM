from pydantic import BaseModel


class SettingRead(BaseModel):
    key: str
    value: str
    description: str

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    value: str
    description: str = ""
