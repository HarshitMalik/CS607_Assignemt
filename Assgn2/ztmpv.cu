/*
  Program to compare performance of CPU and GPU on ZTMPV operation

  SGEMV  performs the below matrix-vector operations

    x := op(A)*x

  where x is an n element vector and  A is an n by n unit, or non-unit, upper or lower triangular matrix

  Link to ZTMPV: https://www.netlib.org/lapack/explore-html/dc/dc1/group__complex16__blas__level2_gaed33e3470ec372c730960b6038d1e037.html#gaed33e3470ec372c730960b6038d1e037

*/

#include <iostream>
#include <ctime>
#include <thrust/host_vector.h>
#include <thrust/device_vector.h>
#include <curand.h>
#include <cublas_v2.h>

#define DIM_N 4 // Numbers of row and columns in matrix A
#define UPLO CUBLAS_FILL_MODE_LOWER // Upper triangular or lower triangular, other option: CUBLAS_FILL_MODE_UPPER
#define DIAG CUBLAS_DIAG_NON_UNIT // Unit or Non unit diagonal, other option: CUBLAS_DIAG_NON_UNIT
#define TRANSA CUBLAS_OP_N // Operation to be performed,  CUBLAS_OP_N => op(A) = A, CUBLAS_OP_T => op(A) = A**T, CUBLAS_OP_T => op(A) = A**H
#define INCX 1 //INCX specifies the increment for the elements of X

#define THREADS_PER_BLOCK 16 // Threads to spin per block in GPU
#define EPSILON 1e-2 // Precision for verifying actual and computed values

// Fill the vector x with random initial values
void init_vals(float *x, int N){
  curandGenerator_t prng;
  curandCreateGenerator(&prng, CURAND_RNG_PSEUDO_DEFAULT);
  curandSetPseudoRandomGeneratorSeed(prng, 1234ULL);
  curandGenerateUniform(prng, x, N);
  curandDestroyGenerator(prng);
}

// Fill the matrix A with random initial values
void init_A(float *A){
  // Input matrix are assumed to be in column major order

  if(DIAG == CUBLAS_DIAG_UNIT){
    for(int i=0; i<DIM_N; i++) A[i + i * DIM_N]= 1.0;
  }
  if(UPLO == CUBLAS_FILL_MODE_LOWER){
    for(int i=0; i<DIM_N; i++){
      for(int j=i+1; j<DIM_N; j++) A[i + j*DIM_N]= 0.0;
    }
  }
  else{
    for(int i=0; i<DIM_N; i++){
      for(int j=0; j<i; j++) A[i + j*DIM_N]= 0.0;
    }
  }
}

void init_B(const float *A, float *B){
  // Input matrix are assumed to be in column major order

  if(UPLO == CUBLAS_FILL_MODE_LOWER){
    for(int i=0; i<DIM_N; i++){
      for(int j=0; j<=i; j++) B[i -j + j*DIM_N]= A[i + j*DIM_N];
    }
  }
  else{
    for(int i=0; i<DIM_N; i++){
      for(int j=i; j<DIM_N; j++) B[DIM_N + i - j - 1 + j*DIM_N]= A[i + j*DIM_N];
    }
  }
}

// cuBLAS Level 3 routine call to perform ZTMPV operaiton
float cublas_ztmpv(const float *A, float *x){
  // Input matrix are assumed to be in column major order

  // Events to measure performance
  cudaEvent_t start, stop;
  cudaEventCreate(&start);
  cudaEventCreate(&stop);

  cublasHandle_t handle;
  cublasCreate(&handle);

  cudaEventRecord(start);
  cublasStbmv(handle, UPLO, TRANSA, DIAG, DIM_N, DIM_N-1, A, DIM_N, x, INCX);
  cudaEventRecord(stop);
  cudaEventSynchronize(stop);
  float ms = 0;
  cudaEventElapsedTime(&ms, start, stop);

  cublasDestroy(handle);
  return ms;
}

//GPU Kernel method to compute single element of the resultant vector
__global__ void gpu_kernel(const float *A, const float *x, float *res, int N, int op, int uplo){
  int i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<N) {
    float sum = 0;
    if(uplo == 1){
      for(int j=0;j<=i;j++){
        if(op == 1)
          sum += A[i + j * N] * x[j];
        else
          sum += A[i * N + j] * x[j];
      }
    }
    else{
      for(int j=i;j<N;j++){
        if(op == 1)
          sum += A[i + j * N] * x[j];
        else
          sum += A[i * N + j] * x[j];
      }
    }
    res[i] = sum;
  }
}

// Performing ZTMPV operation on GPU
float gpu_ztmpv(const float *A, const float *x, float *res){
  // Input matrix are assumed to be in column major order

  // Events to measure performance
  cudaEvent_t start, stop;
  cudaEventCreate(&start);
  cudaEventCreate(&stop);

  int op = (TRANSA == CUBLAS_OP_N) ? 1 : 0;
  int uplo = (UPLO == CUBLAS_FILL_MODE_LOWER) ? 1 : 0;

  cudaEventRecord(start);

  dim3 threadsPerBlock(THREADS_PER_BLOCK, 1);
  dim3 numBlocks( (DIM_N + threadsPerBlock.x - 1) / threadsPerBlock.x, 1);

  gpu_kernel<<<numBlocks, threadsPerBlock>>>(A, x, res, DIM_N, op, uplo);

  cudaEventRecord(stop);
  cudaEventSynchronize(stop);
  float ms = 0;
  cudaEventElapsedTime(&ms, start, stop);

  return ms;
}

