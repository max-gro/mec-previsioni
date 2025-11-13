"""
Blueprint per autenticazione (Login/Logout)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import User
from forms import LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Max 5 tentativi di login al minuto
def login():
    """Pagina di login"""
    # Se già loggato, vai alla dashboard
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data) and user.active:
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Benvenuto {user.username}!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Username o password non validi, oppure account disattivato.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout utente"""
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('auth.login'))