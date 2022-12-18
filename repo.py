from mysql.connector import connect, Error


class Repo:
    ROLE_STOREKEEPER = 1
    ROLE_ADMINISTRATOR = 2

    def __init__(self, host, user, password, db):
        self.connection = None
        self.cursor = None
        self.connect_to_db(host, user, password, db)
        if self.connection is not None and self.cursor is not None:
            self.select_db(db)
            self.get_tables = lambda: self.raw_query("SHOW TABLES")

            self.get_user = lambda username: self.get_query("SELECT * FROM user WHERE username='%s'" % username)
            self.get_all_users = lambda: self.raw_query("SELECT * FROM user JOIN role ON user.role_id=role.id")
            self.login_user = lambda username, password: self.get_query(
                "SELECT * FROM user WHERE username='%s' AND password='%s'" % (username, password))
            self.login_user_safe = lambda username, password: self.get_query("SELECT * FROM user WHERE username=%(u)s AND password=%(p)s", params={'u': username, 'p': password})
            self.add_u = lambda username, password, fio, role: self.write_query(
                f"INSERT INTO user SET username='{username}', fio='{fio}', password='{password}', role_id='{role}'")
            self.get_all_zero_users = lambda: self.raw_query("SELECT * FROM user WHERE role=0")
            self.rm_user = lambda id: self.write_query(f"DELETE FROM user WHERE id='{id}'")

            self.get_roles = lambda: self.raw_query("SELECT * from role")

            self.add_supplier = lambda name, address, phone: self.write_query(
                f"INSERT INTO supplier SET name='{name}', address='{address}', phonenumber='{phone}'")
            self.get_suppliers = lambda: self.raw_query("SELECT * FROM supplier WHERE hidden='0'")
            self.select_suppliers = lambda: self.raw_query("SELECT id, name FROM supplier WHERE hidden='0'")
            self.get_supplier = lambda id: self.get_query("SELECT * FROM supplier WHERE id='%d'" % id)
            self.rm_supplier = lambda id: self.write_query("UPDATE supplier SET hidden='1' WHERE id='%d'" % id)

            self.get_foods = lambda: self.raw_query(
                "SELECT * FROM food f JOIN supplier s, unit u WHERE f.supplier_id=s.id AND f.unit_id=u.id AND f.hidden='0' AND (s.hidden='0' OR f.amount > 0)")
            self.get_food_of_supplier = lambda id: self.raw_query(
                "SELECT * FROM food WHERE supplier_id='%d' and hidden='0'" % id)
            self.add_food = lambda s, n, u, p: self.write_query(
                f"INSERT INTO food SET supplier_id='{s}', name='{n}', unit_id='{u}', price='{p}'")
            self.add_food_amount = lambda i, a: self.write_query(
                "UPDATE food SET amount=amount+'%f' WHERE id='%s'" % (a, i))
            self.get_food = lambda id: self.get_query(
                "SELECT * FROM food f JOIN supplier s, unit u WHERE f.supplier_id=s.id AND f.unit_id=u.id AND f.id='%d'" % id)
            self.change_food_amount = lambda id, amount: self.write_query(
                f"UPDATE food SET amount=amount+'{amount}' WHERE id='{id}'")
            self.rm_food = lambda id: self.write_query("UPDATE food SET hidden='1' WHERE id='%d'" % id)
            self.rm_supplier_food = lambda id: self.write_query(
                "UPDATE food SET supplier_id='0' WHERE supplier_id='%d'" % id)
            self.select_foods = lambda: self.raw_query("SELECT id, name FROM food WHERE hidden='0'")
            self.get_food_amount = lambda id: self.get_one_query(f"SELECT amount FROM food WHERE id='{id}'")
            self.get_contracts_of_food = lambda id: self.raw_query(
                f"SELECT * FROM food_has_contract f JOIN contract c ON f.contract_id=c.id WHERE food_id='{id}'")

            self.get_customers = lambda: self.raw_query("SELECT * FROM customer WHERE hidden='0'")
            self.add_customer = lambda fio, p: self.write_query(
                f"INSERT INTO customer SET fio='{fio}', phonenumber='{p}'")
            self.get_customer = lambda id: self.get_query(f"SELECT * FROM customer WHERE id='{id}'")
            self.select_customers = lambda: self.raw_query("SELECT id, fio FROM customer WHERE hidden='0'")
            self.get_contracts_of_customer = lambda id: self.raw_query(
                f"SELECT * FROM contract WHERE customer_id='{id}'")
            self.rm_customer = lambda id: self.write_query(f"UPDATE customer SET hidden='1' WHERE id='{id}'")

            self.get_contracts = lambda: self.raw_query(
                "SELECT * FROM contract c JOIN customer cs, status s WHERE c.customer_id=cs.id AND c.status_id=s.id")
            self.get_contracts_with_sums = lambda: self.raw_query("SELECT * FROM contract c LEFT JOIN (SELECT f.contract_id, SUM(f.amount * price) FROM food_has_contract f JOIN food ON f.food_id=food.id GROUP BY f.contract_id) s ON c.id=s.contract_id INNER JOIN customer cs, status st WHERE c.customer_id=cs.id AND c.status_id=st.id ORDER BY date")
            self.add_contract = lambda d, c, p: self.write_query(
                f"INSERT INTO contract SET customer_id='{c}', percent='{p}', delivery_date='{d}'")
            self.get_contract = lambda id: self.get_query(
                "SELECT * FROM contract c JOIN customer cs, status s WHERE c.customer_id=cs.id AND c.status_id=s.id AND c.id='%d'" % id)
            self.rm_contract = lambda id: self.write_query("DELETE FROM contract WHERE id='%d'" % id)
            self.change_contract_status = lambda id, sid: self.write_query(
                f"UPDATE contract SET status_id='{sid}' WHERE id='{id}'")

            self.get_foods_of_contract = lambda id: self.raw_query(
                f"SELECT * FROM food_has_contract f JOIN food, supplier s, unit u WHERE f.food_id=food.id AND food.unit_id=u.id AND food.supplier_id=s.id AND contract_id='{id}'")
            self.add_food_to_contr = lambda cid, fid, a: self.write_query(
                f"INSERT INTO food_has_contract SET contract_id='{cid}', food_id='{fid}', amount='{a}'")
            self.change_food_in_contract_amount = lambda cid, fid, a: self.write_query(
                f"UPDATE food_has_contract SET amount=amount+'{a}' WHERE contract_id='{cid}' AND food_id='{fid}'")
            self.check_food_of_contract = lambda cid, fid: self.raw_query(
                f"SELECT * FROM food_has_contract WHERE contract_id='{cid}' AND food_id='{fid}'")
            self.rm_food_from_c = lambda cid, fid: self.write_query(
                f"DELETE FROM food_has_contract WHERE contract_id='{cid}' AND food_id='{fid}'")
            self.get_contract_sum = lambda id: self.get_one_query(
                f"SELECT SUM(f.amount * price) FROM food_has_contract f JOIN food ON f.food_id=food.id WHERE contract_id='{id}'")
            self.get_profit_by_months = lambda: self.raw_query("SELECT DATE_FORMAT(delivery_date, '%Y-%c') df, sum(s * percent / 100) FROM (SELECT f.contract_id, c.delivery_date, c.percent, SUM(f.amount * price) s FROM food_has_contract f JOIN food ON f.food_id=food.id JOIN contract c ON f.contract_id=c.id GROUP BY f.contract_id) summ GROUP BY YEAR(summ.delivery_date), MONTH(summ.delivery_date) ORDER BY df")

            self.get_units = lambda: self.raw_query("SELECT * FROM unit")

            self.select_statuses = lambda: self.raw_query("SELECT id, name FROM status")

    def connect_to_db(self, host, user, password, db):
        try:
            self.connection = connect(host=host, user=user, password=password)
            self.cursor = self.connection.cursor()
            self.cursor.execute("SHOW DATABASES")
            for res in self.cursor:
                if res[0] == db:
                    self.cursor.fetchall()
                    return
            for line in open('dump.sql'):
                self.cursor.execute(line)
            self.connection.commit()
            print('dump loaded successfully')
        except Error as e:
            print(e)

    def select_db(self, db):
        self.cursor.execute(f"USE {db}")

    def raw_query(self, query, params=None):  # Функция, отправляющая запрос к БД
        if self.cursor and query:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()

    def write_query(self, query):
        if self.cursor and query:
            self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.fetchall()

    def get_query(self, query, params=None):
        if self.cursor and query:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchone()

    def get_one_query(self, query):
        if self.cursor and query:
            self.cursor.execute(query)
            return self.cursor.fetchone()[0]

    def add_user(self, username, password, fio, role):
        if not self.get_user(username):
            self.add_u(username, password, fio, role)
            return True
        else:
            return False

    def add_food_to_contract(self, contract_id, food_id, amount):
        food_amount = self.get_food_amount(food_id)
        if food_amount < amount:
            return False
        if self.check_food_of_contract(contract_id, food_id):
            self.change_food_in_contract_amount(contract_id, food_id, amount)
        else:
            self.add_food_to_contr(contract_id, food_id, amount)
        self.change_food_amount(food_id, -amount)
        return True

    def remove_food_from_contract(self, contract_id, food_id):
        food = self.check_food_of_contract(contract_id, food_id)
        if food:
            self.rm_food_from_c(contract_id, food_id)
            self.change_food_amount(food_id, food[0][2])

    def remove_contract(self, contract_id):
        if not self.get_foods_of_contract(contract_id):
            self.rm_contract(contract_id)
            return True
        return False

    def get_contract_sorted(self, start_date, end_date, customer, status):
        q = "SELECT * FROM contract c LEFT JOIN (SELECT f.contract_id, SUM(f.amount * price) FROM food_has_contract f JOIN food ON f.food_id=food.id GROUP BY f.contract_id) s ON c.id=s.contract_id INNER JOIN customer cs, status st WHERE c.customer_id=cs.id AND c.status_id=st.id"
        if start_date:
            q = q + f" AND delivery_date > '{start_date}'"
        if end_date:
            q = q + f" AND delivery_date < '{end_date}'"
        if customer:
            q = q + f" AND customer_id = '{customer}'"
        if status:
            q = q + f" AND status_id = '{status}'"
        q = q + ' ORDER BY date'
        return self.raw_query(q)
