####################### Importing necessary libraries #######################
from flask import Flask, render_template, request, redirect, url_for, g, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pygal
from pygal.style import Style
import base64
import re
import socket
from dotenv import load_dotenv
import os
import datetime

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def domain_exists(domain):
    try:
        socket.getaddrinfo(domain, None)
        return True
    except OSError:
        return False

def is_valid_email(email):
    if not email or not EMAIL_REGEX.match(email):
        return False

    domain = email.split('@')[-1].strip()
    return domain_exists(domain)

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
        "annual_balance" INTEGER,
        "bonus_threshold" INTEGER DEFAULT 50,
        "dark_mode" INTEGER DEFAULT 0,
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

def should_reset_balances():
    now = datetime.datetime.now()
    # Reset yearly at midnight on January 1 (commented out for testing):
    # if now.month == 1 and now.day == 1 and now.hour == 0 and now.minute == 0 and now.second < 5:  # Add a small window to ensure it only triggers once
    #     return True
    # Reset at lunch each day for testing purposes:
    return now.hour == 12 and now.minute == 0 and now.second < 5  # Add a small window to ensure it only triggers once


def reset_balances_if_due():
    if should_reset_balances():
        cur = connect_db().cursor()
        cur.execute('UPDATE users SET balance = COALESCE(annual_balance, 300), spent = 0 WHERE privilege = 0')
        flash('Balances reset for testing purposes.', 'info')


@app.before_request
def before_request():
    reset_balances_if_due()


def connect_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.commit()
        db.close()

