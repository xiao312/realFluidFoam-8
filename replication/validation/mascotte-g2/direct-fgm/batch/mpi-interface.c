#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    char *end = NULL;
    const long expected = argc == 2 ? strtol(argv[1], &end, 10) : 0;
    if (expected < 1 || expected > 32 || !end || *end != '\0') return 2;
    MPI_Init(&argc, &argv);
    int rank = -1, size = 0, sum = -1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Allreduce(&rank, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    printf("MPI_INTERFACE rank=%d size=%d sum=%d\n", rank, size, sum);
    MPI_Finalize();
    return size == expected && sum == expected*(expected-1)/2 ? 0 : 3;
}
