from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
import os

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), unique=True, nullable=False)
    subtitle = db.Column(db.String(150))
    date = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(150))
    author = relationship("User", back_populates="posts")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":

        email = request.form["email"]
        user = User.query.filter_by(email=email).first()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        else:
            name = request.form["name"]
            password = generate_password_hash(
                request.form["password"],
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(name=name, email=email, password=password)

            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            return redirect(url_for('get_all_posts'))

    else:
        return render_template("register.html", form=RegisterForm())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("That email does not exist or the password is incorrect. Please try again.")
            return redirect(url_for('login'))

    else:
        return render_template("login.html", form=LoginForm())


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

# CRUD API
@app.route('/')
def get_all_posts():
    posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(
                text = comment_form.comment_text.data,
                comment_author = current_user,
                parent_post = requested_post
            )
            db.session.add(comment)
            db.session.commit()
        else:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route('/new-post', methods=["GET", "POST"])
@login_required
def create_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post_to_edit = BlogPost.query.get(post_id)
    if request.method == "POST":
        title = request.form["title"]
        subtitle = request.form["subtitle"]
        author = request.form["author"]
        body = request.form["body"]
        img_url = request.form["img_url"]

        post_to_edit.title = title
        post_to_edit.subtitle = subtitle
        post_to_edit.author = author
        post_to_edit.body = body
        post_to_edit.img_url = img_url

        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    else:
        edit_form = CreatePostForm(
            title=post_to_edit.title,
            subtitle=post_to_edit.subtitle,
            img_url=post_to_edit.img_url,
            author=post_to_edit.author,
            body=post_to_edit.body
        )
        return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
