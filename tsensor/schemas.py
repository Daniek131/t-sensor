from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class OrganizationInput(Input):
    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=100)]


class DeviceInput(Input):
    id: Identifier


class Measurements(Input):
    moisture: Annotated[float, Field(ge=0, le=100)]
    temperature: Annotated[float, Field(ge=-50, le=100)]
    ec: Annotated[int, Field(ge=0, le=65535, strict=True)]
    ph: Annotated[float, Field(ge=0, le=14)]
    nitrogen: Annotated[int, Field(ge=0, le=65535, strict=True)]
    phosphorus: Annotated[int, Field(ge=0, le=65535, strict=True)]
    potassium: Annotated[int, Field(ge=0, le=65535, strict=True)]


class ReadingInput(Measurements):
    observed_at: datetime
    source: Literal["hardware", "synthetic", "replay"]
    raw_frame_hex: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{38}$")] | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Timestamp is more than five minutes in the future")
        return value.astimezone(timezone.utc)


class FrameInput(Input):
    frame_hex: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{38}$")]
    observed_at: datetime
    address: Annotated[int, Field(ge=1, le=247)] = 1
    source: Literal["hardware", "synthetic", "replay"] = "replay"
