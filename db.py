from utility.paths import get_project_root_path
from utility.db_connect_helper import DbConnectHelper


# переопределяем класс, чтобы изменить путь к конфиг кайлу для бд
class DbRusprofile(DbConnectHelper):

    def __init__(self):
        # вызываем конструктор родителя
        super().__init__()
        self.config_path = f'{get_project_root_path()}/rus_companies/config.ini'
