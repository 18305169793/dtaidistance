import numpy as np
cimport numpy as np
cimport cython
import ctypes
from cpython cimport array
from cython import parallel
from cython.parallel import parallel, prange
from libc.stdlib cimport abort, malloc, free, abs
from libc.stdio cimport printf
from libc.math cimport sin, cos, acos, exp, sqrt, fabs, M_PI

DTYPE = np.float64
ctypedef np.float64_t DTYPE_t
cdef double inf = np.inf

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def distance(np.ndarray[DTYPE_t, ndim=1] s1, np.ndarray[DTYPE_t, ndim=1] s2,
             int window=0, double max_dist=0,
             double max_step=0, int max_length_diff=0):
    """
    Dynamic Time Warping (keep compact matrix)
    :param s1: First sequence
    :param s2: Second sequence
    :param dist_func: Point-wise distance
    :param window: Only allow for shifts up to this amount away from the two diagonals
    :param max_dist: Stop if the returned values will be larger than this value
    :param max_step: Do not allow steps larger than this value
    :param compact: Use compact storage (2 by abs(r-c)*2*(window-1)+3)

    Returns: DTW distance
    """
    assert s1.dtype == DTYPE and s2.dtype == DTYPE
    cdef int r = len(s1)
    cdef int c = len(s2)
    if max_length_diff != 0 and abs(r-c) > max_length_diff:
        return inf
    if window == 0:
        window = max(r, c)
    if max_step == 0:
        max_step = inf
    if max_dist == 0:
        max_dist = inf
    cdef np.ndarray[DTYPE_t, ndim=2] dtw = np.full((2, min( c +1 ,abs( r -c ) + 2 *( window -1 ) + 1 + 1 +1)), inf)
    dtw[0, 0] = 0
    cdef double last_under_max_dist = 0
    cdef double prev_last_under_max_dist = inf
    cdef int skip = 0
    cdef int skipp = 0
    cdef int i0 = 1
    cdef int i1 = 0
    cdef DTYPE_t d
    for i in range(r):
        if last_under_max_dist == -1:
            prev_last_under_max_dist = inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        skipp = skip
        skip = max(0, i - window + 1)
        i0 = 1 - i0
        i1 = 1 - i1
        dtw[i1 ,:] = inf
        if dtw.shape[1] == c+ 1:
            skip = 0
        for j in range(max(0, i - max(0, r - c) - window + 1), min(c, i + max(0, c - r) + window)):
            d = abs(s1[i] - s2[j])
            if d > max_step:
                continue
            dtw[i1, j + 1 - skip] = d + min(dtw[i0, j - skipp], dtw[i0, j + 1 - skipp], dtw[i1, j - skip])
            if dtw[i1, j + 1 - skip] <= max_dist:
                last_under_max_dist = j
            else:
                dtw[i1, j + 1 - skip] = inf
                if prev_last_under_max_dist < j + 1:
                    break
        if last_under_max_dist == -1:
            # print('early stop')
            # print(dtw)
            return inf
    # print(dtw)
    return dtw[i1, min(c, c + window - 1) - skip]


def distance_nogil(double[:] s1, double[:] s2,
             int window=0, double max_dist=0,
             double max_step=0, int max_length_diff=0):
    #return distance_nogil_c(s1, s2, len(s1), len(s2),
    return distance_nogil_c(&s1[0], &s2[0], len(s1), len(s2),
                            window, max_dist, max_step, max_length_diff)


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
cdef double distance_nogil_c(
             #double[:] s1, double[:] s2,
             double *s1, double *s2,
             int len_s1, int len_s2,
             int window=0, double max_dist=0,
             double max_step=0, int max_length_diff=0) nogil:
    cdef int r = len_s1
    cdef int c = len_s2
    if max_length_diff != 0 and abs(r-c) > max_length_diff:
        return inf
    if window == 0:
        window = max(r, c)
    if max_step == 0:
        max_step = inf
    if max_dist == 0:
        max_dist = inf
    cdef int length = min(c+1,abs(r-c) + 2*(window-1) + 1 + 1 +1)
    #cdef array.array dtw_tpl = array.array('d', [])
    #cdef array.array dtw
    #dtw = array.clone(dtw_tpl, length*2, zero=False)
    cdef double * dtw
    dtw = <double *> malloc(sizeof(double) * length * 2)
    cdef int i
    cdef int j
    for j in range(length*2):
        dtw[j] = inf
    dtw[0] = 0
    cdef double last_under_max_dist = 0
    cdef double prev_last_under_max_dist = inf
    cdef int skip = 0
    cdef int skipp = 0
    cdef int i0 = 1
    cdef int i1 = 0
    cdef int minj
    cdef int maxj
    cdef double minv
    cdef DTYPE_t d
    for i in range(r):
        if last_under_max_dist == -1:
            prev_last_under_max_dist = inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        skipp = skip
        skip = max(0, i - window + 1)
        i0 = 1 - i0
        i1 = 1 - i1
        for j in range(length):
            dtw[length * i1 + j] = inf
        if length == c + 1:
            skip = 0
        maxj = r - c
        if maxj < 0:
            maxj = 0
        maxj = i - maxj - window + 1
        if maxj < 0:
            maxj = 0
        minj = c - r
        if minj < 0:
            minj = 0
        minj = i + minj + window
        if minj > c:
            minj = c
        for j in range(maxj, minj):
            d = fabs(s1[i] - s2[j])
            if d > max_step:
                continue
            minv = dtw[i0*length + j - skipp]
            if dtw[i0*length + j + 1 - skipp] < minv:
                minv = dtw[i0*length + j + 1 - skipp]
            if dtw[i1*length + j - skip] < minv:
                minv = dtw[i1*length + j - skip]

            dtw[i1 * length + j + 1 - skip] = d + minv
            if dtw[i1*length + j + 1 - skip] <= max_dist:
                last_under_max_dist = j
            else:
                dtw[i1*length + j + 1 - skip] = inf
                if prev_last_under_max_dist < j + 1:
                    break
        if last_under_max_dist == -1:
            # print('early stop')
            # print(dtw)
            return inf
    # print(dtw)
    if window - 1 < 0:
        c = c + window - 1
    cdef double result = dtw[length * i1 + c - skip]
    free(dtw)
    return result



