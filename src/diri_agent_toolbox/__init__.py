"""diri-agent-toolbox: portable typed tools for LLM agents."""

from diri_agent_toolbox.caching import AdvancedCacheManager, CacheEntry, EmbeddingCache
from diri_agent_toolbox.confidence import (
    ConfidenceAttributes,
    ConfidenceCalculator,
    ConfidenceLevel,
    ConfidenceSource,
    get_confidence_calculator,
)
from diri_agent_toolbox.contracts import (
    AGIDecisionEvent,
    AIModel,
    BaseEvent,
    EventType,
    InferenceEvent,
    ModelContract,
    ModelInput,
    ModelLoadedEvent,
    ModelMetadata,
    ModelOutput,
    ModelReadyEvent,
    ModelRegistryService,
    PlatformEvent,
    StreamingService,
    TrainingEvent,
)
from diri_agent_toolbox.database import DatabaseToolbox
from diri_agent_toolbox.device import get_device
from diri_agent_toolbox.errors import (
    CacheToolboxError,
    ConfidenceToolboxError,
    ConfigurationToolboxError,
    DatabaseToolboxError,
    DeviceToolboxError,
    FileToolboxError,
    HttpToolboxError,
    StreamingToolboxError,
    ToolboxError,
    ValidationToolboxError,
)
from diri_agent_toolbox.http import (
    AsyncHttpToolbox,
    UrlPolicy,
    default_prefix_url_policy,
    parse_json_or_text,
)
from diri_agent_toolbox.logging import (
    ErrorLogger,
    JsonFormatter,
    StructuredLogger,
    get_error_logger,
    get_logger,
)
from diri_agent_toolbox.models import (
    ToolCategory,
    ToolDefinition,
    ToolResult,
    tool_definition_parameters_schema,
    tool_definition_to_json_schema,
    tool_definition_to_openai_function,
)
from diri_agent_toolbox.monitoring import MetricsCollector
from diri_agent_toolbox.processing import (
    AsyncBatchProcessor,
    AsyncItemProcessor,
    BatchProcessingConfig,
    BatchProcessingResult,
)
from diri_agent_toolbox.runner import ToolRunner
from diri_agent_toolbox.streaming import StreamingClient, StreamTopics, validate_event

__all__ = [
    "AdvancedCacheManager",
    "AGIDecisionEvent",
    "AIModel",
    "AsyncBatchProcessor",
    "AsyncHttpToolbox",
    "AsyncItemProcessor",
    "BaseEvent",
    "BatchProcessingConfig",
    "BatchProcessingResult",
    "CacheEntry",
    "CacheToolboxError",
    "ConfidenceAttributes",
    "ConfidenceCalculator",
    "ConfidenceLevel",
    "ConfidenceSource",
    "ConfidenceToolboxError",
    "ConfigurationToolboxError",
    "DatabaseToolbox",
    "DatabaseToolboxError",
    "DeviceToolboxError",
    "EmbeddingCache",
    "ErrorLogger",
    "EventType",
    "FileToolboxError",
    "HttpToolboxError",
    "InferenceEvent",
    "JsonFormatter",
    "MetricsCollector",
    "ModelContract",
    "ModelInput",
    "ModelLoadedEvent",
    "ModelMetadata",
    "ModelOutput",
    "ModelReadyEvent",
    "ModelRegistryService",
    "PlatformEvent",
    "StreamTopics",
    "StreamingClient",
    "StreamingService",
    "StreamingToolboxError",
    "StructuredLogger",
    "ToolCategory",
    "ToolDefinition",
    "ToolResult",
    "ToolRunner",
    "ToolboxError",
    "TrainingEvent",
    "UrlPolicy",
    "ValidationToolboxError",
    "default_prefix_url_policy",
    "get_confidence_calculator",
    "get_device",
    "get_error_logger",
    "get_logger",
    "parse_json_or_text",
    "tool_definition_parameters_schema",
    "tool_definition_to_json_schema",
    "tool_definition_to_openai_function",
    "validate_event",
]

__version__ = "0.2.0"
