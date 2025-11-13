"""
Blueprint per la gestione utenti (CRUD) - Solo Admin
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, User
from forms import UserForm
from utils.decorators import admin_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@admin_required
def list():
    """Lista tutti gli utenti"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users/list.html', users=users)

@users_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Crea un nuovo utente"""
    form = UserForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            active=form.active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Utente {user.username} creato!', 'success')
        return redirect(url_for('users.list'))
    
    return render_template('users/create.html', form=form)

@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un utente esistente"""
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    form.user_id = user.id  # Per validazione username univoco
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.active = form.active.data
        
        # Aggiorna password solo se fornita
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        flash(f'Utente {user.username} aggiornato!', 'success')
        return redirect(url_for('users.list'))
    
    return render_template('users/edit.html', form=form, user=user)

@users_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Elimina un utente"""
    user = User.query.get_or_404(id)
    
    # Non permettere eliminazione ultimo admin
    if user.is_admin() and User.query.filter_by(role='admin').count() == 1:
        flash('Non puoi eliminare l\'ultimo amministratore!', 'danger')
        return redirect(url_for('users.list'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Utente {username} eliminato.', 'info')
    return redirect(url_for('users.list'))