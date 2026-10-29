#include <cuda_runtime.h>
#include <cuda.h>
#include <cublas_v2.h>

__global__ __launch_bounds__(256) void mxready_kernel(float* values) {
    float value = values[threadIdx.x];
    value = __shfl_sync(0xffffffff, value, 0);
    values[threadIdx.x] = value;
}

void create_graph(cudaGraph_t* graph) {
    cudaGraphCreate(graph, 0);
}

void manage_resources(float* device_values, cudaStream_t* stream) {
    cudaMalloc(&device_values, 4096);
    cudaStreamCreate(stream);
    cudaSetDevice(0);
}

void copy_data(float* out, float* in) {
    cudaMemcpy(out, in, 4096, cudaMemcpyDeviceToDevice);
}

#include <thrust/device_vector.h>
#include <cub/device/device_reduce.cuh>

__device__ float mxready_warp_lane(float* values) {
    int lane = threadIdx.x % 32;
    return values[lane];
}

__device__ float mxready_inline_ptx(float a, float b, float c) {
    float out;
    asm volatile("fma.rn.f32 %0, %1, %2, %3;" : "=f"(out) : "f"(a), "f"(b), "f"(c));
    return out;
}

void mxready_libraries(float* input, float* output, int count, void* temp, size_t bytes) {
    thrust::device_vector<float> buffer(1024);
    cub::DeviceReduce::Sum(temp, bytes, input, output, count);
}
