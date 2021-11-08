import os
import time

import keyboard
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager

start_time = time.perf_counter()

os.system("chcp 65001")
keyboard.add_hotkey('ctrl + alt + l', os.system, args=('taskkill /f /im firefox.exe /T',))

# logging.disable()
driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())

keyboard.wait('ctrl + c')

print(time.perf_counter() - start_time)
