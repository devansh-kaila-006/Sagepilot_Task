from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class SupervisorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the supervisor")
    base_instruction: str = Field(..., min_length=1, description="Base prompt instructions")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Optional configurations")

class SupervisorCreate(SupervisorBase):
    pass

class SupervisorResponse(SupervisorBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RunCreate(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=100, description="The order identifier")
    supervisor_id: int = Field(..., gt=0, description="ID of the supervisor template")

class RunResponse(BaseModel):
    id: str
    order_id: str
    supervisor_id: int
    status: str
    state: Dict[str, Any]
    next_wake_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ActivityCreate(BaseModel):
    type: str = Field(..., min_length=1, description="Type of activity")
    payload: Dict[str, Any] = Field(..., description="Payload data")

class ActivityResponse(BaseModel):
    id: int
    run_id: str
    type: str
    payload: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
