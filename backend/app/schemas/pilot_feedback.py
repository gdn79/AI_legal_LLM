from datetime import datetime

from pydantic import BaseModel


class PilotFeedbackCreate(BaseModel):
    case_id: int | None = None
    module: str
    severity: str
    title: str
    description: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""


class PilotFeedbackUpdate(BaseModel):
    module: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    status: str | None = None


class PilotFeedbackScreenshotAttach(BaseModel):
    screenshot_document_id: int


class PilotFeedbackRead(BaseModel):
    id: int
    case_id: int | None
    user_id: int
    role: str
    module: str
    severity: str
    title: str
    description: str
    expected_behavior: str
    actual_behavior: str
    screenshot_document_id: int | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
