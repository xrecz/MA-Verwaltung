from flask import Flask, render_template, flash, redirect
from config import config
from login import LoginForm

app = Flask(__name__)
app.config.from_object(config)

@app.route('/')
def index():
    return "Willkommen"
@app.route('/login', methods=['GET', 'POST'])
def login():  # put application's code here
    #render_template() wird als Methode zum auslagern benutzt und verweist auf die Daten im templates ordner
    form = LoginForm()
    if form.validate_on_submit():
        flash("Logged in successfully".format(form.username.data))
        return redirect("/")
    return render_template("test.html", title="Login", form=form)


if __name__ == '__main__':
    app.run()
