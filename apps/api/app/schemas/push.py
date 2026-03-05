from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(..., min_length=1)
    auth: str = Field(..., min_length=1)


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=500)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=500)


class PushSubscriptionResponse(BaseModel):
    id: uuid.UUID
    endpoint: str
    created_at: datetime


class VapidKeyResponse(BaseModel):
    public_key: str
