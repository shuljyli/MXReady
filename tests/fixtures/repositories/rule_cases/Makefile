# 共享夹具里的构建入口：同时喂给 MXR-TOOLCHAIN-001（NVCC = nvcc）
# 与 MXR-TOOLCHAIN-002（make_maca 说明已接入 cu-bridge）。
NVCC = nvcc

all: kernel
	$(NVCC) -O3 -o kernel main.cu

maca:
	make_maca
