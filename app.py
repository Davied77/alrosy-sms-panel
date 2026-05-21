from flask import Flask,render_template,request,redirect,url_for,flash,session,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,UserMixin,login_user,logout_user,login_required,current_user
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime,timedelta
from functools import wraps
import enum,secrets,random,os

app=Flask(__name__)
app.config['SECRET_KEY']=os.environ.get('SECRET_KEY','alrosy-2024-secret-key')
app.config['SQLALCHEMY_DATABASE_URI']=os.environ.get('DATABASE_URL','sqlite:///alrosy.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)
login_manager=LoginManager(app)
login_manager.login_view='login'
login_manager.login_message_category='info'

# ========== MODELS ==========
class Role(enum.Enum):
    ADMIN='admin';AGENT='agent';CLIENT='client';DEVELOPER='developer'

class User(UserMixin,db.Model):
    __tablename__='users'
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),unique=True,nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password_hash=db.Column(db.String(256))
    role=db.Column(db.Enum(Role),default=Role.CLIENT)
    is_active=db.Column(db.Boolean,default=True)
    api_token=db.Column(db.String(64),unique=True)
    sms_limit=db.Column(db.Integer,default=100)
    sms_used=db.Column(db.Integer,default=0)
    agent_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    clients=db.relationship('User',backref=db.backref('agent',remote_side=[id]),lazy='dynamic')
    def set_password(self,p):self.password_hash=generate_password_hash(p,'pbkdf2:sha256')
    def check_password(self,p):return check_password_hash(self.password_hash,p)
    def generate_api_token(self):self.api_token=secrets.token_urlsafe(32);db.session.commit();return self.api_token
    def is_admin(self):return self.role==Role.ADMIN
    def is_agent(self):return self.role==Role.AGENT
    def is_client(self):return self.role==Role.CLIENT
    def is_developer(self):return self.role==Role.DEVELOPER
    def to_dict(self):return{'id':self.id,'username':self.username,'email':self.email,'role':self.role.value,'is_active':self.is_active}

class SMSRange(db.Model):
    __tablename__='sms_ranges'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    country=db.Column(db.String(50))
    prefix=db.Column(db.String(20))
    total_numbers=db.Column(db.Integer,default=0)
    price=db.Column(db.Float,default=0.0)
    is_active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    numbers=db.relationship('SMSNumber',backref='range',lazy='dynamic')
    def get_available_count(self):return self.numbers.filter_by(is_reserved=False).count()

class SMSNumber(db.Model):
    __tablename__='sms_numbers'
    id=db.Column(db.Integer,primary_key=True)
    number=db.Column(db.String(20),nullable=False)
    range_id=db.Column(db.Integer,db.ForeignKey('sms_ranges.id'))
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=True)
    is_reserved=db.Column(db.Boolean,default=False)
    reserved_at=db.Column(db.DateTime,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    assigned_to=db.relationship('User',backref='sms_numbers')

class SMSCDR(db.Model):
    __tablename__='sms_cdr'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    sender=db.Column(db.String(20))
    recipient=db.Column(db.String(20))
    message=db.Column(db.Text)
    status=db.Column(db.String(20),default='pending')
    cost=db.Column(db.Float,default=0.0)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='sms_records')

class ActivityLog(db.Model):
    __tablename__='activity_logs'
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=True)
    action=db.Column(db.String(200))
    details=db.Column(db.Text)
    ip_address=db.Column(db.String(45))
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='activities')
    @classmethod
    def log(cls,user_id,action,details=None,ip=None):
        l=cls(user_id=user_id,action=action,details=details,ip_address=ip)
        db.session.add(l);db.session.commit()

class News(db.Model):
    __tablename__='news'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    content=db.Column(db.Text)
    is_published=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid):return User.query.get(int(uid))

# ========== AUTH ==========
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login():
    if current_user.is_authenticated:return redirect(url_for('dashboard'))
    if request.method=='POST':
        u=request.form.get('username');p=request.form.get('password');ca=request.form.get('captcha_answer','0')
        if int(ca)!=(session.get('c1',0)+session.get('c2',0)):flash('Wrong captcha','danger');return redirect(url_for('login'))
        user=User.query.filter_by(username=u).first()
        if user and user.check_password(p) and user.is_active:
            login_user(user,remember=True)
            ActivityLog.log(user.id,'Login','Logged in',request.remote_addr)
            flash(f'Welcome {u}!','success')
            if user.is_admin():return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials','danger')
    session['c1']=random.randint(0,9);session['c2']=random.randint(0,9)
    return render_template('login.html',n1=session['c1'],n2=session['c2'])