####################### Classes #######################
class User:
    def __init__(self, id, email, username, privilege, children, parent_id, bonus_threshold=50):
        self.id = id
        self.email = email
        if privilege == 1:
            self.parent_id = None
        else:
            self.parent_id = parent_id
        self.username = username
        self.privilege = privilege
        self.bonus_threshold = bonus_threshold or 50
        self.children = []
        if children:
            self.children = [int(child_id) for child_id in children.split(',') if child_id]
        else:
            self.children = []


    @staticmethod
    def get_by_username(username):
        cur = connect_db().cursor()
        cur.execute('SELECT id, email, username, privilege, children, parent_id, bonus_threshold FROM users WHERE username = ?', (username,))
        result = cur.fetchone()
        if result:
            return User(*result)
        return None

    @staticmethod
    def get_by_id(user_id):
        cur = connect_db().cursor()
        cur.execute('SELECT id, email, username, privilege, children, parent_id, bonus_threshold FROM users WHERE id = ?', (user_id,))
        result = cur.fetchone()
        if result:
            return User(*result)
        return None

    def sign_in(self, password):
        cur = connect_db().cursor()
        # Also fetch stored dark_mode preference (0/1) and bonus threshold
        cur.execute('SELECT password_hash, dark_mode, bonus_threshold FROM users WHERE id = ?', (self.id,))
        result = cur.fetchone()
        if result and check_password_hash(result[0], password):
            session['user_id'] = self.id
            session['username'] = self.username
            session['privilege'] = self.privilege
            session['logged_in'] = True
            session['children'] = self.children
            session['children_name'] = []
            session['children_balances'] = []
            session['children_spent'] = []
            # Load dark mode preference (treat None as off)
            try:
                session['dark_mode'] = bool(result[1])
            except Exception:
                session['dark_mode'] = False
            try:
                session['bonus_threshold'] = int(result[2]) if result[2] is not None else BONUS_THRESHOLD
            except Exception:
                session['bonus_threshold'] = BONUS_THRESHOLD
            for child_id in self.children:
                cur.execute('SELECT username, balance, spent FROM users WHERE id = ?', (child_id,))
                child_result = cur.fetchone()
                session['children_name'].append(child_result[0] if child_result else "Unknown")
                session['children_balances'].append(child_result[1] if child_result else 0)
                session['children_spent'].append(child_result[2] if child_result else 0)

            flash('Signed in successfully!', 'success')
            return True
        else: 
            flash('Invalid username or password.', 'error')
        return False
    
    @staticmethod
    def sign_up(username, email, password, confirm_password):
        cur = connect_db().cursor()
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'error')
            return False

        if password == confirm_password:
            # Check if username already exists
            cur.execute('SELECT username FROM users WHERE username = ?', (username,))
            u_result = cur.fetchone()
            cur.execute('SELECT email FROM users WHERE email = ?', (email,))
            e_result = cur.fetchone()
            if u_result is None and e_result is None:
                hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                cur.execute('INSERT INTO users (username, email, password_hash, privilege, children, parent_id) VALUES (?, ?, ?, ?, ?, ?)', (username, email, hash, 1, None, None))
                flash('Account created successfully! Please sign in.', 'success')
                return True
            else:
                flash('Username or email already exists.', 'error')
        else:
            flash('Passwords do not match.', 'error')
        return False

    @staticmethod
    def sign_out():
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('privilege', None)
        session.pop('children', None)
        session.pop('children_name', None)
        session.pop('children_balances', None)
        session.pop('children_spent', None)
        session.pop('dark_mode', None)
        session['logged_in'] = False

    def add_child(self, child_name, password, confirm_password, annual_balance=300):
        cur = connect_db().cursor()
        if self.privilege == 1:
            cur.execute('SELECT username FROM users WHERE username = ?', (child_name,))
            if cur.fetchone():
                flash('Child username already exists. Please choose a different username.', 'error')
                return False
            else:
                if password == confirm_password:
                    hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                    cur.execute('INSERT INTO users (username, email, password_hash, privilege, children, parent_id, balance, spent, annual_balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (child_name, self.email, hash, 0, None, self.id, annual_balance, 0, annual_balance))
                    child_id = cur.lastrowid
                    cur.execute('UPDATE users SET children = COALESCE(children, "") || ? WHERE id = ?', (',' + str(child_id), self.id))
                    self.children.append(child_id)
                    session.setdefault('children', []).append(child_id)
                    session.setdefault('children_name', []).append(child_name)
                    session.setdefault('children_balances', []).append(annual_balance)
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

    def change_password(self, old_password, new_password, confirm_password):
        """Change user password. Returns (success, message)."""
        if new_password != confirm_password:
            return False, "New passwords do not match."
        
        cur = connect_db().cursor()
        cur.execute('SELECT password_hash FROM users WHERE id = ?', (self.id,))
        result = cur.fetchone()
        
        if not result or not check_password_hash(result[0], old_password):
            return False, "Current password is incorrect."
        
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
        cur.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, self.id))
        return True, "Password changed successfully!"

    def update_child_allowance(self, child_id, new_allowance):
        """Update a child's annual allowance."""
        if child_id not in self.children:
            return False, "Child not found."
        
        try:
            new_allowance = int(float(new_allowance))
            if new_allowance < 0:
                return False, "Allowance must be non-negative."
        except (ValueError, TypeError):
            return False, "Invalid allowance amount."
        
        cur = connect_db().cursor()
        cur.execute('SELECT spent FROM users WHERE id = ?', (child_id,))
        spent_result = cur.fetchone()
        if not spent_result:
            return False, "Child not found."
        spent = spent_result[0] or 0
        new_balance = new_allowance - spent
        cur.execute('UPDATE users SET annual_balance = ?, balance = ? WHERE id = ?', (new_allowance, new_balance, child_id))

        # Keep session data consistent if this child is already loaded in session.
        if 'children' in session and child_id in session.get('children', []):
            try:
                idx = session['children'].index(child_id)
                session['children_balances'][idx] = new_balance
            except Exception:
                pass
        return True, "Allowance updated successfully!"

    def change_child_password(self, child_id, new_password, confirm_password):
        """Change a child's password."""
        if child_id not in self.children:
            return False, "Child not found."
        
        if new_password != confirm_password:
            return False, "New passwords do not match."
        
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
        cur = connect_db().cursor()
        cur.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, child_id))
        return True, "Child password changed successfully!"

