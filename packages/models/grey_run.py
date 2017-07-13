import multiprocessing as mp
import math

class GreyRun:
    
    def __init__(self):
        mp.freeze_support() # for windows
        self.cpu_count = mp.cpu_count()

    def _is_empty(self, array = []):
        return not bool(array)

    def _close_pool(self, pool):
        pool.close()
        pool.join()

    # multiprocessing
    def _execute_models(self, gmnn_queue=[], is_gm11=False): 
        if self._is_empty(gmnn_queue):
            return []
        pool        = mp.Pool()
        cpu_count   = self.cpu_count
        length      = len(gmnn_queue)
        block_count = long(math.ceil(length / float(cpu_count)))
        start_index = 0
        end_length  = cpu_count
        for block in xrange(0, block_count):
            for gm_model in gmnn_queue[start_index:end_length]:
                if is_gm11 == False:
                    pool.apply_async(gm_model.analyze())
                else:
                    pool.apply_async(gm_model.forecast())
                
            start_index += cpu_count
            end_length  += cpu_count
            if end_length > length:
                end_length = length

        self._close_pool(pool)
        return gmnn_queue

    def gm0n(self, queue):
        return self._execute_models(queue)

    def gm1n(self, queue):
        return self._execute_models(queue)

    def gm11(self, queue):
        return self._execute_models(queue, True)

