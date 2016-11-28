"""
dtaidistance.dtw - Dynamic Time Warping

__author__ = "Wannes Meert"
__copyright__ = "Copyright 2016 KU Leuven, DTAI Research Group"
__license__ = "APL"

..
    Part of the DTAI experimenter code.

    Copyright 2016 KU Leuven, DTAI Research Group

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import logging
import numpy as np

logger = logging.getLogger("be.kuleuven.dtai.distance")

try:
    from . import dtw_c
except ImportError:
    logger.info('C library not available')
    dtw_c = None

try:
    from tqdm import tqdm
except ImportError:
    logger.info('tqdm library not available')
    tqdm = None


def lb_keogh(s1, s2, window=None, max_dist=None,
               max_step=None, max_length_diff=None):
    """Lowerbound LB_KEOGH"""
    # TODO: This implementation slower than distance() itself
    if window is None:
        window = max(len(s1), len(s2))

    t = 0
    for i in range(len(s1)):
        imin = max(0, i - max(0, len(s1) - len(s2)) - window + 1)
        imax = min(len(s2), i + max(0, len(s2) - len(s1)) + window)
        ui = np.max(s2[imin:imax])
        li = np.min(s2[imin:imax])
        ci = s1[i]
        if ci > ui:
            t += abs(ci - ui)
        else:
            t += abs(ci - li)
    return t


def distance(s1, s2, window=None, max_dist=None,
             max_step=None, max_length_diff=None):
    """
    Dynamic Time Warping (keep compact matrix)
    :param s1: First sequence
    :param s2: Second sequence
    :param window: Only allow for shifts up to this amount away from the two diagonals
    :param max_dist: Stop if the returned values will be larger than this value
    :param max_step: Do not allow steps larger than this value
    :param max_length_diff: Return infinity if length of two series is larger

    Returns: DTW distance
    """
    r, c = len(s1), len(s2)
    if max_length_diff is not None and abs(r - c) > max_length_diff:
        return np.inf
    if window is None:
        window = max(r, c)
    if max_step is None:
        max_step = np.inf
    if max_dist is None:
        max_dist = np.inf
    length = min(c + 1, abs(r - c) + 2 * (window - 1) + 1 + 1 + 1)
    # print("length (py) = {}".format(length))
    dtw = np.full((2, length), np.inf)
    dtw[0, 0] = 0
    last_under_max_dist = 0
    skip = 0
    i0 = 1
    i1 = 0
    for i in range(r):
        # print(dtw)
        if last_under_max_dist == -1:
            prev_last_under_max_dist = np.inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        skipp = skip
        skip = max(0, i - max(0, r - c) - window + 1)
        i0 = 1 - i0
        i1 = 1 - i1
        dtw[i1, :] = np.inf
        if dtw.shape[1] == c + 1:
            skip = 0
        for j in range(max(0, i - max(0, r - c) - window + 1), min(c, i + max(0, c - r) + window)):
            d = (s1[i] - s2[j])**2
            if d > max_step:
                continue
            assert j + 1 - skip >= 0
            assert j - skipp >= 0
            assert j + 1 - skipp >= 0
            assert j - skip >= 0
            dtw[i1, j + 1 - skip] = d + min(dtw[i0, j - skipp], dtw[i0, j + 1 - skipp], dtw[i1, j - skip])
            # print('({},{}), ({},{}), ({},{})'.format(i0, j - skipp, i0, j + 1 - skipp, i1, j - skip))
            # print('{}, {}, {}'.format(dtw[i0, j - skipp], dtw[i0, j + 1 - skipp], dtw[i1, j - skip]))
            # print('i={}, j={}, d={}, skip={}, skipp={}'.format(i,j,d,skip,skipp))
            # print(dtw)
            if dtw[i1, j + 1 - skip] <= max_dist:
                last_under_max_dist = j
            else:
                dtw[i1, j + 1 - skip] = np.inf
                if prev_last_under_max_dist < j + 1:
                    break
        if last_under_max_dist == -1:
            # print('early stop')
            # print(dtw)
            return np.inf
    return dtw[i1, min(c, c + window - 1) - skip]


def distance_with_params(t):
    return distance(t[0], t[1], **t[2])


def distance_c_with_params(t):
    return dtw_c.distance(t[0], t[1], **t[2])


def distances(s1, s2, window=None, max_dist=None,
              max_step=None, max_length_diff=None):
    """
    Dynamic Time Warping (keep full matrix)
    :param s1: First sequence
    :param s2: Second sequence
    :param window: Only allow for shifts up to this amount away from the two diagonals
    :param max_dist: Stop if the returned values will be larger than this value
    :param max_step: Do not allow steps larger than this value
    :param max_length_diff: Return infinity if length of two series is larger

    Returns: DTW distance, DTW matrix
    """
    compact = False
    r, c = len(s1), len(s2)
    if max_length_diff is not None and abs(r - c) > max_length_diff:
        return np.inf
    if window is None:
        window = max(r, c)
    # if self.dtw is None:
    if compact:
        dtw = np.full((2, min(c + 1, abs(r - c) + 2 * (window - 1) + 1 + 1 + 1)), np.inf)
    else:
        dtw = np.full((r + 1, c + 1), np.inf)
    # print('dtw shape', dtw.shape)
    # else:
    #     self.dtw = np.resize(self.dtw, (r + 1, c + 1))
    #     self.dtw.fill(np.inf)
    dtw[0, 0] = 0
    last_under_max_dist = 0
    skip = 0
    i0 = 1
    i1 = 0
    for i in range(r):
        if last_under_max_dist == -1:
            prev_last_under_max_dist = np.inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        skipp = skip
        if compact:
            skip = max(0, i - window + 1)
            i0 = 1 - i0
            i1 = 1 - i1
            dtw[i1, :] = np.inf
        else:
            i0 = i
            i1 = i + 1
        if dtw.shape[1] == c + 1:
            skip = 0
        # print('i =', i, 'skip =',skip, 'skipp =', skipp)
        # jmin = max(0, i - max(0, r - c) - window + 1)
        # jmax = min(c, i + max(0, c - r) + window)
        # print(i,jmin,jmax)
        # x = dtw[i, jmin-skipp:jmax-skipp]
        # y = dtw[i, jmin+1-skipp:jmax+1-skipp]
        # print(x,y,dtw[i+1, jmin+1-skip:jmax+1-skip])
        # dtw[i+1, jmin+1-skip:jmax+1-skip] = np.minimum(x,
        #                                                y)
        for j in range(max(0, i - max(0, r - c) - window + 1), min(c, i + max(0, c - r) + window)):
            # print('j =', j, 'max=',min(c, c - r + i + window))
            d = (s1[i] - s2[j])**2
            if max_step is not None and d > max_step:
                continue
            # print(i, j + 1 - skip, j - skipp, j + 1 - skipp, j - skip)
            dtw[i1, j + 1 - skip] = d + min(dtw[i0, j - skipp], dtw[i0, j + 1 - skipp], dtw[i1, j - skip])
            # dtw[i + 1, j + 1 - skip] = d + min(dtw[i + 1, j + 1 - skip], dtw[i + 1, j - skip])
            if max_dist is not None:
                if dtw[i1, j + 1 - skip] <= max_dist:
                    last_under_max_dist = j
                else:
                    dtw[i1, j + 1 - skip] = np.inf
                    if prev_last_under_max_dist < j + 1:
                        break
        if max_dist is not None and last_under_max_dist == -1:
            # print('early stop')
            # print(dtw)
            return np.inf, dtw
    # print(dtw)
    # print(c,c-skip+window-1)
    # if skip > 0:
    #     return dtw[-1, min(c,window)]  # / (sum(self.dtw.shape)-2)
    return dtw[i1, min(c, c + window - 1) - skip], dtw


def distance_matrix_func(use_c=False, use_nogil=False, parallel=False, show_progress=False):
    def distance_matrix_wrapper(seqs, **kwargs):
        return distance_matrix(seqs, parallel=parallel, use_c=use_c,
                               use_nogil=use_nogil,
                               show_progress=show_progress, **kwargs)
    return distance_matrix_wrapper


def distance_matrix(s, max_dist=None, max_length_diff=5,
                    window=None, max_step=None, parallel=True,
                    use_c=False, use_nogil=False, show_progress=False):
    """Distance matrix for all sequences in s.

    :param parallel: Use parallel operations
    :param use_c: Use c compiled Python functions
    :param use_nogil: Use pure c functions
    """
    if parallel:
        try:
            import multiprocessing as mp
            logger.info('Using multiprocessing')
        except ImportError:
            parallel = False
            mp = None
    else:
        mp = None
    dist_opts = {
        'max_dist': max_dist,
        'max_step': max_step,
        'window': window,
        'max_length_diff': max_length_diff
    }
    if max_length_diff is None:
        max_length_diff = np.inf
    large_value = np.inf
    logger.info('Computing distances')
    if use_c:
        for k, v in dist_opts.items():
            if v is None:
                dist_opts[k] = 0.0
    if use_c and use_nogil:
        logger.info("Compute distances in pure C")
        if parallel:
            logger.info("Use parallel computation")
            dists = dtw_c.distance_matrix_nogil_p(s, **dist_opts)
        else:
            logger.info("Use serial computation")
            dists = dtw_c.distance_matrix_nogil(s, **dist_opts)
    if use_c and not use_nogil:
        logger.info("Compute distances in Python compiled C")
        if parallel:
            logger.info("Use parallel computation")
            dists = np.zeros((len(s), len(s))) + large_value
            idxs = np.triu_indices(len(s), k=1)
            with mp.Pool() as p:
                dists[idxs] = p.map(distance_c_with_params, [(s[r], s[c], dist_opts) for c, r in zip(*idxs)])
                # pbar = tqdm(total=int((len(s)*(len(s)-1)/2)))
                # for r in range(len(s)):
                #     dists[r,r+1:len(s)] = p.map(distance, [(s[r],s[c], dist_opts) for c in range(r+1,len(cur))])
                #     pbar.update(len(s) - r - 1)
                # pbar.close()
        else:
            logger.info("Use serial computation")
            dists = dtw_c.distance_matrix(s, **dist_opts)
    if not use_c:
        logger.info("Compute distances in Python")
        if parallel:
            logger.info("Use parallel computation")
            dists = np.zeros((len(s), len(s))) + large_value
            idxs = np.triu_indices(len(s), k=1)
            with mp.Pool() as p:
                dists[idxs] = p.map(distance_with_params, [(s[r], s[c], dist_opts) for c, r in zip(*idxs)])
                # pbar = tqdm(total=int((len(s)*(len(s)-1)/2)))
                # for r in range(len(s)):
                #     dists[r,r+1:len(s)] = p.map(distance, [(s[r],s[c], dist_opts) for c in range(r+1,len(cur))])
                #     pbar.update(len(s) - r - 1)
                # pbar.close()
        else:
            logger.info("Use serial computation")
            dists = np.zeros((len(s), len(s))) + large_value
            it_r = range(len(s))
            if show_progress:
                it_r = tqdm(it_r)
            for r in it_r:
                for c in range(r + 1, len(s)):
                    if abs(len(s[r]) - len(s[c])) <= max_length_diff:
                        dists[r, c] = distance(s[r], s[c], **dist_opts)
    return dists