@app.route('/logout')
@login_required
def logout():
    ActivityLog.log(current_user.id,'Logout','Logged out',request.remote_addr)
    logout_user();flash('Logged out','info');return redirect(url_for('login'))

# ========== DASHBOARD ==========
@app.route('/dashboard')
@login_required
def dashboard():
    today=datetime.utcnow().date()
    w=SMSCDR.query.filter(SMSCDR.user_id==current_user.id,SMSCDR.created_at>=today-timedelta(days=7)).count()
    m=SMSCDR.query.filter(SMSCDR.user_id==current_user.id,SMSCDR.created_at>=today-timedelta(days=30)).count()
    t=SMSCDR.query.filter(SMSCDR.user_id==current_user.id,db.func.date(SMSCDR.created_at)==today).count()
    nums=SMSNumber.query.filter_by(user_id=current_user.id).all()
    ranges=SMSRange.query.filter_by(is_active=True).all()
    news=News.query.filter_by(is_published=True).order_by(News.created_at.desc()).limit(5).all()
    return render_template('dashboard.html',today_sms=t,week_sms=w,month_sms=m,my_numbers=nums,available_ranges=ranges,recent_news=news)

@app.route('/my-numbers')
@login_required
def my_numbers():
    nums=SMSNumber.query.filter_by(user_id=current_user.id).all()
    return render_template('my_numbers.html',numbers=nums)

@app.route('/ranges')
@login_required
def ranges():
    r=SMSRange.query.filter_by(is_active=True).all()
    return render_template('ranges.html',ranges=r)

@app.route('/cdr')
@login_required
def cdr():
    recs=SMSCDR.query.filter_by(user_id=current_user.id).order_by(SMSCDR.created_at.desc()).limit(100).all()
    return render_template('cdr.html',records=recs)

@app.route('/test-sms',methods=['GET','POST'])
@login_required
def test_sms():
    if request.method=='POST':
        cdr=SMSCDR(user_id=current_user.id,sender=request.form.get('sender','ALROSY'),recipient=request.form.get('recipient'),message=request.form.get('message'),status='sent',cost=0.05)
        db.session.add(cdr);db.session.commit()
        ActivityLog.log(current_user.id,'Test SMS',f"Sent to {request.form.get('recipient')}")
        flash('SMS sent!','success');return redirect(url_for('test_sms'))
    return render_template('test_sms.html')

@app.route('/profile')
@login_required
def profile():return render_template('profile.html')

@app.route('/news-page')
@login_required
def news_page():
    n=News.query.filter_by(is_published=True).order_by(News.created_at.desc()).all()
    return render_template('news_page.html',news_list=n)

@app.route('/clients')
@login_required
def clients():
    if current_user.is_agent():cl=User.query.filter_by(agent_id=current_user.id).all()
    elif current_user.is_admin():cl=User.query.filter_by(role=Role.CLIENT).all()
    else:cl=[]
    return render_template('clients.html',clients=cl)

@app.route('/activity')
@login_required
def activity():
    a=ActivityLog.query.filter_by(user_id=current_user.id).order_by(ActivityLog.created_at.desc()).limit(100).all()
    return render_template('activity.html',activities=a)

# ========== ADMIN ==========
def admin_required(f):
    @wraps(f)
    def d(*a,**k):
        if not current_user.is_admin():flash('Admin only','danger');return redirect(url_for('login'))
        return f(*a,**k)
    return d

@app.route('/admin')
@login_required
@admin_required
def admin():
    tu=User.query.count();tn=SMSNumber.query.count();ts=SMSCDR.query.count();tr=SMSRange.query.count()
    ra=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    return render_template('admin.html',total_users=tu,total_numbers=tn,total_sms=ts,total_ranges=tr,recent_activities=ra)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    ul=User.query.all();return render_template('admin_users.html',users=ul)

