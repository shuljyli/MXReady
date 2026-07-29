cmake_minimum_required(VERSION 3.24)
project(mxready_fixture LANGUAGES CXX CUDA)
find_package(Torch REQUIRED)
add_library(mxready_fixture SHARED csrc/kernel.cu)
