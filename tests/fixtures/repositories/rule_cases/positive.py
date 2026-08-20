import os
import subprocess

import apex
import pytest
import tensorrt
import torch
import torch.distributed as dist
from torch.utils.cpp_extension import CUDAExtension, load

TENSORRT_MODULE = tensorrt
APEX_MODULE = apex
CUDA_HOME = "/usr/local/cuda"
ARCH_FLAGS = ["-gencode=arch=compute_80,code=sm_80"]

subprocess.run(["nvcc", "kernel.cu"], check=True)
subprocess.run(["nvidia-smi"], check=True)
os.environ["NCCL_DEBUG"] = "INFO"
os.environ["TORCH_CUDA_ARCH_LIST"] = "8.0"

extension = CUDAExtension("demo", ["kernel.cu"])
jit_extension = load(name="jit_demo", sources=["kernel.cpp"])

dist.init_process_group(backend="nccl", init_method="env://")

scaler = torch.cuda.amp.GradScaler()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="requires cuda")
def skipped_test():
    pass
