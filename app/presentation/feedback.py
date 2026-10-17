"""Private aggregate feedback boundary, independent of public collection."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.feedback import FeedbackReadPort
from app.presentation.operations import authorize

router = APIRouter(include_in_schema=False)


class FeedbackView(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[1] = 1
    project: Literal['portfolio'] = 'portfolio'
    basis: Literal['retained_answer_creation'] = 'retained_answer_creation'
    window_days: Literal[7] = 7
    observed_at: str = Field(max_length=40)
    up: int = Field(ge=0, le=10**12)
    down: int = Field(ge=0, le=10**12)

    @field_validator('observed_at')
    @classmethod
    def timezone(cls, value: str) -> str:
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError('timezone_required')
        return value


@router.get(
    '/internal/ops/v1/feedback',
    response_model=FeedbackView,
    dependencies=[Depends(authorize)],
)
def read_feedback(request: Request):
    if not request.app.state.config.feedback_overview_enabled:
        raise HTTPException(404, 'feedback_overview_disabled')
    reader: FeedbackReadPort = request.app.state.feedback
    result = reader.read()
    return FeedbackView(observed_at=result.observed_at, up=result.up, down=result.down)
