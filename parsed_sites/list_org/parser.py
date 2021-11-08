import logging
import os
import sys
from pathlib import Path

import keyboard
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from parsed_sites.list_org.proxy import list_org_random_proxy, LIST_ORG_FILENAME
from parsed_sites.list_org.user_agent import save_user_agent, get_user_agent
from utility.paths import get_project_root_path
from utility.proxy.proxy import parse, delete_proxy


# настраиваем логгер чтобы отключить говно из класса webdriver-manager
def config_logger(logger):
    # другой конфиг можно взять из webdrivermanager/logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)


logger = logging.getLogger('__name__')
config_logger(logger)


class ListOrg:
    site_url = 'https://www.list-org.com/'
    ogrn_find_url = 'https://www.list-org.com/search?type=ogrn&val='
    user_agent = None
    proxy_str = None

    def __init__(self, proxy=None):

        logging.disable()

        # TODO пробнуть PhantomJS
        driver_name_list = ['chrome', 'firefox']

        # # выбираем браузер из списка
        # driver_name = random.choice(driver_name_list)

        driver_name = 'firefox'
        # хром не поддерживаем расширения в headless режиме, а мне они нужны блочить рекламу
        # driver_name = 'chrome'

        # user_agent
        # print('get user_agent...')
        try:
            self.user_agent = UserAgent(cache=False, use_cache_server=False).random
            # сейвим юзер агента чтобы в случае превышения лимита обращений
            # к API либы webdriver_manager забирать уже записанные в json
            save_user_agent(self.user_agent)
        except ValueError:
            print('value_err')
            self.user_agent = get_user_agent()
        except Exception:
            # print('get_user_agent_err')
            self.user_agent = get_user_agent()

        # print('user_agent: ', self.user_agent)

        # proxy
        if not proxy:
            # print('get proxy...')
            self.proxy_str = list_org_random_proxy()
            # print('proxy: ', self.proxy_str)
            proxy = parse(self.proxy_str).signature()
        else:
            self.proxy_str = proxy.__str__()
            proxy = proxy.signature()

        if driver_name == 'chrome':
            chrome_options = ChromeOptions()
            # скрывает окно браузера (СТАРОЕ)
            # options.add_argument(f'--headless')
            # изменяет размер окна браузера
            chrome_options.add_argument(f'--window-size=800,600')
            chrome_options.add_argument("--incognito")
            # вырубаем палево с инфой что мы webdriver
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--no-sandbox')
            # user-agent
            if self.user_agent:
                chrome_options.add_argument(f'user-agent={self.user_agent}')
            # headless mode
            chrome_options.headless = True

            # chrome_options.add_experimental_option("mobileEmulation",
            #                                        {"deviceName": "Galaxy S5"})  # or whatever

            # не помню зачем енто :(
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

            # устанавливаем расширение шоб рекламу блочить)
            chrome_options.add_extension(
                Path(f'{get_project_root_path()}/rus_companies/driver_extensions/chrome/AdGuard-Werbeblocker_v3.6.6.crx'))

            # чет связанное с ssl сертификатами
            webdriver.DesiredCapabilities.CHROME['acceptSslCerts'] = True

            if proxy:
                chrome_options.add_argument(f'--proxy-server={proxy}')

            try:
                driver = webdriver.Chrome(executable_path=ChromeDriverManager(cache_valid_range=14).install(),
                                          options=chrome_options)
            except ValueError:
                driver = webdriver.Chrome(executable_path=f'{get_project_root_path()}/drivers/chromedriver.exe',
                                          options=chrome_options)

            # сейчас эта либа только хром поддерживает (selenium_stealth)
            stealth(driver,
                    languages=["ru-RU", "ru"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    )
        else:
            firefox_profile = webdriver.FirefoxProfile()
            if self.user_agent:
                # меняем user-agent, можно через FirefoxOptions если ЧЕ
                firefox_profile.set_preference('general.useragent.override', self.user_agent)
            firefox_profile.set_preference('dom.file.createInChild', True)

            firefox_profile.set_preference("privacy.clearOnShutdown.offlineApps", True)
            firefox_profile.set_preference("privacy.clearOnShutdown.passwords", True)
            firefox_profile.set_preference("privacy.clearOnShutdown.siteSettings", True)
            firefox_profile.set_preference("privacy.sanitize.sanitizeOnShutdown", True)
            firefox_profile.set_preference("network.cookie.lifetimePolicy", 2)
            firefox_profile.set_preference("network.dns.disablePrefetch", True)
            firefox_profile.set_preference("network.http.sendRefererHeader", 0)
            # off css
            firefox_profile.set_preference("permissions.default.stylesheet", 2)
            # off imgs
            firefox_profile.set_preference("permissions.default.image", 2)
            # off js
            firefox_profile.set_preference("javascript.enabled", False)

            firefox_profile.update_preferences()

            # пытался установить расширение чтоб блочить рекламу - не робит
            # firefox_profile.add_extension(ublock_extension_path)

            if proxy:
                firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX
                firefox_capabilities['marionette'] = True

                firefox_capabilities['proxy'] = {
                    'proxyType': 'MANUAL',
                    'httpProxy': proxy,
                    # с 90 версии ff FTP больше не поддерживается
                    # 'ftpProxy': proxy,
                    'sslProxy': proxy
                }
            else:
                firefox_capabilities = None

            firefox_options = FirefoxOptions()
            # размер окна браузера
            firefox_options.add_argument('--width=800')
            firefox_options.add_argument('--height=600')
            # вырубаем палево с инфой что мы webdriver
            firefox_options.set_preference('dom.webdriver.enabled', False)
            # headless mode
            firefox_options.headless = True

            # инициализируем firefox
            try:
                # TODO падает с ошибкой от вебдрайвера прописать путь руками
                driver = webdriver.Firefox(firefox_profile=firefox_profile,
                                           capabilities=firefox_capabilities,
                                           executable_path=GeckoDriverManager(cache_valid_range=14).install(),
                                           options=firefox_options,
                                           service_log_path=f'{get_project_root_path()}'
                                                            f'/rus_companies/logs/geckodriver.log')
            except ValueError:
                driver = webdriver.Firefox(firefox_profile=firefox_profile,
                                           capabilities=firefox_capabilities,
                                           executable_path=f'{get_project_root_path()}/drivers/geckodriver.exe',
                                           options=firefox_options,
                                           service_log_path=f'{get_project_root_path()}'
                                                            f'/rus_companies/logs/geckodriver.log')

            # путь пишем через двойной обратный слеш - без этого не работает!
            ublock_extension_path = f'{get_project_root_path()}\\rus_companies\\driver_extensions\\firefox\\uBlock0_1.37.3b8.firefox.signed.xpi'
            ddgo = f'{get_project_root_path()}\\rus_companies\\driver_extensions\\firefox\\duckduckgo_privacy_essentials-2021.8.13.36133-an+fx.xpi'
            # устанавливаем расширение чтоб блочить рекламу
            driver.install_addon(ublock_extension_path)
            # вырубает трекинг
            driver.install_addon(ddgo)

        driver.delete_all_cookies()

        self.driver = driver

        # ставим кодировки для оси utf-8 чтобы в консоль нормальный вид печаталось
        os.system("chcp 65001")
        # ставим на сочетание клавиш закрытие ВСЕХ процессов фаерфокс, если че посыпалось
        keyboard.add_hotkey('ctrl + alt + l', os.system, args=('taskkill /f /im firefox.exe /T',))

    # метод для закрытия браузера
    def close_driver(self):
        self.driver.close()
        self.driver.quit()

    def wait_and_close_driver(self):
        input('Press enter if you want to stop browser right now')
        self.close_driver()
        sys.exit()

    # чтобы протестить прокси
    def open_site(self):
        self.driver.set_page_load_timeout(30)

        try:
            self.driver.get(self.site_url)
        except TimeoutException:
            print('GET TIMEOUT')

        title = self.driver.title

        self.close_driver()

        return title

    def get_contacts(self, phone=False, email=False, site=False):
        if phone:
            search_pattern = 'Телефон'
        elif email:
            search_pattern = 'E-mail'
        elif site:
            search_pattern = 'Сайт'
        else:
            print('Ошибка поискового паттерна')
            return None

        # print(f'ищем {search_pattern}')

        # desc_elem_block = WebDriverWait(self.driver, 15).until(
        #     EC.((By.XPATH, f"// i[contains(text(), '{search_pattern}')]"))
        # )
        # print(desc_elem_block)

        desc_elem_block = self.driver.find_element_by_xpath(
            f"// i[contains(text(), '{search_pattern}')]")
        elems_block = desc_elem_block.find_element_by_xpath('..')
        elems = elems_block.find_elements_by_tag_name('a')

        elem_list = [elem.text for elem in elems]

        if len(elem_list) == 0:
            elem_list = None

        return elem_list

    # TODO сделать условие, чтоб он в этом же инстансе открывал следующий огрн до капчи
    def get_contacts_by_ogrn(self, ogrn):

        ogrn_url = f'{self.ogrn_find_url}{ogrn}'

        self.driver.set_page_load_timeout(30)
        # какая то альтернатива по ходу
        # self.driver.command_executor.set_timeout(10)

        try:
            self.driver.get(ogrn_url)
        except TimeoutException:
            print(f'таймаут самой страницы {ogrn_url}')

            # значит прокся не работает - удаляем ее из файла
            # TODO засунуть все в бд и там счетчиком проверять когда удалять проксю или не юзать
            delete_proxy(self.proxy_str, LIST_ORG_FILENAME)

            return None

        #
        # for log in self.driver.get_log('driver'):
        #     print('driver:' + log['message'])

        if not self.captcha_exist():

            try:
                # проверяем, есть ли в тайтле слово "список"
                if WebDriverWait(self.driver, 3).until(
                        EC.title_contains('Список')
                ):

                    org_list_elem = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'org_list'))
                    )

                    # жмякаем на ссылку с компанией из списка (она единственная)
                    org_list_elem.find_element_by_tag_name('a').click()

                    # company_link = self.driver.find_element_by_class_name('org_list')
                    # company_link.find_element_by_tag_name('a').click()

                    # TODO придумать как логировать чтоб запускать в хедлесс режиме
                    print(f'открыли линку: {ogrn_url}')

                    if not self.captcha_exist():
                        # парсим контактные данные
                        phone_list = self.get_contacts(phone=True)

                        email_list = self.get_contacts(email=True)

                        site_list = self.get_contacts(site=True)

                        res_dict = {
                            'phones': phone_list,
                            'emails': email_list,
                            'sites': site_list
                        }
                    else:
                        print(f'КАПЧА: {ogrn_url}')
                        return None

                    return res_dict
                else:
                    print(f'в тайтле нет слова Список {ogrn_url}')
                    return None
            except TimeoutException:
                print(f'таймаут {ogrn_url}')
                return None
            except Exception as ex:
                print(f'получили чет другое: {ex}')
                return None
        else:
            print(f'КАПЧА: {ogrn_url}')
            return None

    # проверяем, всплыло ли окно с капчей
    def captcha_exist(self):
        # по быстроте (в порядке убывания) id - name - css_selecor - xpath
        return self.element_exist(By.CSS_SELECTOR, 'form[name="frm"')

    def element_exist(self, search_by, search_pattern):
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((search_by, search_pattern))
            )
            return True
        except NoSuchElementException:
            return False
        except Exception as ex:
            print(ex)
            return False
