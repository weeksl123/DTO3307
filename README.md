# DTO3307 Documentation

## Overview

My project for DTO3307 is a Flask web application managed by parent accounts for budget tracking and transaction history.

- Parents can create child accounts, update child balances, and reverse transactions.
- Children can sign in, view their own spending chart, and see transaction history.
- The app stores users and transactions in a local SQLite database.

## Requirements

- Python 3.8+
- Flask
- Werkzeug
- pygal
- python-dotenv

## Installation

1. Clone the repository:

```bash
git clone https://github.com/weeksl123/DTO3307.git
cd DTO3307
```

2. Create a virtual environment (Optional):

```bash
python -m venv venv
```

3. Activate the environment (Only necessary if you did step 2):

- PowerShell:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- Command Prompt:
  ```cmd
  .\venv\Scripts\activate
  ```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root containing:

```env
SECRET_KEY=your-secure-secret-key
```

Generate a secure secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Database

- The database file is created automatically when `app.py` runs for the first time.
- Default database path: `./test.db`
- To change it before first run, update the `DATABASE` constant in `app.py`.

## Running the Application

Start the app with:

```bash
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser. (Or if running in Visual Studio Code, hold control and click on the link to `http://127.0.0.1:5000/` in the terminal when the program starts)

## Project Structure

- `app.py` - Flask application, routes, database setup, and core logic
- `templates/` - HTML templates used by Flask
- `static/css/style.css` - application styling
- `static/js/script.js` - front-end JavaScript
- `.env` - environment variables (should not be committed)
- `test.db` - SQLite database generated at runtime

## Application Features

- Parent registration and login
- Child account creation and management
- Balance updates and spending tracking
- Transaction logging and reversal
- Child-specific transaction history
- Spending charts rendered with pygal

## Important Routes

- `/` - dashboard and child balance update form
- `/sign_in` - sign-in page
- `/sign_up` - parent registration page
- `/sign_out` - log out
- `/add_child` - create a new child account
- `/remove_child/<int:child_id>` - delete a child account
- `/transactions/<int:child_id>` - view child transaction history
- `/reverse_transaction/<int:tx_id>/<int:child_id>` - reverse a transaction

## Database Schema

### `users`

Columns:

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `username` TEXT NOT NULL
- `email` TEXT NOT NULL
- `password_hash` TEXT NOT NULL
- `privilege` INTEGER NOT NULL
- `children` TEXT
- `parent_id` INTEGER
- `balance` INTEGER
- `spent` INTEGER
- `annual_balance` INTEGER
- `dark_mode` INTEGER DEFAULT 0

Notes:

- Parent accounts store child IDs as a comma-separated string in `children`.
- Child accounts use `parent_id` to link to the parent.
- Child accounts store balance and spent amounts.

### `transactions`

Columns:

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` INTEGER NOT NULL
- `amount` INTEGER NOT NULL
- `description` TEXT
- `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP

Notes:

- Transactions are associated with a child account by `user_id`.
- Reverse operations are stored as new transactions with negative amounts.

## Notes

- `sqlite3`, `os`, `re`, `base64`, and `datetime` are part of Python’s standard library.
- Keep `.env` private and do not commit it.
- This documentation is based on the current `app.py` implementation.


## For Assessor

### Previous Flask Experience

- [91906 - Github](https://github.com/weeksl123/91906)

### Tutorials

- [Learn Flask for Python - Full Tutorial](https://www.youtube.com/watch?v=Z1RJmh_OqeA)
- I also spent many hours learning through trial and error
- Plus many little google searches on how to do certain things here and there

### Testing

- For my documentation on the testing done to this project check out the [Testing Documentation](./Testing.md)
