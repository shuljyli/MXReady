#include <cuda_runtime.h>
#include <cuda.h>

__global__ __launch_bounds__(256) void mxready_kernel(float* values) {
    float value = values[threadIdx.x];
    value = __shfl_sync(0xffffffff, value, 0);
    values[threadIdx.x] = value;
}

void create_graph(cudaGraph_t* graph) {
    cudaGraphCreate(graph, 0);
}
