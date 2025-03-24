import os
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from sqlalchemy import func

from .forms import RegisterForm, LoginForm, AuctionForm
from .models import db, User, AuditLog, Auction, Bid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from flask import jsonify

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Latest 3 approved auctions
    recommended_auctions = Auction.query.filter_by(status='approved').order_by(Auction.created_at.desc()).limit(3).all()

    # Top 3 sellers by number of auctions
    top_sellers = (
        db.session.query(User, func.count(Auction.id).label("auction_count"))
        .join(Auction, Auction.seller_id == User.id)
        .filter(User.role == 'seller')
        .group_by(User.id)
        .order_by(func.count(Auction.id).desc())
        .limit(3)
        .all()
    )

    # Active auctions (not expired)
    now = datetime.utcnow()
    available_auctions = Auction.query.filter(
        Auction.status == 'approved',
        Auction.deadline > now
    ).order_by(Auction.deadline.asc()).limit(5).all()

    return render_template('index.html',
                           recommended_auctions=recommended_auctions,
                           top_sellers=top_sellers,
                           available_auctions=available_auctions,
                           now=now)

@main.route('/auction')
def auction():
    return render_template('auction.html')

@main.route('/place_bid', methods=['POST'])
def place_bid():
    # Later: Save bid to DB
    return "<h3>Bid placed! (Mock)</h3>"

