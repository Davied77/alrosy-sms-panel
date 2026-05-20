from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User, Role
from app.models.sms import SMSRange, SMSNumber, SMSCDR
from app.models.activity import ActivityLog, News
from app import db
from functools import wraps
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('⛔ Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@login_required
@admin_required
def index():
    total_users = User.query.count()
    total_numbers = SMSNumber.query.count()
    total_sms = SMSCDR.query.count()
    total_ranges = SMSRange.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    available_numbers = SMSNumber.query.filter_by(is_reserved=False).count()
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    last_7_days = []
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        count = SMSCDR.query.filter(db.func.date(SMSCDR.created_at) == date).count()
        last_7_days.insert(0, {'date': str(date), 'count': count})
    
    return render_template('admin/dashboard.html',
                         total_users=total_users, total_numbers=total_numbers,
                         total_sms=total_sms, total_ranges=total_ranges,
                         active_users=active_users, available_numbers=available_numbers,
                         recent_activities=recent_activities, last_7_days=last_7_days)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    user_list = User.query.all()
    return render_template('admin/users.html', users=user_list)

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'client')
    
    if User.query.filter_by(username=username).first():
        flash('❌ Username already exists.', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User(username=username, email=email, role=Role(role))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    ActivityLog.log(current_user.id, '👤 Create User', f'Created: {username}')
    flash('✅ User created successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.username = request.form.get('username', user.username)
    user.email = request.form.get('email', user.email)
    user.role = Role(request.form.get('role', user.role.value))
    user.sms_limit = int(request.form.get('sms_limit', user.sms_limit))
    
    if request.form.get('password'):
        user.set_password(request.form.get('password'))
    
    db.session.commit()
    ActivityLog.log(current_user.id, '✏️ Edit User', f'Edited: {user.username}')
    flash('✅ User updated!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('❌ Cannot delete yourself!', 'danger')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    ActivityLog.log(current_user.id, '🗑️ Delete User', f'Deleted: {user.username}')
    flash('✅ User deleted!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'✅ User {status}!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/sms-numbers')
@login_required
@admin_required
def sms_numbers():
    numbers = SMSNumber.query.all()
    return render_template('admin/sms_numbers.html', numbers=numbers)

@admin_bp.route('/sms-numbers/delete/<int:number_id>')
@login_required
@admin_required
def delete_number(number_id):
    number = SMSNumber.query.get_or_404(number_id)
    db.session.delete(number)
    db.session.commit()
    flash('✅ Number deleted!', 'success')
    return redirect(url_for('admin.sms_numbers'))

@admin_bp.route('/sms-ranges')
@login_required
@admin_required
def sms_ranges():
    ranges = SMSRange.query.all()
    return render_template('admin/sms_ranges.html', ranges=ranges)

@admin_bp.route('/sms-ranges/create', methods=['POST'])
@login_required
@admin_required
def create_sms_range():
    range_obj = SMSRange(
        name=request.form.get('name'),
        country=request.form.get('country'),
        prefix=request.form.get('prefix'),
        total_numbers=int(request.form.get('total_numbers', 0)),
        price=float(request.form.get('price', 0))
    )
    db.session.add(range_obj)
    db.session.commit()
    flash('✅ SMS Range created!', 'success')
    return redirect(url_for('admin.sms_ranges'))

@admin_bp.route('/sms-send', methods=['GET', 'POST'])
@login_required
@admin_required
def sms_send():
    if request.method == 'POST':
        recipients = request.form.get('recipients').strip().split('\n')
        message = request.form.get('message')
        sender = request.form.get('sender', 'ALROSY')
        
        count = 0
        for recipient in recipients:
            recipient = recipient.strip()
            if recipient:
                cdr = SMSCDR(user_id=current_user.id, sender=sender, recipient=recipient, message=message, status='sent', cost=0.05)
                db.session.add(cdr)
                count += 1
        
        db.session.commit()
        flash(f'✅ SMS sent to {count} recipients!', 'success')
        return redirect(url_for('admin.sms_send'))
    
    return render_template('admin/sms_send.html')

@admin_bp.route('/sms-cdr')
@login_required
@admin_required
def sms_cdr():
    records = SMSCDR.query.order_by(SMSCDR.created_at.desc()).limit(200).all()
    return render_template('admin/sms_cdr.html', records=records)

@admin_bp.route('/news')
@login_required
@admin_required
def news():
    news_list = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news.html', news_list=news_list)

@admin_bp.route('/news/create', methods=['POST'])
@login_required
@admin_required
def create_news():
    news = News(title=request.form.get('title'), content=request.form.get('content'), is_published=True)
    db.session.add(news)
    db.session.commit()
    flash('✅ News published!', 'success')
    return redirect(url_for('admin.news'))

@admin_bp.route('/news/<int:news_id>/delete')
@login_required
@admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()
    flash('✅ News deleted!', 'success')
    return redirect(url_for('admin.news'))

@admin_bp.route('/activity-logs')
@login_required
@admin_required
def activity_logs():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(500).all()
    return render_template('admin/activity_logs.html', logs=logs)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        flash('✅ Settings updated!', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html')
