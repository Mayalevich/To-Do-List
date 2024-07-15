from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from config import Config
from models import db, User, Todo
from forms import LoginForm, RegistrationForm, TodoForm
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from urllib.parse import urlparse

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
csrf = CSRFProtect(app)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('todo'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('todo')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    form = TodoForm()
    if form.validate_on_submit():
        todo = Todo(
            title=form.title.data,
            description=form.description.data,
            priority=form.priority.data,
            deadline=form.deadline.data,
            author=current_user
        )
        db.session.add(todo)
        db.session.commit()
        flash('Your task has been added.')
        return redirect(url_for('todo'))
    todos = current_user.todos.order_by(Todo.timestamp.desc()).all()
    return render_template('todo.html', title='Todo List', form=form, todos=todos)

@app.route('/edit/<int:todo_id>', methods=['GET', 'POST'])
@login_required
def edit(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        abort(403)
    form = TodoForm()
    if form.validate_on_submit():
        todo.title = form.title.data
        todo.description = form.description.data
        todo.priority = form.priority.data
        todo.deadline = form.deadline.data
        db.session.commit()
        flash('Your task has been updated.')
        return redirect(url_for('todo'))
    elif request.method == 'GET':
        form.title.data = todo.title
        form.description.data = todo.description
        form.priority.data = todo.priority
        form.deadline.data = todo.deadline
    return render_template('edit_todo.html', title='Edit Todo', form=form)

@app.route('/api/todos', methods=['GET'])
@login_required
def get_todos():
    todos = current_user.todos.order_by(Todo.timestamp.desc()).all()
    events = []
    for todo in todos:
        color = '#ff0000' if todo.priority == 'High' else '#ffcc00' if todo.priority == 'Medium' else '#00ff00'
        events.append({
            'title': todo.title,
            'start': todo.deadline.strftime('%Y-%m-%d'),
            'description': todo.description,
            'color': color
        })
    return jsonify(events)

@app.route('/delete/<int:todo_id>', methods=['POST'])
@login_required
def delete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        abort(403)
    db.session.delete(todo)
    db.session.commit()
    flash('Your task has been deleted.')
    return redirect(url_for('todo'))

if __name__ == '__main__':
    app.run(debug=True)
