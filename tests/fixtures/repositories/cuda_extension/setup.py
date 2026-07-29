from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

CUDA_HOME = "/usr/local/cuda"
NVCC = "/usr/local/cuda/bin/nvcc"

setup(
    name="mxready-cuda-fixture",
    ext_modules=[
        CUDAExtension(
            "mxready_fixture",
            ["csrc/kernel.cu"],
            extra_compile_args={"nvcc": ["-O3"]},
        )
    ],
    cmdclass={"build_ext": BuildExtension},
)
