from db import DbConnectHelper


def get_capital():
    con = DbConnectHelper().get_single_connection()

    cursor = con.cursor()

    cursor.execute('SELECT id, capital FROM companies order by capital desc LIMIT 10')
    ogrn_list = cursor.fetchall()

    con.close()

    print(ogrn_list)

# забирать прокси из бд
def get():
    pass