####################### Family and child Classes #######################
BONUS_THRESHOLD = 50

class Child:
    def __init__(self, id, username, balance, spent, annual_balance, parent_id):
        self.id = id
        self.username = username
        self.balance = balance or 0
        self.spent = spent or 0
        self.annual_balance = annual_balance or 0
        self.parent_id = parent_id

    @property
    def on_track(self):
        return self.balance > BONUS_THRESHOLD

    def update_balance(self, amount, description=None):
        if amount > self.balance:
            flash('Cannot spend more than the remaining allowance.', 'error')
            return False
        cur = connect_db().cursor()
        cur.execute('UPDATE users SET balance = balance - ?, spent = spent + ? WHERE id = ?', (amount, amount, self.id))
        cur.execute('INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)', (self.id, amount, description))
        self.balance -= amount
        self.spent += amount
        flash('Balance updated successfully!', 'success')
        return True

    @staticmethod
    def get_by_id(child_id):
        cur = connect_db().cursor()
        cur.execute('SELECT id, username, balance, spent, annual_balance, parent_id FROM users WHERE id = ?', (child_id,))
        row = cur.fetchone()
        return Child(*row) if row else None

class Family:
    def __init__(self, parent_user, children):
        self.parent = parent_user
        self.children = children or []

    @classmethod
    def load_for_parent(cls, parent_id):
        parent_user = User.get_by_id(parent_id)
        if not parent_user:
            return None
        children = []
        for child_id in parent_user.children:
            child = Child.get_by_id(child_id)
            if child:
                children.append(child)
        return cls(parent_user, children)

    def get_child(self, child_id):
        return next((child for child in self.children if child.id == child_id), None)

    def reload_children(self):
        children = []
        for child_id in self.parent.children:
            child = Child.get_by_id(child_id)
            if child:
                children.append(child)
        self.children = children

    def update_session_data(self):
        session['children'] = [child.id for child in self.children]
        session['children_name'] = [child.username for child in self.children]
        session['children_balances'] = [child.balance for child in self.children]
        session['children_spent'] = [child.spent for child in self.children]

####################### Chart setup #######################

class DataUriChart:
    def __init__(self, data_uri):
        self._data_uri = data_uri

    def render_data_uri(self):
        return self._data_uri


def create_half_donut_chart(title, spent_amount, total=300):
    remaining = total - spent_amount
    if remaining < 0:
        remaining = 0

    dark_mode = session.get('dark_mode', True)
    style = Style(
        background='transparent',
        plot_background='transparent',
        foreground='#e0e0e0' if dark_mode else '#111111',
        foreground_strong='#ffffff' if dark_mode else '#000000',
        foreground_subtle='#bbbbbb' if dark_mode else '#444444',
        tooltip_font_size=16
    )

    chart = pygal.Pie(
        inner_radius=0.5,
        half_pie=True,
        style=style,
        show_legend=False,
        margin=10
    )
    chart.title = title
    chart.add('Spent', spent_amount)
    chart.add('Remaining', remaining)

    svg = chart.render(is_unicode=True)
    chart_id_match = re.search(r'<svg[^>]*id="([^"]+)"', svg)
    if chart_id_match:
        chart_id = chart_id_match.group(1)
        tooltip_color = '#ffffff' if dark_mode else '#111111'
        override_css = f'#{chart_id} .tooltip text {{ fill: {tooltip_color}; }}'
        svg = svg.replace('</style>', f'{override_css}</style>', 1)

    data_uri = 'data:image/svg+xml;charset=utf-8;base64,' + base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return DataUriChart(data_uri)

