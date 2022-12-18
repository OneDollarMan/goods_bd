import hashlib
from flask import url_for, render_template, request, redirect, send_from_directory, flash, session
from __init__ import app
import forms
from repo import *

repo = Repo(host=app.config['HOST'], user=app.config['USER'], password=app.config['PASSWORD'], db=app.config['DB'])


@app.route("/")
def index():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    return render_template('index.html', title="Главная")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if session.get('loggedin'):
        return redirect(url_for('index'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = repo.login_user_safe(form.login.data, hashlib.md5(form.password.data.encode('utf-8')).hexdigest())
        if user:
            flash('Вы авторизовались!')
            session['loggedin'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))


@app.route("/users", methods=['GET', 'POST'])
def users():
    form = forms.UserForm()
    form.role.choices = repo.get_roles()
    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            if not repo.add_user(form.username.data, hashlib.md5(form.password.data.encode('utf-8')).hexdigest(), form.fio.data, form.role.data):
                flash('Пользователь уже существует')
            else:
                app.logger.warning(f'User {form.username.data} with role id {form.role.data} was added by {session.get("username")}')
            redirect(url_for('users'))
    return render_template('users.html', title='Работники', us=repo.get_all_users(), form=form)


@app.route("/users/rm/<int:id>")
def user_rm(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.rm_user(id)
    return redirect(url_for('users'))


@app.route("/suppliers", methods=['GET', 'POST'])
def suppliers():
    form = forms.SupplierForm()
    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            repo.add_supplier(form.name.data, form.address.data, form.phone.data)
            return redirect(url_for('suppliers'))
    return render_template('suppliers.html', title="Поставщики", ss=repo.get_suppliers(), form=form)


@app.route("/suppliers/<int:supplierid>")
def supplier(supplierid):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        return render_template('supplier.html', title="Поставщик", s=repo.get_supplier(supplierid),
                               ps=repo.get_food_of_supplier(supplierid))
    else:
        flash("Недостаточно прав")
        return redirect(url_for('suppliers'))


@app.route("/suppliers/rm/<int:id>")
def suppliers_rm(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.rm_supplier(id)
    return redirect(url_for("suppliers"))


@app.route("/food", methods=['GET', 'POST'])
def foods():
    food_form = forms.FoodForm()
    food_form.supplier.choices = repo.select_suppliers()
    food_form.unit.choices = repo.get_units()

    get_form = forms.GetForm()
    get_form.food.choices = repo.select_foods()

    if food_form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            repo.add_food(food_form.supplier.data, food_form.name.data, food_form.unit.data, food_form.price.data)
            return redirect(url_for('foods'))

    if get_form.validate_on_submit():
        if session.get('role') >= repo.ROLE_STOREKEEPER:
            repo.add_food_amount(get_form.food.data, get_form.amount.data)
            return redirect(url_for('foods'))
    return render_template('foods.html', title="Продукты", ss=repo.get_suppliers(), foods=repo.get_foods(), us=repo.get_units(), product_form=food_form, get_form=get_form)


@app.route("/food/<int:id>")
def food(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        return render_template('food.html', title="Продукт", p=repo.get_food(id), cs=repo.get_contracts_of_food(id))
    else:
        flash("Недостаточно прав")
        return redirect(url_for('foods'))


@app.route("/food/rm/<int:id>")
def food_remove(id):
    if session.get('role') >= repo.ROLE_STOREKEEPER:
        if id:
            repo.rm_food(id)
    return redirect(url_for("foods"))


@app.route("/customers", methods=['GET', 'POST'])
def customers():
    form = forms.CustomerForm()
    if form.validate_on_submit() and session.get('role') == repo.ROLE_ADMINISTRATOR:
        repo.add_customer(form.fio.data, form.phonenumber.data)
        redirect(url_for("customers"))
    return render_template('customers.html', title="Заказчики", cs=repo.get_customers(), form=form)


@app.route("/customers/<int:id>")
def customer(id):
    c = repo.get_customer(id)
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        return render_template('customer.html', title="Заказчик", c=c, ss=repo.get_contracts_of_customer(id))
    else:
        flash("Недостаточно прав")
        return redirect(url_for('customers'))


@app.route("/customers/rm/<int:id>")
def customers_remove(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.rm_customer(id)
    return redirect(url_for("customers"))


@app.route("/contracts", methods=["GET", "POST"])
def contracts():
    contract_form = forms.ContractForm()
    contract_form.customer.choices = repo.select_customers()

    filter_form = forms.FilterContractForm()
    filter_form.customer2.choices = [("", "---")] + repo.select_customers()
    filter_form.status.choices = [("", "---")] + repo.select_statuses()

    if filter_form.validate_on_submit():
        s = filter_form.start_date.data
        e = filter_form.end_date.data
        c = filter_form.customer2.data
        st = filter_form.status.data
        return render_template('contracts.html', title="Контракты", contracts=repo.get_contract_sorted(s, e, c, st),
                               cs=repo.get_customers(), ps=repo.get_foods(), form=contract_form, filter_form=filter_form)

    return render_template('contracts.html', title="Контракты", contracts=repo.get_contracts_with_sums(), cs=repo.get_customers(), ps=repo.get_foods(), form=contract_form, filter_form=filter_form)


@app.route("/contracts/add", methods=['POST'])
def add_contract():
    contract_form = forms.ContractForm()
    contract_form.customer.choices = repo.select_customers()

    if contract_form.validate_on_submit():
        if session.get('role') >= repo.ROLE_STOREKEEPER:
            repo.add_contract(d=contract_form.date.data, c=contract_form.customer.data, p=contract_form.percent.data)
            app.logger.warning(f'New contract added by {session.get("username")}')
    return redirect(url_for("contracts"))


@app.route("/contracts/<int:id>", methods=["GET", "POST"])
def contract(id):
    if session.get('role') >= repo.ROLE_STOREKEEPER:
        form = forms.AddFoodForm()
        form.food.choices = repo.select_foods()

        status_form = forms.StatusForm()
        status_form.status.choices = repo.select_statuses()

        if form.validate_on_submit():
            if not repo.add_food_to_contract(id, form.food.data, form.amount.data):
                flash("Недостаточно товара")
            return redirect(url_for("contract", id=id))

        return render_template('contract.html', title="Контракт", c=repo.get_contract(id), form=form, foods=repo.get_foods_of_contract(id), status_form=status_form, sum=repo.get_contract_sum(id))
    else:
        flash("Недостаточно прав")
        return redirect(url_for('contracts'))


@app.route('/contracts/<int:id>/status', methods=['POST'])
def status(id):
    status_form = forms.StatusForm()
    status_form.status.choices = repo.select_statuses()
    if status_form.validate_on_submit():
        repo.change_contract_status(id, status_form.status.data)
        flash('Статус изменен')
    return redirect(url_for("contract", id=id))


@app.route("/contracts/<int:cid>/rm_food/<int:fid>", methods=['GET'])
def contracts_remove_food(cid, fid):
    if session.get('role') >= repo.ROLE_STOREKEEPER:
        if cid and fid:
            repo.remove_food_from_contract(cid, fid)
            flash('Позиция удалена')
    return redirect(url_for("contract", id=cid))


@app.route("/contracts/rm/<int:id>")
def contracts_remove(id):
    if session.get('role') >= repo.ROLE_STOREKEEPER:
        if not repo.remove_contract(id):
            flash('Сначала очистите список продуктов')
            return redirect(url_for("contract", id=id))
    flash('Контракт удален')
    return redirect(url_for("contracts"))


@app.route("/contracts/profit")
def profit():
    return repo.get_profit_by_months()


@app.route('/robots.txt')
@app.route('/sitemap.xml')
@app.route('/favicon.ico')
@app.route('/style.css')
@app.route('/script.js')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404
