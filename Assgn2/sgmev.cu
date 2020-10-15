/*
  Program to compare performance of CPU and GPU on SGMEV operation

  SGEMV  performs the below matrix-vector operations

    y := alpha*op(A)*x + beta*y

 where alpha and beta are scalars, x and y are vectors and A is an m by n matrix.

 Link to SGMEV: https://www.netlib.org/lapack/explore-html/d6/d30/group__single__blas__level2_gafc92361b74c6d41c7e5afa0aa5d13ec9.html#gafc92361b74c6d41c7e5afa0aa5d13ec9

*/

#include <iostream>
#include <ctime>
#include <thrust/host_vector.h>
#include <thrust/device_vector.h>
#include <curand.h>
#include <cublas_v2.h>

#define DIM_M 4096 // Numbers of row in matrix A
#define DIM_N 2048 // Numbers of columns in matrix A
#define DIM_X 2048 // Dimension of vector x, must be equal to number of columns in A or A**T accordingly
#define DIM_Y 4096// Dimension of vector y, must be equal to number of rows in A or A**T accordingly
#define ALPHA 0.25 // value of alpha
#define BETA 0.75 // Value of beta
#define TRANSA CUBLAS_OP_N // Operation to be performed,  CUBLAS_OP_N => op(A) = A, CUBLAS_OP_T => op(A) = A**T

#define THREADS_PER_BLOCK 16 // Threads to spin per block in GPU
#define EPSILON 1e-2 // Precision for verifying actual and computed values

// Fill the matrix/vectors with random initial values
void init_vals(float *in, int N){
  curandGenerator_t prng;
  curandCreateGenerator(&prng, CURAND_RNG_PSEUDO_DEFAULT);
  curandSetPseudoRandomGeneratorSeed(prng, 1234ULL);
  curandGenerateUniform(prng, in, N);
  curandDestroyGenerator(prng);
}

// cuBLAS Level 3 routine call to perform SGMEV operaiton
float cublas_sgmev(const float *A, const float *x, float *y){
  // Input matrix are assumed to be in column major order

  // Events to measure performance
  cudaEvent_t start, stop;
  cudaEventCreate(&start);
  cudaEventCreate(&stop);

  int m = DIM_Y; // rows in op(A)
  int n = 1;   // columns in x
  int k = DIM_X; // columns in op(A)
  const float alpha = ALPHA;
  const float beta = BETA;

  cublasHandle_t handle;
  cublasCreate(&handle);

  cudaEventRecord(start);
  cublasSgemm(handle, TRANSA, CUBLAS_OP_N, m, n, k, &alpha, A, DIM_M, x, DIM_X, &beta, y, DIM_Y);
  cudaEventRecord(stop);
  cudaEventSynchronize(stop);
  float ms = 0;
  cudaEventElapsedTime(&ms, start, stop);

  cublasDestroy(handle);
  return ms;
}


//GPU Kernel method to compute single element of the resultant vector
__global__ void gpu_kernel(const float *A, const float *x, const float *y, float *res, int rows, int cols, int op, float alpha, float beta){
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if(i < rows) {
    float sum = 0;
    for(int j=0; j < cols; j++) {
      if(op == 1)
        sum += A[i + j * rows] * x[j];//GPU Kernel method to compute single element of the resultant vector;
      else
        sum += A[i * cols + j] * x[j];
    }
    res[i] = alpha*sum + beta*y[i];
  }
}

// Performing SGMEV operation on GPU
float gpu_sgmev(const float *A, const float *x, const float *y, float *res){
  // Input matrix are assumed to be in column major order

  // Events to measure performance
  cudaEvent_t start, stop;
  cudaEventCreate(&start);
  cudaEventCreate(&stop);

  int op = (TRANSA == CUBLAS_OP_N) ? 1: 0;

  cudaEventRecord(start);
  dim3 threadsPerBlock(THREADS_PER_BLOCK, 1);
  dim3 numBlocks( (DIM_Y + threadsPerBlock.x - 1) / threadsPerBlock.x, 1);

  gpu_kernel<<<numBlocks, threadsPerBlock>>>(A, x, y,res, DIM_Y, DIM_X, op, ALPHA, BETA);

  cudaEventRecord(stop);
  cudaEventSynchronize(stop);
  float ms = 0;
  cudaEventElapsedTime(&ms, start, stop);
  return ms;
}



