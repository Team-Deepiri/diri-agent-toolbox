from diri_agent_toolbox.contracts import (
    AGIDecisionEvent,
    BaseEvent,
    EventType,
    InferenceEvent,
    ModelContract,
    ModelInput,
    ModelLoadedEvent,
    ModelMetadata,
    ModelOutput,
    ModelReadyEvent,
    PlatformEvent,
    TrainingEvent,
)


def test_model_input_defaults():
    inp = ModelInput(data={"x": 1})
    assert inp.data == {"x": 1}
    assert inp.metadata is None
    assert isinstance(inp.timestamp, str)


def test_model_output_defaults():
    out = ModelOutput(prediction="cat")
    assert out.prediction == "cat"
    assert out.confidence is None


def test_model_metadata():
    meta = ModelMetadata(name="test", version="1.0", accuracy=0.95, size_mb=100.0)
    assert meta.name == "test"
    assert meta.accuracy == 0.95
    assert meta.size_mb == 100.0


def test_model_contract():
    meta = ModelMetadata(name="m", version="1")
    contract = ModelContract(
        metadata=meta, input_schema={"type": "object"}, output_schema={"type": "object"}
    )
    assert contract.metadata.name == "m"


def test_event_type_values():
    assert EventType.MODEL_READY == "model-ready"
    assert EventType.INFERENCE_COMPLETE == "inference-complete"
    assert EventType.TRAINING_STARTED == "training-started"


def test_base_event():
    e = BaseEvent(event="test", source="test_svc")
    assert e.source == "test_svc"
    assert e.correlation_id is None
    assert isinstance(e.timestamp, str)


def test_model_ready_event():
    e = ModelReadyEvent(
        source="registry",
        model_name="bert",
        version="1.0",
        registry_path="/models/bert",
        metadata={},
    )
    assert e.event == "model-ready"
    assert e.model_name == "bert"


def test_model_loaded_event():
    e = ModelLoadedEvent(
        source="loader",
        model_name="gpt",
        version="2.0",
        load_time_ms=1500.0,
    )
    assert e.event == "model-loaded"
    assert e.load_time_ms == 1500.0


def test_inference_event():
    e = InferenceEvent(
        source="api",
        model_name="claude",
        version="3",
        latency_ms=200.0,
        success=True,
    )
    assert e.event == "inference-complete"
    assert e.latency_ms == 200.0


def test_platform_event():
    e = PlatformEvent(
        event="user.login",
        source="auth",
        service="auth-svc",
        action="login",
        data={"user_id": "123"},
    )
    assert e.action == "login"
    assert e.data["user_id"] == "123"


def test_agi_decision_event():
    e = AGIDecisionEvent(
        source="agi",
        decision_type="route",
        target_service="renderflow",
        action={"task": "render"},
        reasoning="optimal path",
        confidence=0.85,
    )
    assert e.decision_type == "route"
    assert e.confidence == 0.85


def test_training_event():
    e = TrainingEvent(
        event="training-started",
        source="trainer",
        experiment_id="exp-1",
        model_name="my-model",
        status="running",
    )
    assert e.experiment_id == "exp-1"
    assert e.status == "running"
