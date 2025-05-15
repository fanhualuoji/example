import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import current_app

class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_id(user_id):
        conn = sqlite3.connect(current_app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, role FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2],
                role=user_data[3]
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        conn = sqlite3.connect(current_app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2],
                role=user_data[3]
            )
        return None
    
    @staticmethod
    def create_user(username, password, role='user'):
        conn = sqlite3.connect(current_app.config['DATABASE'])
        cursor = conn.cursor()
        
        try:
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                (username, password_hash, role)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return User(user_id, username, password_hash, role)
        except sqlite3.IntegrityError:
            conn.close()
            return None 