from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# --------------- Database Configuration ---------------
# SQLite database ka file todo.db banayega
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

db = SQLAlchemy(app)

# --------------- Login Manager Configuration ---------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------- Model Definition ---------------

# User model for authentication
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    todos = db.relationship('Todo', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Ek simple Todo model with id, content, date_created
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)         # unique ID
    content = db.Column(db.String(200), nullable=False)   # task ka text
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.id}>'

# --------------- Routes ---------------

# --------------- Authentication Routes ---------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists.', 'error')
            else:
                flash('Email already registered.', 'error')
            return render_template('signup.html')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username_or_email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username/email or password.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# --------------- Todo Routes ---------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Form se jo task aaya, use get karen
        task_content = request.form['content']
        if task_content.strip() == '':
            # Agar empty input hai to wapis index par redirect karen
            return redirect(url_for('index'))

        # Naya Todo object create karen with user_id
        new_task = Todo(content=task_content, user_id=current_user.id)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            # Agar DB mein koi error ho jaye
            return f'An error occurred while adding the task: {e}'

    else:
        # GET request: current user ke tasks database se fetch karen, order by date_created
        tasks = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks)


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)
    # Check if task belongs to current user
    if task_to_delete.user_id != current_user.id:
        flash('You do not have permission to delete this task.', 'error')
        return redirect(url_for('index'))
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return f'An error occurred while deleting the task: {e}'


@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    task = Todo.query.get_or_404(id)
    
    # Check if task belongs to current user
    if task.user_id != current_user.id:
        flash('You do not have permission to update this task.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_content = request.form['content']
        if new_content.strip() == '':
            return redirect(url_for('index'))

        try:
            task.content = new_content
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            return f'An error occurred while updating the task: {e}'
    else:
        # GET request par update page dikhayen
        return render_template('index.html', task=task)

# --------------- App Run ---------------
if __name__ == "__main__":
    # Agar pehli baar hai to database create karen
    with app.app_context():
        db.create_all()
    # Debug mode on rakh sakte hain during development
    app.run(debug=True)
