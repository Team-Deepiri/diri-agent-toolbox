from __future__ import annotations

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from diri_agent_toolbox.logging import get_logger

logger = get_logger("diri_agent_toolbox.device")


def get_device() -> str:
    if not HAS_TORCH:
        logger.info("PyTorch not installed, using cpu")
        return "cpu"

    logger.debug(f"PyTorch version: {torch.__version__}")
    logger.debug(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        try:
            cuda_version = torch.version.cuda
            device_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            capability = torch.cuda.get_device_capability(0)

            logger.info(
                f"CUDA: v={cuda_version}, devices={device_count}, "
                f"GPU={gpu_name}, sm_{capability[0]}.{capability[1]}"
            )

            test = torch.tensor([1.0], device="cuda")
            _ = (test * 2.0).cpu()
            del test
            torch.cuda.empty_cache()

            logger.info(f"CUDA GPU tested: {gpu_name} (CUDA {cuda_version})")
            return "cuda"
        except RuntimeError as e:
            err = str(e)
            if "no kernel image" in err or "cudaErrorNoKernelImageForDevice" in err:
                logger.error(f"GPU compute capability not supported: {err}")
            else:
                logger.warning(f"CUDA test failed, falling back to CPU: {err}")
        except Exception as e:
            logger.warning(f"CUDA error, falling back to CPU: {e}")
    else:
        logger.debug("CUDA not available")

    if HAS_TORCH and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        try:
            test = torch.tensor([1.0], device="mps")
            _ = (test * 2.0).cpu()
            del test
            logger.info("Apple Silicon MPS detected and tested")
            return "mps"
        except Exception as e:
            logger.warning(f"MPS test failed: {e}")

    logger.info("Using CPU")
    return "cpu"


def get_torch_device() -> "torch.device":
    if not HAS_TORCH:
        raise ImportError("torch required. Install: pip install torch")
    return torch.device(get_device())
