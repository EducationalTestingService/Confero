# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 17:54:20 2014

@author: Sol
"""
from heapq import heappush, heappop, heappushpop, heapify, heapreplace
import itertools

class PriorityQueue(object):
    # Priority Constants 
    LOWEST = 255
    LOW = 192
    MEDIUM = 128
    HIGH = 64
    HIGHEST = 0
    
    _REMOVED = '<removed-task>'      # placeholder for a removed task
    def __init__(self,initial_tasks=[]):
        """
        PriorityQueue based on python heapq module and comments in the
        heapq docs: http://docs.python.org/2/library/heapq.html
        
        0 is highest priority level, maxint() is lowest priority.
        
        Tasks that have the same priority are returned in a FIFO order.
        
        The class defines a set priority level constants that can be used
        if desired.
        """
        self.pq = []                         # list of entries arranged in a heap
        self.entry_finder = {}               # mapping of tasks to entries
        self.counter = itertools.count()     # unique sequence count

        for task,priority in initial_tasks:
            self.add(task,priority)
            
    def add(self, task, priority=0):
        'Add a new task or update the priority of an existing task'
        if task in self.entry_finder:
            self.remove(task)
        count = next(self.counter)
        entry = [priority, count, task]
        self.entry_finder[task] = entry
        heappush(self.pq, entry)
    
    def remove(self, task):
        'Mark an existing task as REMOVED.  Raise KeyError if not found.'
        entry = self.entry_finder.pop(task)
        entry[-1] = self._REMOVED
    
    def pop(self, ):
        'Remove and return the lowest priority task. Raise KeyError if empty.'
        while self.pq:
            priority, count, task = heappop(self.pq)
            if task is not self._REMOVED:
                del self.entry_finder[task]
                return task
        raise KeyError('pop from an empty priority queue')     
    
    def __len__(self):
        return len(self.pq)
        
#######
import os, errno
        
def createPath(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise exception