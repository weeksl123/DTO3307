####################### Importing necessary libraries #######################
from flask import Flask, render_template, request, redirect, url_for, g, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pygal
from dotenv import load_dotenv
import os

####################### Flask app setup #######################
app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'HailstoneSecretKey')  # Use a default value if SECRET_KEY is not set in .env)

####################### Database setup #######################
DATABASE = './test.db'

def create_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS "users" (
        "id" INTEGER NOT NULL,
        "username" TEXT NOT NULL,
        "email" TEXT NOT NULL,
        "password_hash"	TEXT NOT NULL,
        "privilege"	INTEGER NOT NULL,
        "children"	TEXT,
        "parent_id"	INTEGER,
        "balance"	INTEGER,
        "spent"	INTEGER,
        PRIMARY KEY("id" AUTOINCREMENT)
        )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS "transactions" (
        "id" INTEGER NOT NULL,
        "user_id" INTEGER NOT NULL,
        "amount" INTEGER NOT NULL,
        "description" TEXT,
        "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY("id" AUTOINCREMENT),
        FOREIGN KEY("user_id") REFERENCES "users"("id")
    )''')
    conn.commit()
    conn.close()

create_db()

def connect_db():
    db = getattr(g, '_database', None)
    print("Database connection:", db)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        print("New database connection established:", db)
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.commit()
        db.close()

####################### Classes #######################
class User:
    def __init__(self, id, email, username, privilege, children, parent_id):
        self.id = id
        self.email = email
        if privilege == 1:
            self.parent_id = None
        else:
            self.parent_id = parent_id
        self.username = username
        self.privilege = privilege
        self.children = []
        if children:
            self.children = [int(child_id) for child_id in children.split(',') if child_id]
        else:
            self.children = []


    @staticmethod
    def get_by_username(username):
        cur = connect_db().cursor()
        cur.execute('SELECT id, email, username, privilege, children, parent_id FROM users WHERE username = ?', (username,))
        result = cur.fetchone()
        if result:
            return User(*result)
        return None

    @staticmethod
    def get_by_id(user_id):
        cur = connect_db().cursor()
        cur.execute('SELECT id, email, username, privilege, children, parent_id FROM users WHERE id = ?', (user_id,))
        result = cur.fetchone()
        if result:
            return User(*result)
        return None

    def sign_in(self, password):
        cur = connect_db().cursor()
        print("User ID:", self.id)
        print("Password:", password)
        cur.execute('SELECT password_hash FROM users WHERE id = ?', (self.id,))
        result = cur.fetchone()
        print("Password Hash from DB:", result)
        print("Check Password Result:", check_password_hash(result[0], password) if result else "No result")
        if result and check_password_hash(result[0], password):
            session['user_id'] = self.id
            session['username'] = self.username
            session['privilege'] = self.privilege
            session['logged_in'] = True
            session['children'] = self.children
            session['children_name'] = []
            session['children_balances'] = []
            session['children_spent'] = []
            for child_id in self.children:
                cur.execute('SELECT username, balance, spent FROM users WHERE id = ?', (child_id,))
                child_result = cur.fetchone()
                session['children_name'].append(child_result[0] if child_result else "Unknown")
                session['children_balances'].append(child_result[1] if child_result else 0)
                session['children_spent'].append(child_result[2] if child_result else 0)

            print("""
                    Session Data:
                    user_id: {}
                    username: {}
                    privilege: {}
                    logged_in: {}
                    children: {}
                    children_name: {}
                    children_balances: {}
                    children_spent: {}
                  """.format(session['user_id'], session['username'], session['privilege'], session['logged_in'], session['children'], session['children_name'], session['children_balances'], session['children_spent']))
            flash('Signed in successfully!', 'success')
            return True
        else: 
            flash('Invalid username or password.', 'error')
        return False
    
    @staticmethod
    def sign_up(username, email, password, confirm_password):
        cur = connect_db().cursor()
        print("Password:", password)
        print("Confirm Password:", confirm_password)
        if password == confirm_password:
            # Check if username already exists
            cur.execute('SELECT username FROM users WHERE username = ?', (username,))
            u_result = cur.fetchone()
            print("user:", u_result)
            cur.execute('SELECT email FROM users WHERE email = ?', (email,))
            e_result = cur.fetchone()
            print("email:", e_result)
            if u_result == None and e_result == None:
                hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                print("Password Hash:", hash)
                cur.execute('INSERT INTO users (username, email, password_hash, privilege, children, parent_id) VALUES (?, ?, ?, ?, ?, ?)', (username, email, hash, 1, None, None))
                flash('Account created successfully! Please sign in.', 'success')
            else:
                flash('Username or email already exists.', 'error')
        else:
            flash('Passwords do not match.', 'error')

    @staticmethod
    def sign_out():
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('privilege', None)
        session.pop('children', None)
        session.pop('children_name', None)
        session.pop('children_balances', None)
        session.pop('children_spent', None)
        session['logged_in'] = False

    def add_child(self, child_name, password, confirm_password):
        cur = connect_db().cursor()
        if self.privilege == 1:
            cur.execute('SELECT username FROM users WHERE username = ?', (child_name,))
            if cur.fetchone():
                flash('Child username already exists. Please choose a different username.', 'error')
                return False
            else:
                if password == confirm_password:
                    hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                    cur.execute('INSERT INTO users (username, email, password_hash, privilege, children, parent_id, balance, spent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (child_name, self.email, hash, 0, None, self.id, 300, 0))
                    child_id = cur.lastrowid
                    cur.execute('UPDATE users SET children = COALESCE(children, "") || ? WHERE id = ?', (',' + str(child_id), self.id))
                    self.children.append(child_id)
                    session.setdefault('children', []).append(child_id)
                    session.setdefault('children_name', []).append(child_name)
                    session.setdefault('children_balances', []).append(300)
                    session.setdefault('children_spent', []).append(0)
                    flash('Child account added successfully!', 'success')
                    return True
                else:
                    flash('Passwords do not match.', 'error')
        else:
            flash('Only parent accounts can add children.', 'error')
        return False
    
    def remove_child(self, child_id):
        cur = connect_db().cursor()
        cur.execute('DELETE FROM users WHERE id = ?', (child_id,))

        # Update sqlite_sequence table to maintain correct IDs
        cur.execute('SELECT MAX(id) FROM users')
        max_id = cur.fetchone()[0]
        if max_id is None:
            max_id = 0
        cur.execute('UPDATE sqlite_sequence SET seq = ? WHERE name = ?', (max_id, 'users'))

        if child_id in self.children:
            self.children.remove(child_id)

        updated_children = ','.join(str(child) for child in self.children) if self.children else None
        cur.execute('UPDATE users SET children = ? WHERE id = ?', (updated_children, self.id))

        if 'children' in session and child_id in session['children']:
            child_index = session['children'].index(child_id)
            session['children'].pop(child_index)
            session['children_name'].pop(child_index)
            session['children_balances'].pop(child_index)
            session['children_spent'].pop(child_index)

        flash('Child account removed successfully!', 'success')

    def update_balance(self, child_id, amount, description=None):
        cur = connect_db().cursor()
        # Update user's balance and spent. `amount` can be negative to represent a reversal.
        cur.execute('UPDATE users SET balance = balance - ?, spent = spent + ? WHERE id = ?', (amount, amount, child_id))
        # Insert transaction record (description may be NULL)
        cur.execute('INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)', (child_id, amount, description))
        flash('Balance updated successfully!', 'success')

    @staticmethod
    def get_transactions(user_id):
        cur = connect_db().cursor()
        cur.execute('SELECT id, user_id, amount, description, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
        return cur.fetchall()

    @staticmethod
    def get_transaction_by_id(tx_id):
        cur = connect_db().cursor()
        cur.execute('SELECT id, user_id, amount, description, timestamp FROM transactions WHERE id = ?', (tx_id,))
        return cur.fetchone()

####################### Chart setup #######################
def create_half_donut_chart(title, spent_amount, total=300):
    remaining = total - spent_amount
    if remaining < 0:
        remaining = 0

    chart = pygal.Pie(
        inner_radius=0.5,
        half_pie=True,
        style=pygal.style.Style(background='transparent'),
        show_legend=False,
        margin=10
    )
    chart.title = title
    chart.add('Spent', spent_amount)
    chart.add('Remaining', remaining)
    return chart

####################### Routes #######################
@app.route('/', methods=['GET', 'POST'])
def index():
    charts = []
    transactions = []

    if session.get('logged_in', False):
        if request.method == 'POST':
            selected_child = request.form.get('child')
            description = request.form.get('description')
            try:
                amount = float(request.form.get('amount') or 0)
            except ValueError:
                amount = 0
            print("Selected Child (raw):", selected_child)
            print("Amount:", amount)
            if selected_child and amount > 0:
                try:
                    child_id = int(selected_child)
                except ValueError:
                    flash('Invalid child selection.', 'error')
                else:
                    if 'children' in session and child_id in session['children']:
                        child_index = session['children'].index(child_id)
                        user = User.get_by_id(child_id)
                        if user:
                            user.update_balance(child_id, amount, description=description)
                            session['children_balances'][child_index] -= amount
                            session['children_spent'][child_index] += amount
                            flash(f"Updated balance for {session['children_name'][child_index]} by ${amount}.", 'success')
                        else:
                            flash('Child not found.', 'error')
                    else:
                        flash('Child not found in session.', 'error')
            else:
                flash('Please select a child and enter a valid amount.', 'error')

        if session.get('privilege') == 1:
            if session.get('children_name'):
                for idx, child_name in enumerate(session.get('children_name', [])):
                    spent = session.get('children_spent', [0] * len(session['children_name']))[idx] if idx < len(session.get('children_spent', [])) else 0
                    charts.append(create_half_donut_chart(child_name, spent))
            else:
                charts.append(create_half_donut_chart('No Child', 0))
        else:
            current_user = User.get_by_id(session.get('user_id'))
            if current_user:
                cur = connect_db().cursor()
                cur.execute('SELECT balance, spent, username FROM users WHERE id = ?', (current_user.id,))
                result = cur.fetchone()
                if result:
                    balance, spent, username = result
                    charts.append(create_half_donut_chart(username, spent))
                    # Load this child's transactions to display
                    transactions = User.get_transactions(current_user.id)
                else:
                    charts.append(create_half_donut_chart('Child', 0))
            else:
                charts.append(create_half_donut_chart('Child', 0))

    return render_template('index.html', charts=charts, transactions=transactions)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.get_by_username(username)
        if user and user.sign_in(password):
            return redirect(url_for('index'))
    return render_template('sign_in.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('con-password')
        User.sign_up(username=username, email=email, password=password, confirm_password=confirm_password)
        return redirect(url_for('sign_in'))
    return render_template('sign_up.html')

@app.route('/sign_out')
def sign_out():
    User.sign_out()
    flash('Signed out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/add_child', methods=['GET', 'POST'])
def add_child():
    if request.method == 'POST':
        parent = User.get_by_id(session.get('user_id'))
        if parent:
            if parent.add_child(request.form.get('username'), request.form.get('password'), request.form.get('con-password')):
                return redirect(url_for('index'))
        else:
            flash('You must be signed in to add a child.', 'error')
    return render_template('child_signup.html')

@app.route('/remove_child/<int:child_id>', methods=['POST'])
def remove_child(child_id):
    parent = User.get_by_id(session.get('user_id'))
    if parent:
        parent.remove_child(child_id)
    else:
        flash('You must be signed in to remove a child.', 'error')
    return redirect(url_for('index'))


@app.route('/transactions/<int:child_id>', methods=['GET'])
def transactions(child_id):
    if not session.get('logged_in'):
        flash('Not authorized to view transactions.', 'error')
        return redirect(url_for('index'))

    user_privilege = session.get('privilege')
    if user_privilege == 1:
        parent = User.get_by_id(session.get('user_id'))
        if child_id not in parent.children:
            flash('Child not found.', 'error')
            return redirect(url_for('index'))
    elif user_privilege == 0:
        if child_id != session.get('user_id'):
            flash('Not authorized to view another child\'s transactions.', 'error')
            return redirect(url_for('index'))
    else:
        flash('Not authorized to view transactions.', 'error')
        return redirect(url_for('index'))

    txs = User.get_transactions(child_id)
    child = User.get_by_id(child_id)
    child_name = child.username if child else 'Unknown'
    return render_template('transactions.html', transactions=txs, child_id=child_id, child_name=child_name)


@app.route('/reverse_transaction/<int:tx_id>/<int:child_id>', methods=['POST'])
def reverse_transaction(tx_id, child_id):
    if session.get('privilege') != 1:
        flash('Not authorized to reverse transactions.', 'error')
        return redirect(url_for('index'))
    parent = User.get_by_id(session.get('user_id'))
    if child_id not in parent.children:
        flash('Child not found.', 'error')
        return redirect(url_for('index'))
    tx = User.get_transaction_by_id(tx_id)
    if not tx or tx[1] != child_id:
        flash('Transaction not found.', 'error')
        return redirect(url_for('transactions', child_id=child_id))
    # Prevent double reversal by checking for a prior reversal with the same marker
    reversal_description = f"Reversal of tx {tx_id}: {tx[3]}"
    cur = connect_db().cursor()
    cur.execute('SELECT id FROM transactions WHERE description = ? AND user_id = ?', (reversal_description, child_id))
    if cur.fetchone():
        flash('Transaction already reversed.', 'error')
        return redirect(url_for('transactions', child_id=child_id))
    amount = tx[2]
    child_user = User.get_by_id(child_id)
    if child_user:
        # Use negative amount to add back to balance and reduce spent
        child_user.update_balance(child_id, -amount, description=reversal_description)
        flash('Transaction reversed successfully.', 'success')
        # Update session balances/spent so parent dashboard charts reflect reversal immediately
        if 'children' in session and child_id in session.get('children', []):
            try:
                idx = session['children'].index(child_id)
                # amount is original tx amount; reversing should add it back to balance and subtract from spent
                session['children_balances'][idx] += amount
                session['children_spent'][idx] -= amount
            except Exception:
                pass
    else:
        flash('Child user not found.', 'error')
    return redirect(url_for('transactions', child_id=child_id))

if __name__ == '__main__':
    app.run(debug=True)