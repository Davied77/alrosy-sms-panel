from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.sms import SMSRange, SMSNumber, SMSCDR
from app.models.activity import ActivityLog, News
from app import db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    today_sms = SMSCDR.query.filter(
        SMSCDR.user_id == current_user.id,
        db.func.date(SMSCDR.created_at) == today
    ).count()
    
    week_sms = SMSCDR.query.filter(
        SMSCDR.user_id == current_user.id,
        SMSCDR.created_at >= week_ago
    ).count()
    
    month_sms = SMSCDR.query.filter(
        SMSCDR.user_id == current_user.id,
        SMSCDR.created_at >= month_ago
    ).count()
    
    my_numbers = SMSNumber.query.filter_by(user_id=current_user.id).all()
    available_ranges = SMSRange.query.filter_by(is_active=True).all()
    recent_news = News.query.filter_by(is_published=True).order_by(News.created_at.desc()).limit(5).all()
    sms_stats = current_user.get_sms_stats()
    
    return render_template('main/dashboard.html',
                         today_sms=today_sms,
                         week_sms=week_sms,
                         month_sms=month_sms,
                         my_numbers=my_numbers,
                         available_ranges=available_ranges,
                         recent_news=recent_news,
                         sms_stats=sms_stats)

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')

@main_bp.route('/my-sms-numbers')
@login_required
def my_sms_numbers():
    numbers = SMSNumber.query.filter_by(user_id=current_user.id).all()
    return render_template('main/my_numbers.html', numbers=numbers)

@main_bp.route('/sms-ranges')
@login_required
def sms_ranges():
    ranges = SMSRange.query.filter_by(is_active=True).all()
    return render_template('main/sms_ranges.html', ranges=ranges)

@main_bp.route('/sms-cdr')
@login_required
def sms_cdr_reports():
    records = SMSCDR.query.filter_by(user_id=current_user.id).order_by(SMSCDR.created_at.desc()).limit(100).all()
    return render_template('main/sms_cdr.html', records=records)

@main_bp.route('/sms-test-panel', methods=['GET', 'POST'])
@login_required
def sms_test_panel():
    if request.method == 'POST':
        recipient = request.form.get('recipient')
        message = request.form.get('message')
        sender = request.form.get('sender', 'ALROSY')
        
        cdr = SMSCDR(user_id=current_user.id, sender=sender, recipient=recipient, message=message, status='sent', cost=0.05)
        current_user.sms_used += 1
        db.session.add(cdr)
        db.session.commit()
        
        ActivityLog.log(current_user.id, '📤 Test SMS', f'Sent to {recipient}')
        flash('✅ Test SMS sent successfully!', 'success')
        return redirect(url_for('main.sms_test_panel'))
    
    return render_template('main/sms_test.html')

@main_bp.route('/payment-requests')
@login_required
def payment_requests():
    return render_template('main/payment_requests.html')

@main_bp.route('/statements')
@login_required
def statements():
    return render_template('main/statements.html')

@main_bp.route('/credit-notes')
@login_required
def credit_notes():
    return render_template('main/credit_notes.html')

@main_bp.route('/bank-accounts')
@login_required
def bank_accounts():
    return render_template('main/bank_accounts.html')

@main_bp.route('/notifications')
@login_required
def notifications():
    return render_template('main/notifications.html')

@main_bp.route('/news')
@login_required
def news_master():
    all_news = News.query.filter_by(is_published=True).order_by(News.created_at.desc()).all()
    return render_template('main/news.html', news_list=all_news)

@main_bp.route('/clients')
@login_required
def clients():
    if current_user.is_agent():
        client_list = User.query.filter_by(agent_id=current_user.id).all()
    elif current_user.is_admin():
        client_list = User.query.filter_by(role='client').all()
    else:
        client_list = []
    return render_template('main/clients.html', clients=client_list)

@main_bp.route('/my-activity')
@login_required
def my_activity():
    activities = ActivityLog.query.filter_by(user_id=current_user.id).order_by(ActivityLog.created_at.desc()).limit(100).all()
    return render_template('main/activity.html', activities=activities)
