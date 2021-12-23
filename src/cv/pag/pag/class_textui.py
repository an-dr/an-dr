import os
import time


class Item:
    def __init__(self):
        self.__text = 'Text'
        self.__selected = False

    def set_text(self, new_text: str):
        self.__text = new_text

    def get_text(self):
        return self.__text

    def set_selection(self, state: bool):
        self.__selected = state


class Screen:
    def __init__(self):
        self._title = 'Title'
        self._items = []
        self._active = False

    def draw(self):
        self.clear_screen()
        print(self._title)

    @staticmethod
    def clear_screen():
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')


class MainScreen(Screen):
    def __init__(self):
        super().__init__()
        self._title = 'Main Screen'


class App:
    def __init__(self):
        main_screen = MainScreen()
        self.screen_list = [main_screen]
        self.upd_fps = 30
        self.on = True

    def get_active_screen_num(self):
        num = -1
        # for s in

    def show_active_screen(self):
        active_is_founded = False
        # for s in self.screen_list:
        # if not active_is_founded:

    def run(self):
        while self.on:
            self.show_active_screen()
            time.sleep(1 / self.upd_fps)


def main():
    a = App()
    a.run()


if __name__ == '__main__':
    main()
