import multiprocessing
import time

from db import DbConnectHelper
from parsed_sites.list_org.parser import ListOrg


def update_company_contacts(ogrn, contacts_dict):
    con = DbConnectHelper().get_connection()

    cursor = con.cursor()

    if contacts_dict['phones']:
        phones = ', '.join(contacts_dict['phones'])
    else:
        phones = None

    if contacts_dict['emails']:
        emails = ', '.join(contacts_dict['emails'])
    else:
        emails = None

    if contacts_dict['sites']:
        sites = ', '.join(contacts_dict['sites'])
    else:
        sites = None

    cursor.execute('UPDATE companies SET phone = %s, email = %s, company_site = %s '
                   'WHERE ogrn = %s RETURNING id',
                   (phones, emails, sites, ogrn))

    company_id = cursor.fetchone()[0]

    cursor.close()

    con.commit()

    return company_id


def update_company_by_ogrn(ogrn):
    # контакты компании
    company_contacts = None

    # бесконечный цикл с получением контактов
    while not company_contacts:
        # инициализируем объект здесь, т.к. внутри генерятся рандомные прокси
        list_org = ListOrg()

        # создаем браузер, забираем контакты с сайта list_org
        company_contacts = list_org.get_contacts_by_ogrn(ogrn)
        print(f'контакты по {ogrn}:', company_contacts)

        list_org.close_driver()

    company_id = None

    # если спарсили контакты
    if company_contacts:
        # обновляем данные контактов в базе
        company_id = update_company_contacts(ogrn, company_contacts)

    return company_id


def update_companies_massive():
    con = DbConnectHelper().get_connection()

    cursor = con.cursor()

    cursor.execute('SELECT ogrn FROM companies WHERE id BETWEEN 120 AND 140')
    ogrn_list = cursor.fetchall()

    con.close()

    ogrn_list = [ogrn[0] for ogrn in ogrn_list]
    print(ogrn_list)

    start_time = time.perf_counter()

    pool = multiprocessing.Pool(processes=7)

    pool_res = pool.map(update_company_by_ogrn, ogrn_list)

    print(f'Потрачено времени: {time.perf_counter() - start_time}')

    print(pool_res)


if __name__ == '__main__':
    # ogrn = 1046301620111
    #
    # contacts = list_org.get_contacts_by_ogrn(ogrn)
    # company_id = list_org.update_company_contacts(ogrn, contacts)
    # print(company_id)

    update_companies_massive()

    # get_capital()
