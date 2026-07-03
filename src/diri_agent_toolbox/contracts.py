from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol

from pydantic import BaseModel, Field


class ModelInput(BaseModel):
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelOutput(BaseModel):
    prediction: Any
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelMetadata(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    architecture: Optional[str] = None
    accuracy: Optional[float] = None
    size_mb: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trained_by: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class AIModel(Protocol):
    def predict(self, input: ModelInput) -> ModelOutput: ...
    def get_metadata(self) -> ModelMetadata: ...
    def validate(self) -> bool: ...
    def export(self, format: str = "onnx") -> str: ...


class ModelContract(BaseModel):
    metadata: ModelMetadata
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    validation_tests: Optional[list] = None
    model_path: Optional[str] = None
    model_id: Optional[str] = None


class ModelRegistryService(Protocol):
    def register_model(
        self, model_name: str, version: str, model_path: str, metadata: Dict[str, Any]
    ) -> bool: ...
    def get_model(self, model_name: str, version: Optional[str] = None) -> Dict[str, Any]: ...
    def list_models(self, model_name: Optional[str] = None) -> list: ...
    def download_model(self, model_name: str, version: str, destination: str) -> str: ...


class StreamingService(Protocol):
    def publish(self, topic: str, event: Dict[str, Any]) -> bool: ...
    def subscribe(
        self, topic: str, callback: Callable, consumer_group: Optional[str] = None
    ) -> None: ...


class EventType(str, Enum):
    MODEL_READY = "model-ready"
    MODEL_LOADED = "model-loaded"
    MODEL_FAILED = "model-failed"
    INFERENCE_COMPLETE = "inference-complete"
    INFERENCE_FAILED = "inference-failed"
    USER_INTERACTION = "user-interaction"
    TASK_CREATED = "task-created"
    TASK_COMPLETED = "task-completed"
    AGI_DECISION = "agi-decision"
    AGI_ACTION = "agi-action"
    TRAINING_STARTED = "training-started"
    TRAINING_COMPLETE = "training-complete"
    TRAINING_FAILED = "training-failed"


class BaseEvent(BaseModel):
    event: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str
    correlation_id: Optional[str] = None


class ModelReadyEvent(BaseEvent):
    event: str = EventType.MODEL_READY
    model_name: str
    version: str
    registry_path: str
    metadata: Dict[str, Any]
    model_type: Optional[str] = None
    accuracy: Optional[float] = None
    size_mb: Optional[float] = None


class ModelLoadedEvent(BaseEvent):
    event: str = EventType.MODEL_LOADED
    model_name: str
    version: str
    load_time_ms: float
    cache_location: Optional[str] = None


class InferenceEvent(BaseEvent):
    event: str = EventType.INFERENCE_COMPLETE
    model_name: str
    version: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    latency_ms: float
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    confidence: Optional[float] = None
    success: bool = True


class PlatformEvent(BaseEvent):
    event: str
    service: str
    user_id: Optional[str] = None
    action: str
    data: Dict[str, Any]
    organization_id: Optional[str] = None


class AGIDecisionEvent(BaseEvent):
    event: str = EventType.AGI_DECISION
    decision_type: str
    target_service: Optional[str] = None
    action: Dict[str, Any]
    reasoning: Optional[str] = None
    confidence: Optional[float] = None


class TrainingEvent(BaseEvent):
    event: str
    experiment_id: str
    model_name: str
    status: str
    correlation_id: Optional[str] = None
    training_run_request_id: Optional[str] = None
    progress: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