// Performing SGMEV operation on CPU
float cpu_sgmev(const float *A, const float *x, const float *y, float *res){
  // Input matrix are assumed to be in column major order

  //Record start time
  std::clock_t cpu_start = std::clock();

  //Perform operation
  for (int i = 0; i < DIM_Y; i++) {
    float sum = 0.0;
    for (int j = 0; j < DIM_X; j++){
      if(TRANSA == CUBLAS_OP_N)
        sum += A[i + j * DIM_Y] * x[j];
      else
        sum += A[i * DIM_X + j] * x[j];
    }
    res[i] = ALPHA*sum + BETA*y[i];
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


// Function to print matrix in column major order
void print_mat(const float *M, int size){
  for(int i=0; i < size; i++) std::cout<<M[i]<<" ";
  std::cout<<std::endl;
}

int main(){
  // Declare device side vectors
  thrust::device_vector<float> d_A(DIM_M * DIM_N);
  thrust::device_vector<float> d_x(DIM_X);
  thrust::device_vector<float> d_y(DIM_Y);
  thrust::device_vector<float> d_res(DIM_Y);

  // Declare host side vectors
  thrust::host_vector<float> h_A(DIM_M * DIM_N);
  thrust::host_vector<float> h_x(DIM_X);
  thrust::host_vector<float> h_y(DIM_Y);
  thrust::host_vector<float> h_res_gpu(DIM_Y);
  thrust::host_vector<float> h_res_cpu(DIM_Y);
  thrust::host_vector<float> h_res_cublas(DIM_Y);

  // Initialize values
  init_vals(thrust::raw_pointer_cast(d_A.data()), DIM_M * DIM_N);
  init_vals(thrust::raw_pointer_cast(d_x.data()), DIM_X);
  init_vals(thrust::raw_pointer_cast(d_y.data()), DIM_Y);

  // Copy device data to host
  h_A = d_A;
  h_x = d_x;
  h_y = d_y;

  //Perform operation on the CPU
  float cpu_time = cpu_sgmev( thrust::raw_pointer_cast(h_A.data()), thrust::raw_pointer_cast(h_x.data()), thrust::raw_pointer_cast(h_y.data()), thrust::raw_pointer_cast(h_res_cpu.data()) );
  std::cout<<"Computation compeleted on CPU\n";

  //Perform operation on the GPU
  float gpu_time = gpu_sgmev( thrust::raw_pointer_cast(d_A.data()), thrust::raw_pointer_cast(d_x.data()), thrust::raw_pointer_cast(d_y.data()), thrust::raw_pointer_cast(d_res.data()) );
  std::cout<<"Computation compeleted on GPU using custom routine\n";

  // Perform operation on the GPU using cuBLAS routine
  float cublas_time = cublas_sgmev(thrust::raw_pointer_cast(d_A.data()), thrust::raw_pointer_cast(d_x.data()), thrust::raw_pointer_cast(d_y.data()) );
  std::cout<<"Computation compeleted on GPU using CuBLAS routine\n";

  // Copy result to host
  h_res_cublas = d_y;
  h_res_gpu = d_res;



  int status = check(thrust::raw_pointer_cast(h_res_cpu.data()), thrust::raw_pointer_cast(h_res_gpu.data()), thrust::raw_pointer_cast(h_res_cublas.data()), DIM_Y);

  if(status == 0) std::cout<<"\nComputed vectors verified. No mismatch found.\n\n";
  else std::cout<<"\nComputed vectors not verified. Mismatch found.\n\n";

  //Print Result
  std::cout << "Input Data Shape \n"
            << "A : " << DIM_M <<" * " << DIM_N << "\n"
            << "x : " << DIM_X <<" * 1\n"
            << "y : " << DIM_Y <<" * 1\n"
            << std::endl;
  //Print Result
  std::cout << "Perfermance \n"
            << "CPU Time : " << cpu_time << " ms\n"
            << "GPU Time : " << gpu_time << " ms\n"
            << "CuBLAS Time : " << cublas_time << " ms\n"
            << std::endl;

  return 0;
}
