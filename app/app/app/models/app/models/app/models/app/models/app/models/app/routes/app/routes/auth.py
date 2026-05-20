from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.activity import ActivityLog
from app import db
from datetime import datetime
import random

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        captcha_answer = request.form.get('captcha_answer')
        
        num1 = session.get('captcha_num1', 0)
        num2 = session.get('captcha_num2', 0)
        
        if not captcha_answer or int(captcha_answer) != (num1 + num2):
            flash('❌ Invalid security answer. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=True)
                ActivityLog.log(user.id, '🔐 Login', f'User logged in successfully', request.remote_addr)
                flash(f'✅ Welcome back, {user.username}!', 'success')
                
                if user.is_admin():
                    return redirect(url_for('admin.index'))
                return redirect(url_for('main.dashboard'))
            else:
                flash('⛔ Account is deactivated. Contact administrator.', 'danger')
        else:
            flash('❌ Invalid username or password.', 'danger')
            ActivityLog.log(None, '❌ Failed Login', f'Failed attempt for: {username}', request.remote_addr)
    
    num1 = random.randint(0, 9)
    num2 = random.randint(0, 9)
    session['captcha_num1'] = num1
    session['captcha_num2'] = num2
    
    return render_template('auth/login.html', captcha_num1=num1, captcha_num2=num2)

@auth_bp.route('/logout')
@login_required
def logout():
    ActivityLog.log(current_user.id, '🔓 Logout', 'User logged out', request.remote_addr)
    logout_user()
    flash('👋 You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('❌ Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('❌ Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email, role='client')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        ActivityLog.log(user.id, '📝 Registration', 'New user registered', request.remote_addr)
        flash('✅ Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')
