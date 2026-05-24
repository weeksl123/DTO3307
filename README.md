# DTO3307

## Database Setup

The database name is entirely controlled by the 'DATABASE' variable. To change the name of the database, go to [line 15 in app.py](./app.py#L15) prior to running the program for the first time. If you do change it after running the project for the first time then you will have multiple database files and possibly be confused as an account you made with the old database is no longer available after changing the database name.

## Flask Secret Key

Flask uses a secret key for security, you will need to create a ".env" file and place this line inside:
``` env
SECRET_KEY = '(Replace this text and the brackets with your secret key)'
```

To generate a secret key you can run this command in your terminal:
``` Bash
python -c 'import secrets; print(secrets.token_hex(32))'
```
The "secrets" module is designed to generate random and secure strings for passwords and security tokens.