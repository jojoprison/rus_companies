from selenium import webdriver
import time

from webdriver_manager.firefox import GeckoDriverManager

from utility.paths import get_project_root_path

driver = None

try:
    # Fire a remote Firefox instance using geckodriver.
    # You need to have Geckodriver in the same directory as the automation testing script OR
    # you need to add it in the "path" environment variable OR
    # you need to know the full path to the geckodriver executable file and use it as:
    # driver = webdriver.Firefox(executable_path=r'your\path\geckodriver.exe')

    # path to your downloaded Firefox addon extension XPI file

    firefox_profile = webdriver.FirefoxProfile()

    ublock_extension_path = f'{get_project_root_path()}\\rus_companies\\driver_extensions\\firefox\\uBlock0_1.37.3b8.firefox.signed.xpi'

    driver = webdriver.Firefox(firefox_profile=firefox_profile,
                               executable_path=GeckoDriverManager().install())

    # using webdriver's install_addon API to install the downloaded Firefox extension

    driver.install_addon(ublock_extension_path, temporary=True)

    # Opening the Firefox support page to verify that addon is installed

    driver.get("about:support")

    # xpath to the section on the support page that lists installed extension

    # addons = driver.find_element_by_xpath('//*[contains(text(),"Add-ons") and not(contains(text(),"with"))]')
    # scrolling to the section on the support page that lists installed extension

    # driver.execute_script("arguments[0].scrollIntoView();", addons)

    # introducing program halt time to view things, ideally remove this when performing test automation in the cloud using LambdaTest

    print("Success. Yayy!!")

    time.sleep(150)

except Exception as E:

    print(E)

finally:

    # exiting the fired Mozilla Firefox selenium webdriver instance

    driver.quit()
