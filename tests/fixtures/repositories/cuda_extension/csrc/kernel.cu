#include <cuda_runtime.h>

__global__ void mxready_fixture_kernel(float* values) {
    const int index = blockIdx.x * blockDim.x + threadIdx.x;
    values[index] = values[index] + 1.0f;
}
