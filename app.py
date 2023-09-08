from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder='template', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, "warehouse.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    history = db.Column(db.String(99999), nullable=False)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)

with app.app_context():
    db.create_all()
    account_db = Account.query.first()
    if account_db is None:
        default_account_db = Account(balance=0.0, stock=0)
        db.session.add(default_account_db)
        db.session.commit()

def write_history(data):
    with open("history.txt", "a") as file:
        file.write(data + "\n")

@app.route('/', methods=["GET"])
def main_page():
    account_db = Account.query.first()
    return render_template("index.html", stock_level=account_db.stock, account_balance=account_db.balance)

@app.route('/balance_change_form.html', methods=["GET"])
def balance_change_form():
    return render_template("balance_change_form.html")

@app.route('/change_balance', methods=["GET", "POST"])
def balance_change():
    amount = float(request.form["amount"])
    operation = request.form.get("operation")

    if operation == "add":
        account_db = Account.query.first()
        account_db.balance += amount
        db.session.add(account_db)

        message = f"Success: Add the {amount} to account. Account Balance: {account_db.balance}"
        write_history(f"Added {amount} to account. Balance: {account_db.balance}")

        history_db = History(history=f"Added {amount} to account. Balance: {account_db.balance}")
        db.session.add(history_db)
        db.session.commit()

        return render_template("/balance_change_form.html", message=message)
    elif operation == "subtract":
        account_db = Account.query.first()
        if account_db.balance - amount < 0:
            error_message = "Error: Insufficient balance!"
            return render_template("/balance_change_form.html", error_message=error_message)
        else:
            account_db.balance -= amount
            db.session.add(account_db)

            history_db = History(history=f"Subtract {amount} to account. Balance: {account_db.balance}")
            db.session.add(history_db)
            db.session.commit()

            message = f"Success: Subtract  the {amount} to account. Account Balance: {account_db.balance}"
            write_history(f"Subtract {amount} to account. Balance: {account_db.balance}")
            return render_template("/balance_change_form.html", message=message)
    else:
        error_message = "Error: Invalid operation!"
        return render_template("/balance_change_form.html", error_message=error_message)

    return redirect(url_for("balance_change_page"))

@app.route('/purchase_form.html', methods=["GET"])
def purchase_form():
    return render_template("purchase_form.html")

@app.route('/purchase', methods=["GET", "POST"])
def purchase():
    quantity = int(request.form["number_of_pieces"])
    price = float(request.form["unit_price"])
    product_name = request.form["product_name"]

    total_price = price * quantity

    account_db = Account.query.first()
    exist_product = Product.query.filter_by(name=product_name).first()
    
    if exist_product and exist_product.price != price and exist_product.quantity > 0:
        error_message = f"Purchase error: {product_name} already exists with different prices and quantities"
        return render_template("/purchase_form.html", error_message=error_message)
    else:
        if account_db.balance - total_price < 0:
            error_message = "Purchase error: Insufficient balance!"
            return render_template("/purchase_form.html", error_message=error_message)
        else:
            account_db.balance -= total_price

            if exist_product and exist_product.price == price:
                exist_product.quantity += quantity
            else:
                new_product = Product(name=product_name,
                                        quantity=quantity,
                                        price=price)
                db.session.add(new_product)
                db.session.commit()

            account_db.stock += quantity

            db.session.add(account_db)
            
            history_db = History(history=f"Purchased {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}")
            db.session.add(history_db)
            db.session.commit()

            message = f"Successful purchase {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}"
            write_history(f"Purchased {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}")
            return render_template("/purchase_form.html", message=message)
    
    return redirect(url_for("purchase_form"))

@app.route('/sale_form.html', methods=["GET"])
def sale_form():
    product = Product.query.all()
    return render_template("/sale_form.html", product=product)

@app.route('/sale', methods=["GET", "POST"])
def sale():
    quantity = int(request.form["number_of_pieces"])
    price = float(request.form["unit_price"])
    product_name = request.form.get("sale_list")

    product = Product.query.all()

    account_db = Account.query.first()
    exist_product = Product.query.filter_by(name=product_name).first()
    
    if exist_product and exist_product.quantity >= quantity:
        total_price = price * quantity

        account_db.balance += total_price
    
        account_db.stock -= quantity
        db.session.add(account_db)

        exist_product.quantity -= quantity

        if exist_product.quantity == 0:
            db.session.delete(exist_product)
            db.session.commit()
        else:
            db.session.add(exist_product)
            db.session.commit()

        history_db = History(history=f"Sold {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}")
        db.session.add(history_db)
        db.session.commit()

        message = f"Successful sales {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}"
        write_history(f"Sold {quantity} of {product_name} with {total_price}. Balance: {account_db.balance}")
        return render_template("/sale_form.html", message=message, product=product)
    elif not exist_product:
        error_message = f"Sales error: {product_name} is not in the warehouse."
        return render_template("/sale_form.html", error_message=error_message, product=product)
    else:
        error_message = f"Sales error: Not enought quantity for {product_name}. Only {exist_product.quantity} left."
        return render_template("/sale_form.html", error_message=error_message, product=product)

    return redirect(url_for("sale_form"))

@app.route('/history.html', methods=["GET"])
def history_page():
    history_db = History.query.all()
    return render_template("/history.html", history=history_db)

@app.route('/history', methods=["GET", "POST"])
def review():
    from_indices = request.form["from"]
    to_indices = request.form["to"]

    history_db = History.query.all()
    row_count = History.query.count()

    if from_indices == "" or from_indices is None:
        from_indices = 0
    else:
        from_indices = int(from_indices)

    if to_indices == "" or to_indices is None:
        to_indices = int(row_count)
    else:
        to_indices = int(to_indices)

    if from_indices < 0 or from_indices > to_indices or to_indices > int(row_count):
        error_message = f"Error: Invalid range! Please enter between From: 0; To: {row_count}"
        return render_template("/history.html", error_message=error_message)
    elif not history_db:
        error_message = f"No history can be review"
        return render_template("/history.html", error_message=error_message)
    else:
        review_history = History.query.slice(from_indices, to_indices).all()
        return render_template("/history.html", review_history=review_history)
    
    return redirect(url_for("history_page"))
    
if __name__ == '__main__':
    app.run()
