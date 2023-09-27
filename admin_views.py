from models import *
from sqladmin import  ModelView

class UserAdmin(ModelView, model=User):
    column_list = User.__table__.columns.keys()


class ContestAdmin(ModelView, model=Contest):
    column_list = Contest.__table__.columns.keys()
    pk_columns = ["code"]
    defaults=[str(pk) for pk in pk_columns]


class ContestOverviewAdmin(ModelView, model=ContestOverview):
    column_list = ContestOverview.__table__.columns.keys()
    pk_columns = ["user_id", "contest_code"]
    defaults=[str(pk) for pk in pk_columns],


class ContestBidAdmin(ModelView, model=ContestBid):
    column_list = ContestBid.__table__.columns.keys()
    pk_columns = [ "contest_code", "user_id", "player_id"]
    defaults=[str(pk) for pk in pk_columns],


class AuctionAdmin(ModelView, model=Auction):
    column_list = Auction.__table__.columns.keys()
    pk_columns = ["contest_code", "player_id"]
    defaults=[str(pk) for pk in pk_columns],


class PlayerAdmin(ModelView, model=Player):
    column_list = Player.__table__.columns.keys()


class PlayerStatAdmin(ModelView, model=PlayerStat):
    column_list = PlayerStat.__table__.columns.keys()
    pk_columns = ["player_id"]
    defaults=[str(pk) for pk in pk_columns],

class UserTotalAdmin(ModelView, model=UserTotal):
    column_list = UserTotal.__table__.columns.keys()

class AuctionQueueAdmin(ModelView, model = AuctionQueue):
    column_list = AuctionQueue.__table__.columns.keys()

class TradingWindowStatusAdmin(ModelView, model=TradingWindowStatus):
    column_list = TradingWindowStatus.__table__.columns.keys()

class PlayerTradedOutCountAdmin(ModelView, model=PlayerTradedOutCount):
    column_list = PlayerTradedOutCount.__table__.columns.keys()

class TradeWindowAdmin(ModelView, model=TradeWindow):
    column_list = TradeWindow.__table__.columns.keys()