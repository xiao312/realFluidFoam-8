#include <mpi.h>
#include <stdio.h>
int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank = -1, size = 0, sum = -1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Allreduce(&rank, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    printf("MPI_INTERFACE rank=%d size=%d sum=%d\n", rank, size, sum);
    MPI_Finalize();
    return size == 4 && sum == 6 ? 0 : 3;
}
