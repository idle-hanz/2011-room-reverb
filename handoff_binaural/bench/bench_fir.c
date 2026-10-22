/* Direct-form FIR cost for the tail IC mixer: 2 FIRs (hp on M, hm on S) of N taps per sample.
   Upper bound: Play could use its partitioned FFT path instead. gcc -O2 bench_fir.c -o bench_fir */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
int main(int argc, char **argv) {
  int N = argc > 1 ? atoi(argv[1]) : 513, secs = argc > 2 ? atoi(argv[2]) : 20;
  int fs = 48000, n = fs * secs, i, k;
  float *h1 = malloc(N * sizeof(float)), *h2 = malloc(N * sizeof(float));
  float *x1 = calloc(n + N, sizeof(float)), *x2 = calloc(n + N, sizeof(float));
  double acc = 0;
  for (k = 0; k < N; k++) { h1[k] = 1.0f / (k + 1); h2[k] = -0.5f / (k + 2); }
  for (i = 0; i < n + N; i++) { x1[i] = (float)((i * 1103515245u + 12345u) % 1000) * 1e-3f; x2[i] = x1[i] * 0.5f; }
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  for (i = 0; i < n; i++) {
    float s1 = 0, s2 = 0; const float *p1 = x1 + i, *p2 = x2 + i;
    for (k = 0; k < N; k++) { s1 += h1[k] * p1[k]; s2 += h2[k] * p2[k]; }
    acc += 0.5 * (s1 + s2) - 0.5 * (s1 - s2);
  }
  clock_gettime(CLOCK_MONOTONIC, &b);
  double t = (b.tv_sec - a.tv_sec) + 1e-9 * (b.tv_nsec - a.tv_nsec);
  printf("N=%d two FIRs: %.3f ns/sample, %.2f%% of one core at 48 kHz (acc %.3g)\n", N, 1e9 * t / n, 100.0 * t / secs, acc);
  return 0;
}
