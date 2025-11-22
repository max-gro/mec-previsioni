from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, FloatField, TextAreaField, SelectField, DateField, DateTimeField, IntegerField, BooleanField, EmailField
from wtforms.validators import Email, Length, EqualTo
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError
from models import User #, Componente
from datetime import date

def _anno_bounds():
    year = date.today().year
    return (1950, year + 1)  # es. 1950..(oggi+1)
    
    
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)], render_kw={'minlength': 3, 'maxlength': 80})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'minlength': 6})


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)], render_kw={'minlength': 3, 'maxlength': 80})
    email = EmailField('Email', validators=[DataRequired(), Email()], render_kw={'pattern': '[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$'})
    password = PasswordField('Password', validators=[Length(min=6)], render_kw={'minlength': 6})
    confirm_password = PasswordField('Conferma Password', validators=[EqualTo('password')], render_kw={'minlength': 6})
    role = SelectField('Ruolo', choices=[('user', 'Utente'), ('admin', 'Amministratore')])
    active = BooleanField('Attivo')
    
    def validate_username(self, username):
        if hasattr(self, 'user_id'):
            user = User.query.filter(User.username == username.data, User.id != self.user_id).first()
        else:
            user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username giÃ  utilizzato.')


# âœ… FORM PER FILE EXCEL ROTTURE (NUOVO)
class RotturaForm(FlaskForm):
    """Form per upload File Rottura Excel"""
    file = FileField('File Excel', validators=[
        FileRequired(message='Seleziona un file Excel'),
        FileAllowed(['xls', 'xlsx'], 'Solo file Excel (.xls, .xlsx) sono permessi!')
    ])
    anno = IntegerField('Anno', validators=[DataRequired()])
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        default=date.today,
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )

    note = TextAreaField('Note')


class RotturaEditForm(FlaskForm):
    """Form per modifica File Rottura (senza upload)"""
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    data_elaborazione = DateTimeField(
        'Data Elaborazione',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()],
        render_kw={'type': 'datetime-local'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ])
    note = TextAreaField('Note')


# ✅ FORM PER FILE ORDINI PDF (NUOVO SCHEMA)
class FileOrdineForm(FlaskForm):
    """Form per upload File Ordine PDF"""
    file = FileField('File PDF', validators=[
        FileRequired(message='Seleziona un file PDF'),
        FileAllowed(['pdf'], 'Solo file PDF sono permessi!')
    ])
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        default=date.today,
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ], default='Da processare')
    note = TextAreaField('Note')


class FileOrdineEditForm(FlaskForm):
    """Form per modifica File Ordine (senza upload file)"""
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    data_elaborazione = DateTimeField(
        'Data Elaborazione',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()],
        render_kw={'type': 'datetime-local'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ])
    note = TextAreaField('Note')


# ⚠️ DEPRECATO - Mantenuto per compatibilità legacy
class OrdineAcquistoForm(FlaskForm):
    """Form per upload Ordine di Acquisto (DEPRECATO - usa FileOrdineForm)"""
    file = FileField('File PDF', validators=[
        FileRequired(message='Seleziona un file PDF'),
        FileAllowed(['pdf'], 'Solo file PDF sono permessi!')
    ])
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        default=date.today,
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ])
    note = TextAreaField('Note')


class OrdineAcquistoEditForm(FlaskForm):
    """Form per modifica Ordine di Acquisto (DEPRECATO - usa FileOrdineEditForm)"""
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ])
    note = TextAreaField('Note')


class AnagraficaFileForm(FlaskForm):
    """Form per upload Anagrafica File Excel"""
    file = FileField('File Excel', validators=[
        FileRequired(message='Seleziona un file Excel'),
        FileAllowed(['xls', 'xlsx'], 'Solo file Excel (.xls, .xlsx) sono permessi!')
    ])
    marca = SelectField('Marca', validators=[DataRequired()])
    #anno = IntegerField('Anno', validators=[DataRequired()])
    minY, maxY = _anno_bounds()    
    anno = IntegerField(
        'Anno',
        validators=[DataRequired(), NumberRange(min=minY, max=maxY, message=f"Anno valido tra {minY} e {maxY}")],
        render_kw={"min": minY, "max": maxY, "placeholder": str(date.today().year)}
    )    
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        default=date.today,
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    note = TextAreaField('Note')

    def validate_anno(self, field):
        minY, maxY = _anno_bounds()
        if not (minY <= field.data <= maxY):
            raise ValidationError(f"L'anno deve essere tra {minY} e {maxY}.")


class AnagraficaFileEditForm(FlaskForm):
    """Form per modifica Anagrafica File (senza upload)"""
    #anno = IntegerField('Anno', validators=[DataRequired()])
    minY, maxY = _anno_bounds()
    anno = IntegerField(
        'Anno',
        validators=[DataRequired(), NumberRange(min=minY, max=maxY, message=f"Anno valido tra {minY} e {maxY}")],
        render_kw={"min": minY, "max": maxY}
    )
    data_acquisizione = DateField(
        'Data Acquisizione',
        format='%Y-%m-%d',
        validators=[DataRequired()],
        render_kw={'type': 'date'}
    )
    data_elaborazione = DateTimeField(
        'Data Elaborazione',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()],
        render_kw={'type': 'datetime-local'}
    )
    esito = SelectField('Esito', choices=[
        ('Da processare', 'Da processare'),
        ('Processato', 'Processato'),
        ('Errore', 'Errore')
    ])
    note = TextAreaField('Note')

    def validate_anno(self, field):
        minY, maxY = _anno_bounds()
        if not (minY <= field.data <= maxY):
            raise ValidationError(f"L'anno deve essere tra {minY} e {maxY}.")
            

class NuovaMarcaForm(FlaskForm):
    """Form per aggiungere una nuova marca"""
    nome_marca = StringField('Nome Marca', validators=[
        DataRequired(message='Il nome della marca Ã¨ obbligatorio'),
        Length(min=2, max=100, message='Il nome deve essere tra 2 e 100 caratteri')
    ])