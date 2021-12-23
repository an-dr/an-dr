import serial


class SerialInterface:
    def __init__(self):
        self.serial = serial.Serial()

    def set_baudrate(self, val):
        self.serial.baudrate = val

    def set_port(self, port):
        self.serial.port = port

    def set_timeout(self, timeout):
        self.serial.timeout = timeout

    def isOpen(self):
        return self.serial.isOpen()

    def close(self):
        while self.serial.isOpen():
            self.serial.close()

    def open(self):
        while not self.serial.isOpen():
            self.serial.open()

    def write(self, data):
        try:
            self.serial.write(data)
        except BaseException:
            print("Port is not opened")

    def read(self, size=1):
        return self.serial.read(size)


def main():
    pass


if __name__ == '__main__':
    main()
