from unittest.mock import MagicMock, patch

from diri_agent_toolbox.device import get_device


@patch("diri_agent_toolbox.device.HAS_TORCH", False)
def test_get_device_no_torch():
    assert get_device() == "cpu"


def _make_torch_mock():
    torch = MagicMock()
    torch.__version__ = "2.1.0"
    torch.version.cuda = "12.1"
    torch.cuda.is_available.return_value = True
    torch.cuda.device_count.return_value = 2
    torch.cuda.get_device_name.return_value = "Tesla T4"
    torch.cuda.get_device_capability.return_value = (7, 5)
    torch.tensor.return_value.cpu.return_value = None
    torch.backends.mps.is_available.return_value = False
    return torch


@patch("diri_agent_toolbox.device.HAS_TORCH", True)
@patch("diri_agent_toolbox.device.torch", new_callable=_make_torch_mock)
def test_get_device_cuda(mock_torch):
    assert get_device() == "cuda"


@patch("diri_agent_toolbox.device.HAS_TORCH", True)
@patch("diri_agent_toolbox.device.torch")
def test_get_device_cuda_fallback(mock_torch):
    mock_torch.__version__ = "2.1.0"
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1
    mock_torch.tensor.side_effect = RuntimeError("CUDA error")
    mock_torch.backends.mps.is_available.return_value = False
    assert get_device() == "cpu"


@patch("diri_agent_toolbox.device.HAS_TORCH", True)
@patch("diri_agent_toolbox.device.torch")
def test_get_device_mps(mock_torch):
    mock_torch.__version__ = "2.1.0"
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = True
    mock_torch.tensor.return_value.cpu.return_value = None
    assert get_device() == "mps"


@patch("diri_agent_toolbox.device.HAS_TORCH", True)
@patch("diri_agent_toolbox.device.torch")
def test_get_device_mps_fallback(mock_torch):
    mock_torch.__version__ = "2.1.0"
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = True
    mock_torch.tensor.side_effect = RuntimeError("MPS error")
    assert get_device() == "cpu"