@app.route('/admin/users/create',methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    u=User(username=request.form.get('username'),email=request.form.get('email'),role=Role(request.form.get('role','client')))
    u.set_password(request.form.get('password'));db.session.add(u);db.session.commit()
    ActivityLog.log(current_user.id,'Create User',f'Created {u.username}');flash('User created!','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/delete')
@login_required
@admin_required
def admin_delete_user(uid):
    u=User.query.get_or_404(uid)
    if u.id!=current_user.id:db.session.delete(u);db.session.commit();flash('Deleted!','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/toggle')
@login_required
@admin_required
def admin_toggle_user(uid):
    u=User.query.get_or_404(uid);u.is_active=not u.is_active;db.session.commit();flash('Toggled!','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/numbers')
@login_required
@admin_required
def admin_numbers():
    nums=SMSNumber.query.all();return render_template('admin_numbers.html',numbers=nums)

@app.route('/admin/numbers/<int:nid>/delete')
@login_required
@admin_required
def admin_delete_number(nid):
    n=SMSNumber.query.get_or_404(nid);db.session.delete(n);db.session.commit();flash('Deleted!','success')
    return redirect(url_for('admin_numbers'))

@app.route('/admin/ranges')
@login_required
@admin_required
def admin_ranges():
    r=SMSRange.query.all();return render_template('admin_ranges.html',ranges=r)

@app.route('/admin/ranges/create',methods=['POST'])
@login_required
@admin_required
def admin_create_range():
    r=SMSRange(name=request.form.get('name'),country=request.form.get('country'),prefix=request.form.get('prefix'),total_numbers=int(request.form.get('total_numbers',0)),price=float(request.form.get('price',0)))
    db.session.add(r);db.session.commit();flash('Range created!','success')
    return redirect(url_for('admin_ranges'))

@app.route('/admin/send',methods=['GET','POST'])
@login_required
@admin_required
def admin_send():
    if request.method=='POST':
        for rec in request.form.get('recipients','').split('\n'):
            if rec.strip():
                c=SMSCDR(user_id=current_user.id,sender=request.form.get('sender','ALROSY'),recipient=rec.strip(),message=request.form.get('message'),status='sent',cost=0.05)
                db.session.add(c)
        db.session.commit();flash('SMS sent!','success');return redirect(url_for('admin_send'))
    return render_template('admin_send.html')

@app.route('/admin/cdr')
@login_required
@admin_required
def admin_cdr():
    recs=SMSCDR.query.order_by(SMSCDR.created_at.desc()).limit(200).all()
    return render_template('admin_cdr.html',records=recs)

@app.route('/admin/news',methods=['GET','POST'])
@login_required
@admin_required
def admin_news():
    if request.method=='POST':
        n=News(title=request.form.get('title'),content=request.form.get('content'),is_published=True)
        db.session.add(n);db.session.commit();flash('Published!','success')
    nl=News.query.order_by(News.created_at.desc()).all()
    return render_template('admin_news.html',news_list=nl)

@app.route('/admin/news/<int:nid>/delete')
@login_required
@admin_required
def admin_delete_news(nid):
    n=News.query.get_or_404(nid);db.session.delete(n);db.session.commit();flash('Deleted!','success')
    return redirect(url_for('admin_news'))

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    l=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(500).all()
    return render_template('admin_logs.html',logs=l)

# ========== API ==========
def api_auth(f):
    @wraps(f)
    def d(*a,**k):
        token=request.headers.get('Authorization','').replace('Bearer ','')
        u=User.query.filter_by(api_token=token).first()
        if not u:return jsonify({'error':'Invalid token'}),401
        return f(u,*a,**k)
    return d

@app.route('/api/sms-numbers')
@api_auth
def api_numbers(u):
    nums=SMSNumber.query.filter_by(user_id=u.id).all()
    return jsonify([{'id':n.id,'number':n.number,'reserved':n.is_reserved} for n in nums])

@app.route('/api/send-sms',methods=['POST'])
@api_auth
def api_send(u):
    d=request.get_json()
    c=SMSCDR(user_id=u.id,sender=d.get('sender','API'),recipient=d.get('recipient'),message=d.get('message'),status='sent',cost=0.05)
    db.session.add(c);db.session.commit()
    return jsonify({'status':'sent','id':c.id})

# ========== BOOTSTRAP ==========
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        a=User(username='admin',email='admin@alrosy.com',role=Role.ADMIN)
        a.set_password('admin123');db.session.add(a)
        a2=User(username='agent1',email='agent@alrosy.com',role=Role.AGENT)
        a2.set_password('agent123');db.session.add(a2)
        c=User(username='client1',email='client@alrosy.com',role=Role.CLIENT)
        c.set_password('client123');db.session.add(c)
        db.session.commit()
    if not SMSRange.query.first():
        for r in[('USA','+1',1000,0.05),('UK','+44',500,0.08),('UAE','+971',300,0.10),('KSA','+966',200,0.12)]:
            db.session.add(SMSRange(name=r[0]+' Range',country=r[0],prefix=r[1],total_numbers=r[2],price=r[3]))
        db.session.commit()

if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
