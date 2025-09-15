from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --------------- Database Configuration ---------------
# SQLite database ka file todo.db banayega
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------- Model Definition ---------------
# Ek simple Todo model with id, content, date_created
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)         # unique ID
    content = db.Column(db.String(200), nullable=False)   # task ka text
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.id}>'

# --------------- Routes ---------------

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Form se jo task aaya, use get karen
        task_content = request.form['content']
        if task_content.strip() == '':
            # Agar empty input hai to wapis index par redirect karen
            return redirect(url_for('index'))

        # Naya Todo object create karen
        new_task = Todo(content=task_content)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            # Agar DB mein koi error ho jaye
            return f'An error occurred while adding the task: {e}'

    else:
        # GET request: sara tasks database se fetch karen, order by date_created
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks)


@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return f'An error occurred while deleting the task: {e}'


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    task = Todo.query.get_or_404(id)

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
