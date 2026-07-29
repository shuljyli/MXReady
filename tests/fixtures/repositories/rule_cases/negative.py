"""Documentation may mention nvcc, nvidia-smi, CUDAExtension, and tensorrt."""


def discover_toolchain_path():
    return "/opt/maca"


def detect_compute_units():
    return 80


CUDA_HOME = discover_toolchain_path()
sm_count = 80
compute_units = detect_compute_units()
NCCL_option_name = "selected dynamically"
TORCH_CUDA_ARCH_LIST_HELP = "architecture guidance"
cuda_graph_api_name = "cudaGraphCreate"
launch_bounds_description = 256