// Performing ZTMPV operation on CPU
float cpu_ztmpv(const float *A, const float *x, float *res){
  // Input matrix are assumed to be in column major order

  //Record start time
  std::clock_t cpu_start = std::clock();

  for (int i = 0; i < DIM_N; i++) {
    float sum = 0.0;
    if(UPLO == CUBLAS_FILL_MODE_LOWER){
      for (int j = 0; j <= i; j++){
        if(TRANSA == CUBLAS_OP_N)
          sum += A[i + j * DIM_N] * x[j];
        else
          sum += A[i * DIM_N + j] * x[j];
      }
    }
    else{
      for (int j = i; j < DIM_N; j++){
        if(TRANSA == CUBLAS_OP_N)
          sum += A[i + j * DIM_N] * x[j];
        else
          sum += A[i * DIM_N + j] * x[j];
      }
    }
    res[i] = sum;
  }

  //Record end time
  std::clock_t cpu_end = std::clock();

  //return time elapsed in micro second
  long double cpu_ms = 1000.0 * (cpu_end-cpu_start) / CLOCKS_PER_SEC;
  return cpu_ms;
}

//Function to cross check computed vectors
int check(const float *A, const float *B, const float *C, int N){
  for(int i=0; i<N; i++){
    if(abs(B[i] - A[i]) > EPSILON || abs(C[i] - A[i]) > EPSILON){
      std::cout<<"Index : "<<i<<"  CPU : "<<A[i]<<"  GPU : "<<B[i]<<"  CuBLAS : "<<C[i]<<"\n";
      return 1;
    }
  }
  return 0;
}

// Function to print matrix stored in column major order
void print_mat(const float *M, int N){
  for(int i=0; i < N; i++) std::cout<<M[i]<<" ";
  std::cout<<std::endl;
}

int main(){
  // Declare device side vectors
  thrust::device_vector<float> d_A(DIM_N * DIM_N);
  thrust::device_vector<float> d_B(DIM_N * DIM_N);
  thrust::device_vector<float> d_x(DIM_N);
  thrust::device_vector<float> d_res(DIM_N);

  // Declare host side vectors
  thrust::host_vector<float> h_A(DIM_N * DIM_N);
  thrust::host_vector<float> h_B(DIM_N * DIM_N);
  thrust::host_vector<float> h_x(DIM_N);
  thrust::host_vector<float> h_res_gpu(DIM_N);
  thrust::host_vector<float> h_res_cpu(DIM_N);
  thrust::host_vector<float> h_res_cublas(DIM_N);

  // Initialize values
  init_vals(thrust::raw_pointer_cast(d_x.data()), DIM_N);
  init_vals(thrust::raw_pointer_cast(d_A.data()), DIM_N*DIM_N);

  // Copy device data to host
  h_A = d_A;
  h_x = d_x;

  init_A(thrust::raw_pointer_cast(h_A.data()));
  init_B(thrust::raw_pointer_cast(h_A.data()), thrust::raw_pointer_cast(h_B.data()));

  // Copy host data to device
  d_A = h_A;
  d_B = h_B;

  //Perform operation on the CPU
  float cpu_time = cpu_ztmpv( thrust::raw_pointer_cast(h_A.data()), thrust::raw_pointer_cast(h_x.data()), thrust::raw_pointer_cast(h_res_cpu.data()) );
  std::cout<<"Computation compeleted on CPU\n";

  //Perform operation on the GPU
  float gpu_time = gpu_ztmpv( thrust::raw_pointer_cast(d_A.data()), thrust::raw_pointer_cast(d_x.data()), thrust::raw_pointer_cast(d_res.data()) );
  std::cout<<"Computation compeleted on GPU using custom routine\n";

  // Perform operation on the GPU using cuBLAS routine
  float cublas_time = cublas_ztmpv(thrust::raw_pointer_cast(d_B.data()), thrust::raw_pointer_cast(d_x.data()) );
  std::cout<<"Computation compeleted on GPU using CuBLAS routine\n";

  // Copy result to host
  h_res_cublas = d_x;
  h_res_gpu = d_res;

  int status = check(thrust::raw_pointer_cast(h_res_cpu.data()), thrust::raw_pointer_cast(h_res_gpu.data()), thrust::raw_pointer_cast(h_res_cublas.data()), DIM_N);

  if(status == 0) std::cout<<"\nComputed vectors verified. No mismatch found.\n\n";
  else std::cout<<"\nComputed vectors not verified. Mismatch found.\n\n";

  //Print Result
  std::cout << "Input Data Shape \n"
            << "A : " << DIM_N <<" * " << DIM_N << "\n"
            << "x : " << DIM_N <<" * 1\n"
            << std::endl;
  //Print Result
  std::cout << "Perfermance \n"
            << "CPU Time : " << cpu_time << " ms\n"
            << "GPU Time : " << gpu_time << " ms\n"
            << "CuBLAS Time : " << cublas_time << " ms\n"
            << std::endl;
  return 0;
}
