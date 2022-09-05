from flask import Flask, render_template, redirect, url_for, flash, request,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm1,CommentForm
from flask_gravatar import Gravatar
from functools import wraps



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager=LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

db = SQLAlchemy(app)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

# db.create_all()
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if current_user.id!=1:
                return abort(403)
        except AttributeError:
            return abort(403)
        else:

            return f(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# admin_id=""
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, Logged_in=current_user.is_authenticated)

    #
    #
    # return render_template("index.html", all_posts=posts, Logged_in=current_user.is_authenticated, adminid=admin_id)


@app.route('/register', methods=["POST","GET"])
def register():
    register_form=RegisterForm()
    if register_form.validate_on_submit():
        if User.query.filter_by(email=register_form.email.data).first():
            flash("Email already registered login with that email")
            # return redirect(url_for("login"))
        else:

            new_user=User(
            email=register_form.email.data,
            password=generate_password_hash(register_form.password.data,method="pbkdf2:sha256",salt_length=8),
            name=register_form.name.data
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form1=register_form)


@app.route('/login', methods=["POST","GET"])
def login():
    # global admin_id
    login_form=LoginForm1()
    if login_form.validate_on_submit():
        user=User.query.filter_by(email=login_form.email.data).first()
        if user:
            if check_password_hash(user.password,login_form.password.data):
                # if user.id == 1:
                #     admin_id = True
                # else:
                #     admin_id = False
                login_user(user)
                return render_template("/index.html", user_logged=current_user.name, Logged_in=True)
                #
                # return render_template("/index.html", user_logged=current_user.name, Logged_in=True,
                #                        adminid=admin_id)

                # return redirect(url_for("logged"))
            else:
                flash("Password is wrong")

        if not user:
            flash("Email not exist")

    return render_template("login.html",form2=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["POST",'GET'])

def show_post(post_id):
    comment_form=CommentForm()
    if not current_user.is_authenticated:
        flash("first login")
        return redirect(url_for("login"))
    if comment_form.validate_on_submit():
        new_comment=Comment(
            post_id=post_id,
            author_id=current_user.id,
            text=comment_form.comment.data
        )
        db.session.add(new_comment)
        db.session.commit()
    requested_post = BlogPost.query.get(post_id)
    text_comment=db.session.query(Comment).all()

    return render_template("post.html", post=requested_post,form=comment_form,data_comment=text_comment, Logged_in=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html",Logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html",Logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["POST","GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            # author=current_user.name,

            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,Logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["POST","GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = current_user.name
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,Logged_in=current_user.is_authenticated )


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

# @app.route('/logged')
# @login_required
# def logged():
#     return render_template("/index.html",user_logged=current_user.name, Logged_in=True, admin_id=current_user.id)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)
