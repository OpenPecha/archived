from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired


class PechaSecretKeyForm(FlaskForm):
    secret_key = PasswordField("Pecha Secret Key", validators=[DataRequired()])
    submit = SubmitField("Submit")