@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def distance_matrix(cur, double max_dist=inf, int max_diff_length=5,
                    int window=0, double max_point_dist=0, **kwargs):
    """Merge sequences.
    """
    if max_diff_length == 0:
        max_diff_length = 999999
    cdef double large_value = inf
    cdef np.ndarray[DTYPE_t, ndim=2] dists = np.zeros((len(cur), len(cur))) + large_value
    for r in range(len(cur)):
        for c in range(r + 1, len(cur)):
            if abs(len(cur[r]) - len(cur[c])) <= max_diff_length:
                dists[r, c] = distance(cur[r], cur[c], window=window,
                                       max_dist=max_dist, max_step=max_point_dist,
                                       max_length_diff=max_diff_length)
    return dists


def distance_matrix_nogil(cur, double max_dist=inf, int max_diff_length=5,
                          int window=0, double max_point_dist=0, **kwargs):
    # https://github.com/cython/cython/wiki/tutorials-NumpyPointerToC
    # Prepare for only c datastructures
    if max_diff_length == 0:
        max_diff_length = 999999
    cdef double large_value = inf
    cdef np.ndarray[DTYPE_t, ndim=2, mode="c"] dists = np.zeros((len(cur), len(cur))) + large_value
    cdef double **cur2 = <double **> malloc(len(cur) * sizeof(double*))
    cdef int *cur2_len = <int *> malloc(len(cur) * sizeof(int))
    cdef long ptr;
    #for i in range(len(cur)):
    #    print(cur[i])
    for i in range(len(cur)):
        ptr = cur[i].ctypes.data
        cur2[i] = <double *> ptr
        cur2_len[i] = len(cur[i])
    distance_matrix_nogil_c(cur2, len(cur), cur2_len, &dists[0,0], max_dist, max_diff_length, window, max_point_dist)
    free(cur2)
    free(cur2_len)
    return dists


def distance_matrix_nogil_p(cur, double max_dist=inf, int max_diff_length=5,
                          int window=0, double max_point_dist=0, **kwargs):
    # https://github.com/cython/cython/wiki/tutorials-NumpyPointerToC
    # Prepare for only c datastructures
    if max_diff_length == 0:
        max_diff_length = 999999
    cdef double large_value = inf
    cdef np.ndarray[DTYPE_t, ndim=2, mode="c"] dists = np.zeros((len(cur), len(cur))) + large_value
    cdef double **cur2 = <double **> malloc(len(cur) * sizeof(double*))
    cdef int *cur2_len = <int *> malloc(len(cur) * sizeof(int))
    cdef long ptr;
    #for i in range(len(cur)):
    #    print(cur[i])
    for i in range(len(cur)):
        ptr = cur[i].ctypes.data
        cur2[i] = <double *> ptr
        cur2_len[i] = len(cur[i])
    distance_matrix_nogil_c_p(cur2, len(cur), cur2_len, &dists[0,0], max_dist, max_diff_length, window, max_point_dist)
    free(cur2)
    free(cur2_len)
    return dists


cdef distance_matrix_nogil_c(double **cur, int len_cur, int* cur_len, double* output,
                             double max_dist=0, int max_diff_length=0,
                             int window=0, double max_point_dist=0):
    #for i in range(len_cur):
    #    print(i)
    #    print(cur_len[i])
    #    for j in range(cur_len[i]):
    #        printf("%f ", cur[i][j])
    #    printf("\n")
    #printf("---\n")
    cdef int r
    cdef int c
    for r in range(len_cur):
        for c in range(r + 1, len_cur):
            output[len_cur*r + c] = distance_nogil_c(cur[r], cur[c], cur_len[r], cur_len[c],
                                                     window=window, max_dist=max_dist,
                                                     max_step=max_point_dist, max_length_diff=max_diff_length)
            #for i in range(len_cur):
            #    for j in range(len_cur):
            #        printf("%f ", output[i*len_cur+j])
            #    printf("\n")
            #printf("---\n")


cdef distance_matrix_nogil_c_p(double **cur, int len_cur, int* cur_len, double* output,
                             double max_dist=0, int max_diff_length=0,
                             int window=0, double max_point_dist=0):
    # Requires openmp which is not supported for clang on mac
    cdef Py_ssize_t r
    cdef Py_ssize_t c

    with nogil, parallel():
        for r in prange(len_cur):
            for c in range(r + 1, len_cur):
                output[len_cur*r + c] = distance_nogil_c(cur[r], cur[c], cur_len[r], cur_len[c],
                                                         window=window, max_dist=max_dist,
                                                         max_step=max_point_dist, max_length_diff=max_diff_length)