####################### Routes #######################
@app.route('/', methods=['GET', 'POST'])
def index():
    charts = []
    transactions = []
    children_status = []
    bonus_threshold = 50

    child_balance = 0
    child_bonus_on_track = False

    if session.get('logged_in', False):
        bonus_threshold = session.get('bonus_threshold', BONUS_THRESHOLD)
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
                    family = Family.load_for_parent(session.get('user_id')) if session.get('privilege') == 1 else None
                    child = family.get_child(child_id) if family else None
                    if child:
                        if child.update_balance(amount, description=description):
                            family.reload_children()
                            family.update_session_data()
                        else:
                            # An error flash is already set by the child update method
                            pass
                    else:
                        flash('Child not found.', 'error')
            else:
                flash('Please select a child and enter a valid amount.', 'error')

        if session.get('privilege') == 1:
            family = Family.load_for_parent(session.get('user_id'))
            if family and family.children:
                for child in family.children:
                    charts.append(create_half_donut_chart(child.username, child.spent, total=child.annual_balance))
                    children_status.append({
                        'id': child.id,
                        'name': child.username,
                        'balance': child.balance,
                        'on_track': child.balance > bonus_threshold
                    })
                family.update_session_data()
            else:
                charts.append(create_half_donut_chart('No Child', 0))
        else:
            current_user = User.get_by_id(session.get('user_id'))
            if current_user:
                parent = User.get_by_id(current_user.parent_id) if current_user.parent_id else None
                bonus_threshold = parent.bonus_threshold if parent else bonus_threshold
                cur = connect_db().cursor()
                cur.execute('SELECT balance, spent, username, annual_balance FROM users WHERE id = ?', (current_user.id,))
                result = cur.fetchone()
                if result:
                    balance, spent, username, annual_balance = result
                    charts.append(create_half_donut_chart(username, spent, total=annual_balance or 300))
                    # Load this child's transactions to display
                    transactions = User.get_transactions(current_user.id)
                    child_balance = balance
                    child_bonus_on_track = balance > bonus_threshold
                else:
                    charts.append(create_half_donut_chart('Child', 0))
                    child_balance = 0
                    child_bonus_on_track = False
            else:
                charts.append(create_half_donut_chart('Child', 0))
                child_balance = 0
                child_bonus_on_track = False

    return render_template('index.html', charts=charts, transactions=transactions, children_status=children_status, child_balance=child_balance, child_bonus_on_track=child_bonus_on_track)

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
        success = User.sign_up(username=username, email=email, password=password, confirm_password=confirm_password)
        if success:
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
            annual_balance_input = request.form.get('annual_balance', '300')
            try:
                annual_balance = int(float(annual_balance_input))
                if annual_balance < 0:
                    annual_balance = 300
            except ValueError:
                annual_balance = 300
            if parent.add_child(request.form.get('username'), request.form.get('password'), request.form.get('con-password'), annual_balance=annual_balance):
                return redirect(url_for('index'))
        else:
            flash('You must be signed in to add a child.', 'error')
    return render_template('child_signup.html')

@app.route('/remove_child/<int:child_id>', methods=['POST'])
def remove_child(child_id):
    parent = User.get_by_id(session.get('user_id'))
    if parent:
        parent.remove_child(child_id)
        family = Family.load_for_parent(parent.id)
        if family:
            family.update_session_data()
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
    child = Child.get_by_id(child_id)
    child_name = child.username if child else 'Unknown'
    child_balance = child.balance if child else 0
    child_bonus_on_track = False
    if child:
        if session.get('privilege') == 1:
            parent = User.get_by_id(session.get('user_id'))
            bonus_threshold = parent.bonus_threshold if parent else BONUS_THRESHOLD
        else:
            parent = User.get_by_id(child.parent_id) if child.parent_id else None
            bonus_threshold = parent.bonus_threshold if parent else BONUS_THRESHOLD
        child_bonus_on_track = child.balance > bonus_threshold
    return render_template('transactions.html', transactions=txs, child_id=child_id, child_name=child_name, child_balance=child_balance, child_bonus_on_track=child_bonus_on_track)


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
    # Prevent reversing a reversal transaction and double reversal of the same original transaction
    if tx[3] and tx[3].startswith('Reversal of tx '):
        flash('Cannot reverse a reversal transaction.', 'error')
        return redirect(url_for('transactions', child_id=child_id))

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

