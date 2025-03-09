from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import Auction, Bid
from database import db

auction = Blueprint('auction', __name__)

@auction.route('/')
def index():
    auctions = Auction.query.filter(Auction.end_time > db.func.now()).all()
    return render_template('index.html', auctions=auctions)

@auction.route('/auction/<int:auction_id>')
def auction_details(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    return render_template('auction.html', auction=auction)

@auction.route('/place_bid/<int:auction_id>', methods=['POST'])
@login_required
def place_bid(auction_id):
    bid_amount = float(request.form['bid_amount'])
    auction = Auction.query.get_or_404(auction_id)

    if bid_amount > (auction.current_bid or auction.starting_bid):
        auction.current_bid = bid_amount
        new_bid = Bid(auction_id=auction_id, bidder_id=current_user.id, bid_amount=bid_amount)
        db.session.add(new_bid)
        db.session.commit()
    else:
        flash('Bid must be higher than the current bid')

    return redirect(url_for('auction.auction_details', auction_id=auction_id))
