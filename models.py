import datetime
from fastapi import HTTPException
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DECIMAL, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from constants import *
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    email = Column(String)
    role = Column(String)


    def check_password(self, password: str) -> bool:
        """
        Check if the password is correct.
        """
        return self.password == password

    def __str__(self):
        return self.username 
    
    __table_args__ = (
        CheckConstraint(role.in_([ROLE_PLAYER, ROLE_AUCTIONEER]), name='valid_role_values'),
    )
    
class Contest(Base):
    __tablename__ = 'contests'
    
    code = Column(String(4), primary_key = True)
    num_users = Column(Integer)
    pot_contribution = Column(DECIMAL(10,2))
    auctioneer_id = Column(Integer, ForeignKey('users.id'))
    users_left_to_join = Column(Integer)
    total_pot = Column(DECIMAL(10,2))
    auctioneer = relationship("User")

    __table_args__ = (
        CheckConstraint(num_users <= 11),
        CheckConstraint("LENGTH(code) = 4"),
    )

    def __str__(self):
        return self.code 

class ContestOverview(Base):
    __tablename__ = 'contests_overview'

    user_id = Column(Integer, ForeignKey('users.id'))
    contest_code = Column(String(4), ForeignKey('contests.code'))
    balance = Column(DECIMAL(10,2))
    coins = Column(Integer, default=0)
    players_taken = Column(Integer,default=0)

    contest = relationship("Contest")
    user = relationship("User")

    __table_args__ = (
        PrimaryKeyConstraint('contest_code', 'user_id', name='pk_contests_overview'),
        CheckConstraint(balance >= 0),
        CheckConstraint(players_taken <= 11)
    )

    def __str__(self):
        return "#".join(self.contest_code, self.user_id)  

class ContestBid(Base):
    __tablename__ = 'contests_bids'
    
    contest_code = Column(String(4), ForeignKey('contests.code'))
    user_id = Column(Integer, ForeignKey('users.id')) 
    player_id = Column(Integer, ForeignKey('players.id'))
    price_bought = Column(DECIMAL(10,2))
    points = Column(DECIMAL(10,2), default=0)
    is_traded_out = Column(Boolean, default=False)
    is_traded_in = Column(Boolean, default=False)
    player_role = Column(String(2))

    contest = relationship("Contest")
    user = relationship("User")
    player = relationship("Player") 

    __table_args__ = (
        PrimaryKeyConstraint('contest_code', 'user_id', 'player_id', name='pk_contests_bids'),
    )

    def __str__(self):
        return "#".join(self.contest_code,self.user_id, self.player_id)

class Auction(Base):
    __tablename__ = 'auctions'
    
    contest_code = Column(String(4), ForeignKey('contests.code'))
    player_id = Column(Integer, ForeignKey('players.id'))
    status = Column(String)
    bet_placed = Column(DECIMAL(10,2))
    bet_placing_user = Column(Integer, ForeignKey('users.id'))

    contest = relationship("Contest")
    player = relationship("Player")
    user = relationship("User")

    __table_args__ = (
        PrimaryKeyConstraint('contest_code', 'player_id', name='pk_auctions'),
        CheckConstraint(status.in_([STATUS_INQUEUE, STATUS_SOLD, STATUS_UNSOLD]), name='valid_status_values')
    )

    def __str__(self):
        return "#".join(self.contest_code, self.player_id)  

class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    country = Column(String) 
    role = Column(String)
    base_price = Column(DECIMAL(10,2))
    image_link = Column(String)
    points = Column(DECIMAL(10,2))

    def __str__(self):
        return self.name
    
class PlayerStat(Base):
    __tablename__ = 'players_stats'
    player_id = Column(Integer, ForeignKey('players.id'), primary_key=True)
    matches = Column(Integer)
    runs = Column(Integer)
    avg = Column(DECIMAL(3,2))
    hundreds = Column(Integer)
    wickets = Column(Integer)
    bowling_avg = Column(DECIMAL(3,2))
    economy = Column(DECIMAL(3,2))
    ranking = Column(Integer)

    player = relationship("Player")

    def __str__(self):
        return self.player.name

class UserTotal(Base):
    __tablename__ = 'user_totals'

    id = Column(Integer, primary_key=True, index=True)  # Consider using 'id' as the primary key
    contest_code = Column(String(4), ForeignKey('contests.code'))
    user_id_points = Column(Integer, ForeignKey('users.id'))
    total_points_user = Column(DECIMAL(5, 2))

    def __str__(self):
        return f"UserTotal(user_id={self.user_id_points}, user_points={self.total_points_user})"
    

class AuctionQueue(Base):
    __tablename__ = 'auction_queues'
    
    id = Column(Integer, primary_key=True)
    contest_code = Column(String) 
    player_id = Column(Integer, ForeignKey('players.id'))
    auction_order = Column(Integer)
    status = Column(String)
    player = relationship("Player")
    
    def __str__(self):
        return self.contest_code

    __table_args__ = (
        CheckConstraint(status.in_([STATUS_INQUEUE, STATUS_SOLD, STATUS_UNSOLD]), name='valid_status_values'),
    )

class TradingWindowStatus(Base):
    __tablename__ = 'trading_window_statuss'

    id = Column(Integer, primary_key=True)
    contest_code = Column(String(4), ForeignKey('contests.code'))
    is_trading_window_over = Column(Boolean, default=True)

    def __str__(self):
        return f"TradingWindowStatus(contest_code={self.contest_code}, is_trading_window_over={self.is_trading_window_over})"

class PlayerTradedOutCount(Base):
    __tablename__ = 'player_traded_out_counts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    traded_out_count = Column(Integer, default=0)

    def __str__(self):
        return f"PlayerTradedOutCount(user_id={self.user_id}, traded_out_count={self.traded_out_count})"

class TradeWindow(Base):
    __tablename__ = "trade_windows"

    id = Column(Integer, primary_key=True)    
    contest_code = Column(String(4), ForeignKey('contests.code'))
    player_id = player_id = Column(Integer, ForeignKey('players.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    bid_coins = Column(Integer)

    def __str__(self):
        return f"TradeWindow(contest_code={self.contest_code}, user_id={self.user_id})"