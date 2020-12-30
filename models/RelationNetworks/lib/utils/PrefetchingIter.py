# --------------------------------------------------------
# Relation Networks for Object Detection
# Copyright (c) 2017 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Modified by Jiayuan Gu, Dazhi Cheng, Han Hu, Yuwen Xiong
# --------------------------------------------------------
# Based on:
# MX-RCNN
# Copyright (c) 2016 by Contributors
# Licence under The Apache 2.0 License
# https://github.com/ijkguo/mx-rcnn/
# --------------------------------------------------------

import threading

import mxnet as mx
from mxnet.io import DataDesc


class PrefetchingIterV2(mx.io.DataIter):
    """Base class for prefetching iterators. Takes one or more DataIters (
    or any class with "reset" and "next" methods) and combine them with
    prefetching. For example:

    Parameters
    ----------
    iters : DataIter or list of DataIter
        one or more DataIters (or any class with "reset" and "next" methods)
    rename_data : None or list of dict
        i-th element is a renaming map for i-th iter, in the form of
        {'original_name' : 'new_name'}. Should have one entry for each entry
        in iter[i].provide_data
    rename_label : None or list of dict
        Similar to rename_data

    Examples
    --------
    iter = PrefetchingIter([NDArrayIter({'data': X1}), NDArrayIter({'data': X2})],
                           rename_data=[{'data': 'data1'}, {'data': 'data2'}])
    """

    def __init__(self, iters, rename_data=None, rename_label=None, prefetch_n_iter=4):
        super(PrefetchingIterV2, self).__init__()
        if not isinstance(iters, list):
            iters = [iters]
        self.n_iter = len(iters)
        self.prefetch_n_iter = prefetch_n_iter
        assert self.n_iter == 1, "Our prefetching iter only support 1 DataIter"
        self.iters = iters
        self.rename_data = rename_data
        self.rename_label = rename_label
        self.batch_size = len(self.provide_data) * self.provide_data[0][0][1][0]
        self.data_ready = [threading.Event() for i in range(self.prefetch_n_iter)]
        self.data_taken = [threading.Event() for i in range(self.prefetch_n_iter)]

        self.cur_id = 0
        for e in self.data_taken:
            e.set()
        self.started = True
        self.current_batch = None
        self.next_batch = [[None for _ in range(self.n_iter)] for _ in range(self.prefetch_n_iter)]

        def prefetch_func(self, i):
            """Thread entry"""
            while True:
                self.data_taken[i].wait()
                if not self.started:
                    break
                try:
                    self.next_batch[i][0] = self.iters[0].next()
                except StopIteration:
                    self.next_batch[i][0] = None
                self.data_taken[i].clear()
                self.data_ready[i].set()

        self.prefetch_threads = [threading.Thread(target=prefetch_func, args=[self, i]) \
                                 for i in range(self.prefetch_n_iter)]
        for thread in self.prefetch_threads:
            thread.setDaemon(True)
            thread.start()

    def __del__(self):
        self.started = False
        for e in self.data_taken:
            e.set()
        for thread in self.prefetch_threads:
            thread.join()

    @property
    def provide_data(self):
        """The name and shape of data provided by this iterator"""
        if self.rename_data is None:
            return sum([i.provide_data for i in self.iters], [])
        else:
            return sum([[
                DataDesc(r[x.name], x.shape, x.dtype)
                if isinstance(x, DataDesc) else DataDesc(*x)
                for x in i.provide_data
            ] for r, i in zip(self.rename_data, self.iters)], [])

    @property
    def provide_label(self):
        """The name and shape of label provided by this iterator"""
        if self.rename_label is None:
            return sum([i.provide_label for i in self.iters], [])
        else:
            return sum([[
                DataDesc(r[x.name], x.shape, x.dtype)
                if isinstance(x, DataDesc) else DataDesc(*x)
                for x in i.provide_label
            ] for r, i in zip(self.rename_label, self.iters)], [])

    def reset(self):
        for e in self.data_ready:
            e.wait()
        for i in self.iters:
            i.reset()
        for e in self.data_ready:
            e.clear()
        for e in self.data_taken:
            e.set()

    def iter_next(self):
        self.data_ready[self.cur_id].wait()
        if self.next_batch[self.cur_id][0] is None:
            self.cur_id = (self.cur_id + 1) % self.prefetch_n_iter
            return False
        else:
            self.current_batch = self.next_batch[self.cur_id][0]
            self.data_ready[self.cur_id].clear()
            self.data_taken[self.cur_id].set()

            self.cur_id = (self.cur_id + 1) % self.prefetch_n_iter
            return True

    def next(self):
        if self.iter_next():
            return self.current_batch
        else:
            raise StopIteration

    def getdata(self):
        return self.current_batch.data

    def getlabel(self):
        return self.current_batch.label

    def getindex(self):
        return self.current_batch.index

    def getpad(self):
        return self.current_batch.pad