@main.route('/international')
def international():
    return render_template('international.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.name}!', 'success')

            # Role-based redirect
            return redirect(url_for(f'main.dashboard_{user.role}'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

@main.route('/contact')
def contact():
    return render_template('contact.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('main.register'))

        hashed_pw = generate_password_hash(form.password.data)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_pw,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)

@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return render_template('dashboards/dashboard_admin.html', name=current_user.name)
    elif current_user.role == 'seller':
        return render_template('dashboards/dashboard_seller.html', name=current_user.name)
    else:
        return render_template('dashboards/dashboard_buyer.html', name=current_user.name)

@main.route('/dashboard/admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.login'))
    return render_template('dashboards/dashboard_admin.html', name=current_user.name)


@main.route('/dashboard/seller')
@login_required
def dashboard_seller():
    if current_user.role != 'seller':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    auctions = Auction.query.filter_by(seller_id=current_user.id).order_by(Auction.created_at.desc()).all()
    return render_template('dashboards/dashboard_seller.html', name=current_user.name, auctions=auctions)


@main.route('/dashboard/buyer')
@login_required
def dashboard_buyer():
    if current_user.role != 'buyer':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    auctions = Auction.query.filter_by(status='approved').order_by(Auction.created_at.desc()).all()
    return render_template('dashboards/dashboard_buyer.html', name=current_user.name, auctions=auctions)

@main.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    query = User.query
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    users = query.paginate(page=page, per_page=10)
    return render_template('dashboards/admin_users.html', users=users, search=search)

def log_admin_action(admin_id, action):
    log = AuditLog(admin_id=admin_id, action=action)
    db.session.add(log)
    db.session.commit()

@main.route('/admin/users/promote/<int:user_id>', methods=['POST'])
@login_required
def promote_user(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    user = User.query.get(user_id)
    if user:
        old_role = user.role
        user.role = 'seller' if user.role == 'buyer' else 'admin'
        db.session.commit()

        log_admin_action(current_user.id, f"Promoted user '{user.name}' (ID: {user.id}) from {old_role} to {user.role}")
        flash(f"{user.name} has been promoted to {user.role}.", "success")

    return redirect(url_for('main.manage_users'))

@main.route('/admin/users/demote/<int:user_id>', methods=['POST'])
@login_required
def demote_user(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    user = User.query.get(user_id)
    if user:
        old_role = user.role
        user.role = 'buyer'
        db.session.commit()

        log_admin_action(current_user.id, f"Demoted user '{user.name}' (ID: {user.id}) from {old_role} to buyer")
        flash(f"{user.name} has been demoted to Buyer.", "warning")

    return redirect(url_for('main.manage_users'))

@main.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    user = User.query.get(user_id)
    if user:
        log_admin_action(current_user.id, f"Deleted user '{user.name}' (ID: {user.id}) with role {user.role}")
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.name} has been deleted.", "danger")

    return redirect(url_for('main.manage_users'))

@main.route('/admin/audit-logs')
@login_required
def view_audit_logs():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=10)

    return render_template('dashboards/admin_audit_logs.html', logs=logs)

@main.route('/admin/auctions')
@login_required
def manage_auctions():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')

    query = Auction.query

    if search:
        query = query.filter(Auction.title.ilike(f'%{search}%'))

    if status:
        query = query.filter_by(status=status)

    auctions = query.order_by(Auction.created_at.desc()).paginate(page=page, per_page=10)

    return render_template('dashboards/admin_auctions.html', auctions=auctions, search=search, status=status)

@main.route('/admin/auction/approve/<int:auction_id>', methods=['POST'])
@login_required
def approve_auction(auction_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    auction = Auction.query.get(auction_id)
    if auction:
        auction.status = 'approved'
        db.session.commit()

        log_admin_action(current_user.id, f"Approved auction '{auction.title}' (ID: {auction.id}) by seller ID {auction.seller_id}")
        flash(f"Auction '{auction.title}' approved.", 'success')

    return redirect(url_for('main.manage_auctions'))

@main.route('/admin/auction/reject/<int:auction_id>', methods=['POST'])
@login_required
def reject_auction(auction_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    auction = Auction.query.get(auction_id)
    if auction:
        auction.status = 'rejected'
        db.session.commit()

        log_admin_action(current_user.id, f"Rejected auction '{auction.title}' (ID: {auction.id}) by seller ID {auction.seller_id}")
        flash(f"Auction '{auction.title}' rejected.", 'warning')

    return redirect(url_for('main.manage_auctions'))

@main.route('/admin/auction/delete/<int:auction_id>', methods=['POST'])
@login_required
def delete_auction(auction_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    auction = Auction.query.get(auction_id)
    if auction:
        log_admin_action(current_user.id, f"Deleted auction '{auction.title}' (ID: {auction.id}) by seller ID {auction.seller_id}")
        db.session.delete(auction)
        db.session.commit()

        flash(f"Auction '{auction.title}' deleted.", 'danger')

    return redirect(url_for('main.manage_auctions'))

@main.route('/create_auction')
def create_auction():
    return render_template('dashboards/create_auction.html')

@main.route('/auction/new', methods=['GET', 'POST'])
@login_required
def post_coconut_lot():
    if current_user.role != 'seller':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    form = AuctionForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(f"{uuid.uuid4().hex}_{form.image.data.filename}")
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        auction = Auction(
            title=form.title.data,
            description=form.description.data,
            starting_price=form.starting_price.data,
            seller_id=current_user.id,
            image=filename,
            deadline=form.deadline.data  # 🆕 Save deadline here
        )
        db.session.add(auction)
        db.session.commit()
        flash("Auction lot posted successfully!", "success")
        return redirect(url_for('main.dashboard_seller'))

    return render_template('auctions/auction_form.html', form=form, title="Post Coconut Lot")

@main.route('/auction/edit/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def edit_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    if auction.seller_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('main.dashboard_seller'))

    form = AuctionForm(obj=auction)

    if form.validate_on_submit():
        auction.title = form.title.data
        auction.description = form.description.data
        auction.starting_price = form.starting_price.data
        auction.deadline = form.deadline.data  # 🆕 Save updated deadline

        if form.image.data:
            filename = secure_filename(f"{uuid.uuid4().hex}_{form.image.data.filename}")
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            auction.image = filename

        db.session.commit()
        flash("Auction updated successfully!", "success")
        return redirect(url_for('main.dashboard_seller'))

    return render_template('auctions/auction_form.html', form=form, title="Edit Coconut Lot")

@main.route('/auction/delete/<int:auction_id>', methods=['POST'])
@login_required
def delete_own_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    if auction.seller_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('main.dashboard_seller'))

    db.session.delete(auction)
    db.session.commit()
    flash("Auction deleted.", "danger")
    return redirect(url_for('main.dashboard_seller'))

class BidForm(FlaskForm):
    amount = DecimalField('Your Bid ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Place Bid')

@main.route('/auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def view_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    form = BidForm()
    is_expired = auction.deadline and datetime.utcnow() > auction.deadline
    highest_bid = db.session.query(db.func.max(Bid.amount)).filter_by(auction_id=auction_id).scalar() or auction.starting_price

    if form.validate_on_submit():
        if is_expired:
            flash("Bidding has ended for this auction.", "warning")
            return redirect(url_for('main.view_auction', auction_id=auction_id))

    if form.validate_on_submit():
        if current_user.role != 'buyer':
            flash("Only buyers can place bids.", "danger")
            return redirect(url_for('main.login'))

        if form.amount.data <= highest_bid:
            flash(f"Your bid must be higher than the current bid (${highest_bid:.2f}).", "warning")
        else:
            bid = Bid(auction_id=auction_id, buyer_id=current_user.id, amount=form.amount.data)
            db.session.add(bid)
            db.session.commit()
            flash("Your bid was placed successfully!", "success")
            return redirect(url_for('main.view_auction', auction_id=auction_id))

    return render_template('auctions/view_auction.html', auction=auction, form=form, highest_bid=highest_bid, is_expired=is_expired)

@main.route('/buyer/bids')
@login_required
def my_bids():
    if current_user.role != 'buyer':
        flash("Access denied.", "danger")
        return redirect(url_for('main.login'))

    bids = Bid.query.filter_by(buyer_id=current_user.id).order_by(Bid.timestamp.desc()).all()
    return render_template('dashboards/buyer_bids.html', bids=bids)

@main.route('/auction/<int:auction_id>/highest-bid')
def get_highest_bid(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    highest_bid = db.session.query(db.func.max(Bid.amount)).filter_by(auction_id=auction_id).scalar() or auction.starting_price
    return jsonify({'highest_bid': f"{highest_bid:.2f}"})