@app.route('/settings', methods=['GET'])
def settings():
    if not session.get('logged_in'):
        flash('You must be signed in to access settings.', 'error')
        return redirect(url_for('sign_in'))
    
    user = User.get_by_id(session.get('user_id'))
    children_info = []
    bonus_threshold = session.get('bonus_threshold', BONUS_THRESHOLD)
    
    if session.get('privilege') == 1:
        family = Family.load_for_parent(session.get('user_id'))
        if family:
            children_info = family.children
            bonus_threshold = user.bonus_threshold
    
    return render_template('settings.html', user=user, children_info=children_info, bonus_threshold=bonus_threshold)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if not session.get('logged_in'):
        flash('You must be signed in.', 'error')
        return redirect(url_for('sign_in'))
    
    user = User.get_by_id(session.get('user_id'))
    
    # Handle password change
    if request.form.get('change_password'):
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_new_password', '')
        
        if old_password and new_password:
            success, message = user.change_password(old_password, new_password, confirm_password)
            flash(message, 'success' if success else 'error')
    
    # Handle child allowance updates (parent only)
    if session.get('privilege') == 1 and request.form.get('update_allowance'):
        child_id_str = request.form.get('child_id', '')
        new_allowance = request.form.get('allowance', '')
        
        try:
            child_id = int(child_id_str)
            success, message = user.update_child_allowance(child_id, new_allowance)
            flash(message, 'success' if success else 'error')
        except ValueError:
            flash('Invalid child or allowance.', 'error')
    
    # Handle child password change (parent only)
    if session.get('privilege') == 1 and request.form.get('change_child_password'):
        child_id_str = request.form.get('child_id_pwd', '')
        new_password = request.form.get('child_new_password', '')
        confirm_password = request.form.get('child_confirm_password', '')
        
        try:
            child_id = int(child_id_str)
            success, message = user.change_child_password(child_id, new_password, confirm_password)
            flash(message, 'success' if success else 'error')
        except ValueError:
            flash('Invalid child.', 'error')

    # Handle bonus threshold update (parent only)
    if session.get('privilege') == 1 and request.form.get('update_bonus_threshold'):
        new_threshold_str = request.form.get('bonus_threshold', '')
        try:
            new_threshold = int(float(new_threshold_str))
            if new_threshold < 0:
                raise ValueError
            cur = connect_db().cursor()
            cur.execute('UPDATE users SET bonus_threshold = ? WHERE id = ?', (new_threshold, user.id))
            session['bonus_threshold'] = new_threshold
            flash('Bonus threshold updated successfully.', 'success')
        except ValueError:
            flash('Invalid bonus threshold.', 'error')

    return redirect(url_for('settings'))


@app.route('/set_dark_mode', methods=['POST'])
def set_dark_mode():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401

    data = None
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None

    if not data:
        # fallback to form
        data = request.form

    dark_val = data.get('dark') if isinstance(data, dict) else None
    # Accept a few truthy representations
    is_dark = str(dark_val).lower() in ('1', 'true', 'yes', 'on')

    cur = connect_db().cursor()
    try:
        cur.execute('UPDATE users SET dark_mode = ? WHERE id = ?', (1 if is_dark else 0, session.get('user_id')))
        flash('Appearance updated.', 'success')
    except Exception:
        return jsonify({'error': 'Failed to update preference'}), 500

    session['dark_mode'] = bool(is_dark)
    return jsonify({'dark_mode': session['dark_mode']})

if __name__ == '__main__':
    app.run(debug=True)