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
            if password == confirm_password:
                hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                cur.execute('INSERT INTO users (username, email, password_hash, privilege, children, parent_id, balance, spent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (child_name, self.email, hash, 0, None, self.id, 300, 0))
                cur.execute('UPDATE users SET children = COALESCE(children, "") || ? WHERE id = ?', (',' + str(cur.lastrowid), self.id))
                child_id = cur.lastrowid
                self.children.append(child_id)
                session['children_spent'].append(0)
                flash('Child account added successfully!', 'success')
                return render_template('index.html')
            else:
                flash('Passwords do not match.', 'error')
        else:
            flash('Only parent accounts can add children.', 'error')
    
    def remove_child(self, child_id):
        cur = connect_db().cursor()
        cur.execute('DELETE FROM users WHERE id = ?', (child_id,))
        cur.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name = 'users'")
        self.children.remove(child_id)
        flash('Child account removed successfully!', 'success')

    def update_balance(self, child_id, amount):
        cur = connect_db().cursor()
        cur.execute('UPDATE users SET balance = balance - ?, spent = spent + ? WHERE id = ?', (amount, amount, child_id))
        flash('Balance updated successfully!', 'success')

####################### Chart setup #######################
def create_half_donut_chart(Title, Value):
    chart = pygal.Pie(
        inner_radius=0.5, 
        half_pie=True, 
        style = pygal.style.Style(background='transparent'),
        show_legend=False, 
        margin=10
    )
    chart.title = Title
    chart.add('Spent', Value)
    chart.add('Remaining', 300 - Value)
    return chart

####################### Routes #######################
@app.route('/', methods=['GET', 'POST'])
def index():
    if session.get('logged_in', False):
        if request.method == 'POST':
            selected_child = request.form.get('child')
            amount = int(request.form.get('amount'))
            print("Selected Child:", selected_child)
            print("Amount:", amount)
            if selected_child and amount > 0:
                child_index = session['children_name'].index(selected_child)
                child_id = session['children'][child_index]
                user = User.get_by_id(child_id)
                if user:
                    user.update_balance(child_id, amount)
                    session['children_balances'][child_index] -= amount
                    session['children_spent'][child_index] += amount
                    flash(f'Updated balance for {selected_child} by ${amount}.', 'success')
                else:
                    flash('Child not found.', 'error')
            else:
                flash('Please select a child and enter a valid amount.', 'error')
        
        chart1 = create_half_donut_chart(session['children_name'][0] if session['children_name'] else 'Child 1', session['children_spent'][0] if session['children_spent'] else 0)
        chart2 = create_half_donut_chart(session['children_name'][1] if len(session['children_name']) > 1 else 'Child 2', session['children_spent'][1] if len(session['children_spent']) > 1 else 0)
        #chart3 = create_half_donut_chart(session['children_name'][2] if len(session['children_name']) > 2 else 'Child 3', session['children_spent'][2] if len(session['children_spent']) > 2 else 0)

        #chart1 = create_half_donut_chart('Nikau', 75)
        #chart2 = create_half_donut_chart('Hana', 50)
        chart3 = create_half_donut_chart('Tia', 25)

        return render_template('index.html', chart1=chart1, chart2=chart2, chart3=chart3)
    else:
        return render_template('index.html')

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
            parent.add_child(request.form.get('username'), request.form.get('password'), request.form.get('con-password'))
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

if __name__ == '__main__':
    app.run(debug=True)