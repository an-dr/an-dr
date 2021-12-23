import threading
import time


class TimerMulTh(threading.Thread):
    def __init__(self, out_list: list, period_sec: float =1, timeout: int =5, print_out: bool =False):
        threading.Thread.__init__(self)  # init from Thread
        self.__value = out_list  # list for outer access
        self.__print = print_out
        # timer params
        self.__period = period_sec
        self.__timeout = timeout
        self.__stop = True
        # self.__value = 0

    def run(self):
        """
        :return:
        """
        self.__stop = False
        # === setting up a list
        if len(self.__value) == 0:
            self.__value.append(0)
        self.__value[0] = self.__timeout
        # === timer while
        while self.__value[0] > self.__period/2:
            # while > half-__period. At the last iteration it will cause:
            #   - full __period waiting, if remains more then half
            #   - 0 if remains the less
            time.sleep(self.__period)
            self.__value[0] -= self.__period
            if self.__print:
                print(self.__value)
            if self.__stop:
                break
        self.__value[0] = 0

    def set_period(self, n_sec: int):
        self.__period = n_sec

    def set_timeout(self, n_sec: int):
        self.__timeout = n_sec

    def set_print_mode(self, sw: bool):
        self.__print = sw

    def stop(self):
        self.__stop = True
        return self.__value[0]


if __name__ == '__main__':
    # Create new thread and __value
    def example():
        val = []
        timer = TimerMulTh(val, 0.1, 100, True)
        timer.start()
        while 1:
            time.sleep(5)
            print('Value: ' + str(timer.stop()))

    example()
