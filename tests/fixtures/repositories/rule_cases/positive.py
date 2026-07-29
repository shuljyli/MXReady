import os
import subprocess

import tensorrt
from torch.utils.cpp_extension import CUDAExtension, load

TENSORRT_MODULE = tensorrt
CUDA_HOME = "/usr/local/cuda"
ARCH_FLAGS = ["-gencode=arch=compute_80,code=sm_80"]

subprocess.run(["nvcc", "kernel.cu"], check=True)
subprocess.run(["nvidia-smi"], check=True)
os.environ["NCCL_DEBUG"] = "INFO"
os.environ["TORCH_CUDA_ARCH_LIST"] = "8.0"

extension = CUDAExtension("demo", ["kernel.cu"])
jit_extension = load(name="jit_demo", sources=["kernel.cpp"])
