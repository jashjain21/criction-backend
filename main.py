import os
from fastapi import FastAPI, File, HTTPException, Response, UploadFile, Depends, status
import jwt
import pandas as pd
from database import get_db, engine
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqladmin import Admin, ModelView
from sqlalchemy.orm import sessionmaker
from sqlalchemy import asc, func
import csv 
import io
# import jwt 
import dateparser
import random, string
from models import *
from constants import *
from admin_views import *
import logging
import decimal
from decimal import Decimal
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

secret_key = "SECRET_KEY"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
unsold_players_dict = {} #dict for mapping the list of unsold players to a particular contest code

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") # used for the login and signup endpoints

app = FastAPI()

origins = [
    "http://localhost:5173",  # Add the origin of your frontend
    # Add more origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
admin = Admin(app, engine)
admin.add_view(UserAdmin)
admin.add_view(ContestAdmin)
admin.add_view(ContestOverviewAdmin)
admin.add_view(ContestBidAdmin)
admin.add_view(AuctionAdmin)
admin.add_view(PlayerAdmin)
admin.add_view(PlayerStatAdmin)
admin.add_view(UserTotalAdmin)
admin.add_view(AuctionQueueAdmin)
admin.add_view(TradingWindowStatusAdmin)
admin.add_view(PlayerTradedOutCountAdmin)
admin.add_view(TradeWindowAdmin)

@app.post("/playerDetailsmanjasdevmoh")
async def add_player_details(player_file: UploadFile = File(...), 
    stats_file: UploadFile = File(...),
    db: Session = Depends(get_db)
    ):
    """
    Add a CSV file to the database.
    """
    df = pd.read_csv(player_file.file, encoding='utf-8')
    stats_df = pd.read_csv(stats_file.file, encoding='utf-8')
    
    for row in df.itertuples():

        player = Player(
            name=row[1],
            country=row[2], 
            role=row[3],
            base_price=row[4],
            image_link=row[5],
            points=row[6]
        )

        db.add(player)
        db.flush()

        stats = stats_df.iloc[row.Index]

        player_stat = PlayerStat(

        player_id=player.id,

        matches=int(stats['Matches']),
        runs=int(stats['Runs']),
        avg=decimal.Decimal(stats['Avg']), 
        hundreds=int(stats['Hundreds']),

        wickets=int(stats['Wickets']),
        bowling_avg=decimal.Decimal(stats['BowlAvg']),
        economy=decimal.Decimal(stats['Economy']),

        ranking=int(stats['Rankings'])

        )  

        db.add(player_stat)
        
    db.commit()
    
    return {"message": "Player details added successfully"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm=Depends(),db: Session = Depends(get_db)):
    """
    Login a user.
    """
    username = form_data.username
    password = form_data.password
    

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not user.check_password(password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Create a JWT token for the user.
    token = create_access_token(user.id)

    return {"access_token": token}


'''
{
"username":"abc",
"password":"abc", 
"email":"abc",
"role":"player"
}
'''
@app.post("/signup")
async def signup(data: dict, db: Session = Depends(get_db)):
    """
    Signup a new user.
    """
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    # Check if the username or email already exists.
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create the new user.
    user = User(username=username, email=email, password=password, role = role)
    db.add(user)
    db.commit()

    return {"message": "User created successfully"}


def get_current_user(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    """
    Get the currently logged in user.
    """

    # Get the user ID from the token.
    user_id = jwt.decode(token, secret_key, algorithms=["HS256"])["sub"]
    print("Helllo ,", user_id)
    # Get the user from the database.
    user = db.query(User).filter(User.id == user_id).first()

    # Return the user if it exists.
    if user:
        return user
    # Return None if the user does not exist.
    return None

@app.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    print(current_user)
    """
    Get the currently logged in user.
    """
    return {"username": current_user.username, "role": current_user.role,"id": current_user.id}

def create_access_token(id: str):
    """
    Create a JWT token for the user.
    """

    # Create a JWT token
    token = jwt.encode({"sub": id}, secret_key, algorithm="HS256")

    return token


'''
{
"num_users":"10",
"pot_contribution":"100"
}
'''
@app.post("/createContest",response_model=None )
async def createContest(data:dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    num_users=int(data.get("num_users"))
    pot_contribution=int(data.get("pot_contribution"))

    if not current_user:
        raise HTTPException(status_code=401, detail="User not logged in")
    if current_user.role == ROLE_AUCTIONEER:
        raise HTTPException(status_code=404, detail="Auctioneer not allowed to create contest")  
    else:
        contest_code = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
        contest = Contest(
            code=contest_code,
            num_users= num_users,
            pot_contribution = pot_contribution,
            total_pot = pot_contribution,
            users_left_to_join = num_users-1,
        )
        db.add(contest)
        contest_overview = ContestOverview(
            user_id = current_user.id,
            contest_code = contest_code,
            balance = 100,
            coins = 1000,
        )
        db.add(contest_overview)
        players = db.query(Player).all()

        for player in players:
            auction = Auction(contest_code=contest_code, player_id=player.id, status = STATUS_INQUEUE)
            db.add(auction)

        player_ids = [player.id for player in players]

        # randomize or define auction order
        random.shuffle(player_ids) 

        for i, player in enumerate(player_ids):
            auction_queue = AuctionQueue(
            contest_code=contest_code,
            player_id=player, 
            auction_order=i,
            status = STATUS_INQUEUE
            )
            db.add(auction_queue)
       
        db.commit()
        return {"code": contest_code}
    
@app.post("/joincontest")
async def joinContest(data:dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    contest_code=data.get("contest_code")
    
    if current_user:
        if current_user.role == ROLE_AUCTIONEER:
            contest = db.query(Contest).filter(Contest.code == contest_code).first()
            if not contest:
                raise HTTPException(status_code=404, detail="Contest not found")  
            if contest.auctioneer_id:
                raise HTTPException(status_code=400, detail="Auctioneer already exists")
            
            contest.auctioneer_id = current_user.id
            db.commit()
            return {'success': 'You have successfully been set the auctioneer'}
        else:
            contest = db.query(Contest).filter(Contest.code == contest_code).first()
            if not contest:
                raise HTTPException(status_code=404, detail="Contest not found")  
            
            if not contest.users_left_to_join:
                raise HTTPException(status_code=400, detail="Contest is full")        

            contest_overview = ContestOverview(
                user_id = current_user.id,
                contest_code = contest_code,
                balance = 100,
                coins = 1000,
            )
            db.add(contest_overview)
            contest.users_left_to_join -= 1
            contest.total_pot += contest.pot_contribution
            db.commit()
            return {'success': 'You have successfully joined the contest'}
    else:
       raise HTTPException(status_code=401, detail="User not logged in")
    
@app.get("/contest/{contest_code}/usernames")
async def get_usernames_for_contest(contest_code: str, db: Session = Depends(get_db)):
    """
    Get the usernames of users who have joined a specific contest.
    """
    
    
    user_data = (
    db.query(User.id, User.username)
    .join(ContestOverview)
    .filter(ContestOverview.contest_code == contest_code)
    .all()
    )

    usernames_and_ids = [{"id": user[0], "username": user[1]} for user in user_data]

    return {"usernames_and_ids": usernames_and_ids}

@app.get("/getPlayersAuction")
async def getPlayersAuction(contest_code:str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != ROLE_AUCTIONEER:
        raise HTTPException(status_code=404, detail="Auctioneer not found")
    #  Return list of players and users
    contestOverviewList = db.query(ContestOverview).filter(ContestOverview.contest_code == contest_code).all()
    if not contestOverviewList:
        raise HTTPException(status_code=404, detail="Contes code not found") 
    user_data = [
            {"user_id": overview.user_id, "user_name": overview.user.username}
            for overview in contestOverviewList
        ]
    
    auction_queue = db.query(AuctionQueue).filter(AuctionQueue.contest_code == contest_code).all()

    player_data = []
    for auction in auction_queue:
            player_id = auction.player_id

            # Query the Player table to get general player details
            player_info = (
                db.query(Player)
                .filter(Player.id == player_id)
                .first()
            )

            # Query the PlayerStat table to get player statistics
            player_stats = (
                db.query(PlayerStat)
                .filter(PlayerStat.player_id == player_id)
                .first()
            )

            if player_info and player_stats:
                player_data.append({
                    "player_info": {
                        "player_id":player_id,
                        "name": player_info.name,
                        "country": player_info.country,
                        "role": player_info.role,
                        "base_price": float(player_info.base_price),
                        "image_link": player_info.image_link,
                        "points": float(player_info.points),
                    },
                    "player_stats": {
                        "matches": player_stats.matches,
                        "runs": player_stats.runs,
                        "avg": float(player_stats.avg),
                        "hundreds": player_stats.hundreds,
                        "wickets": player_stats.wickets,
                        "bowling_avg": float(player_stats.bowling_avg),
                        "economy": float(player_stats.economy),
                        "ranking": player_stats.ranking,
                    },
                })
    
    return {
            "user_data": user_data,
            "player_data": player_data,
        }
'''
{
"status":"sold",
"contest_code":"gLPz",
"player_id":"10",
"user_id":"1",
"bet_placed":"10"
}

OR 

{
"status":"unsold",
"contest_code":"gLPz",
"player_id":"11"
}
'''
@app.post("/assignPlayer")
async def assignPlayer(data:dict, db: Session = Depends(get_db)):
    #  fill auction and contest bid
    # then in contest overview put balance and reduce players taken

    status = data.get("status")
    contest_code=data.get("contest_code")
    player_id=data.get("player_id")
    
    auction = db.query(Auction).filter(Auction.contest_code == contest_code, Auction.player_id == player_id).first()
    auction_queue = db.query(AuctionQueue).filter(AuctionQueue.contest_code == contest_code, AuctionQueue.player_id == player_id).first()
    
    if auction.status != STATUS_INQUEUE:
        raise HTTPException(status_code=404, detail="Player already sold")
    
    if not auction:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if status == STATUS_UNSOLD:
        auction.status = STATUS_UNSOLD
        auction_queue.status = STATUS_UNSOLD
        db.commit()
        return {'success': 'Player has been added to unsold list'}

    user_id=int(data.get("user_id"))
    bet_placed=int(data.get("bet_placed"))
    contestOverview = db.query(ContestOverview).filter(ContestOverview.user_id == user_id, ContestOverview.contest_code == contest_code).first()  
    
    if not contestOverview:
        raise HTTPException(status_code=404, detail="User not found")
    
    if float(contestOverview.balance) - bet_placed < 0:
        raise HTTPException(status_code=404, detail="You don't have sufficient funds to place this bet.")
    
    if contestOverview.players_taken == 11:
        raise HTTPException(status_code=404, detail="You have taken all your players.")
    
    
    
    # Convert the float to a Decimal
    bet_placed_decimal = decimal.Decimal(str(bet_placed))

    # Assign the Decimal value to your SQLAlchemy model attribute
    auction.bet_placed = bet_placed_decimal

    auction.status = STATUS_SOLD
    auction_queue.status  = STATUS_SOLD
    auction.bet_placed = bet_placed
    auction.bet_placing_user = user_id

    contestOverview.balance -= bet_placed_decimal
    contestOverview.players_taken += 1

    contestBid = ContestBid(contest_code = contest_code, 
                            user_id = user_id,
                            player_id = player_id,
                            price_bought = bet_placed,
                            is_traded_in = True
                            )
    db.add(contestBid)
    db.commit()
    return {'success': 'Player has been sold'}


# # player_file: UploadFile = File(...), 
#     stats_file: UploadFile = File(...),
#     db: Session = Depends(get_db)
#     ):
#     """
#     Add a CSV file to the database.
#     """
#     df = pd.read_csv(player_file.file, encoding='utf-8')
@app.post("/updatePointsmanjasdevmoh")
async def updatePoints(player_file: UploadFile = File(...),db: Session = Depends(get_db)):

    df = pd.read_csv(player_file.file, encoding='utf-8')
    for index, row in df.iterrows():
        player_name = row['Name'] 
        points = row['Points']
        players = db.query(Player).filter(Player.name == player_name).first()
            # Find the player by name and update their points
        players.points = points
    
        # Commit the changes to the player table
    db.commit()

        # Update points for players in the contestbid table
    for user_id in db.query(ContestBid.user_id).distinct():
        user_id = user_id[0]
        for player in db.query(ContestBid).filter(ContestBid.user_id == user_id, ContestBid.is_traded_in == True):
            player_id = player.player_id
            player_contestbid = db.query(ContestBid).filter(ContestBid.user_id == user_id, ContestBid.player_id == player_id).first()
            points = db.query(Player.points).filter(Player.id == player_id).scalar()
            
            points = decimal.Decimal(points)
            # Apply multipliers for specific player roles
            if db.query(ContestBid.player_role).filter(ContestBid.player_id == player_id).scalar() == 'CA':
                player_contestbid.points += 2 * points
            elif db.query(ContestBid.player_role).filter(ContestBid.player_id == player_id).scalar() == 'VC':
                player_contestbid.points += decimal.Decimal(1.5) * points
            else:
                player_contestbid.points += points

        # Commit the changes to the contestbid table
    db.commit()

    db.close()

    return {"message": "Points updated successfully"}

@app.post("/userTotalPoints")
async def userTotalPoints(contest_code: str, db: Session = Depends(get_db)):
    # Get a list of distinct user_ids from the ContestBid table
    user_ids = db.query(ContestBid.user_id).distinct().all()

    # Iterate through user_ids and calculate total points for each user
    for user_id in user_ids:
        user_id = user_id[0]  # Extract the user_id value from the tuple

        # Calculate total points for the user by summing up points from contestbid entries
        total_points = (
            db.query(func.sum(ContestBid.points))
            .filter(ContestBid.user_id == user_id)
            .scalar()
        )

        # Create or update the UserTotal entry for this user
        user_total = (
            db.query(UserTotal)
            .filter(UserTotal.user_id_points == user_id, UserTotal.contest_code == contest_code)
            .first()
        )
        if user_total:
            user_total.total_points_user = total_points
        else:
            user_total = UserTotal(
                contest_code=contest_code,
                user_id_points=user_id,
                total_points_user=total_points,
            )
            db.add(user_total)

    db.commit()

    return {"message": "User total points updated successfully"}

@app.post("/tradingWindow")
async def trading_window(data: dict, db: Session = Depends(get_db)) :     
    # Example usage:
    # You can send a POST request with JSON data to /tradingWindow with the required payload.
    # {"user_id": 1, "value": 100, "player_id": 1, "contest_code": "4Wyy"}
    user_id = data.get("user_id")
    value = data.get("value")
    player_id = data.get("player_id")
    contest_code = data.get("contest_code")

    print(contest_code)
    trading_window_status= db.query(TradingWindowStatus).filter(TradingWindowStatus.contest_code == contest_code).first()
    print(trading_window_status)
    # # trading_window_status = db.query(TradingWindowStatus).filter(TradingWindowStatus.contest_code == contest_code).first()
    # trading_window_status = db.query(TradingWindowStatus)
    
    
    if trading_window_status.is_trading_window_over:

        trade_window_entries = db.query(TradeWindow).all()
        if not trade_window_entries:
            raise HTTPException(status_code=404, detail="No entries found in TradeWindow")
        
        for entry in trade_window_entries:
            user_id_local = entry.user_id
            player_id_local = entry.player_id
            contest_code_local = entry.contest_code

            # Check if the combination already exists in ContestBid
            existing_bid = (
                db.query(ContestBid)
                .filter(ContestBid.player_id == player_id_local,
                        ContestBid.user_id == user_id_local,
                        ContestBid.contest_code == contest_code_local)
                .first()
            )

            if existing_bid:
                existing_bid.is_traded_in = True
                existing_bid.is_traded_out = False
            else:
                # Create a new row in ContestBid
                new_bid = ContestBid(contest_code=contest_code_local,user_id=user_id, player_id=player_id, is_traded_in=True, is_traded_out=False)
                db.add(new_bid)
            
        db.commit()
        # Empty the tables
        db.query(PlayerTradedOutCount).delete()
        db.query(TradeWindow).delete()
        db.commit()

        return {"message": "Table Updation Successful"}
        
    
    else:
        user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == user_id).scalar()
        if user_coins < value:  #check if enough coins or not
            raise HTTPException(status_code=400, detail="Insufficient coins for this trade")
        
        user_traded_out_count = db.query(PlayerTradedOutCount.traded_out_count).filter(PlayerTradedOutCount.user_id == user_id).scalar()
        if user_traded_out_count >= 1:  
            existing_bidder = db.query(TradeWindow).filter(TradeWindow.player_id == player_id, TradeWindow.contest_code == contest_code).first()

            if existing_bidder: #check to see if there is already an entry for the same player in that same contest code
                existing_bidder_user_id = existing_bidder.user_id #get the current highest bidder for the player
                existing_bidder_value = existing_bidder.bid_coins

                if user_id != existing_bidder_user_id and value > existing_bidder_value: #check if new user has bid and bid higher
                    # Add the existing user's coins back to his tally and increase his traded_out_count by 1 as well
                    existing_user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == existing_bidder_user_id).scalar()
                    existing_user_coins += existing_bidder_value
                    db.query(ContestOverview).filter(ContestOverview.user_id == existing_bidder_user_id).update({"coins": existing_user_coins})
                    existing_user_traded_out_count = db.query(PlayerTradedOutCount).filter(PlayerTradedOutCount.user_id == existing_bidder_user_id).first()
                    temp_existing_user_traded_out_count = existing_user_traded_out_count.traded_out_count + 1
                    db.query(PlayerTradedOutCount).filter(PlayerTradedOutCount.user_id == existing_bidder_user_id).update({"traded_out_count": temp_existing_user_traded_out_count})
                    #Subtract the new user's coins and decrease his traded_out_count
                    user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == user_id).scalar()
                    user_coins -= value
                    db.query(ContestOverview).filter(ContestOverview.user_id == user_id).update({"coins": user_coins})
                    user_traded_out_count -= 1
                    db.query(PlayerTradedOutCount).filter(PlayerTradedOutCount.user_id == user_id).update({"traded_out_count": user_traded_out_count})
                    db.query(TradeWindow).filter(TradeWindow.player_id == player_id).update({"user_id": user_id})
                    db.query(TradeWindow).filter(TradeWindow.player_id == player_id).update({"bid_coins": value})

                    db.commit()

                else:
                    raise HTTPException(status_code=400, detail="Either you are already the highest bidder or you have bid less than the current bid")
                
            else:
                user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == user_id, ContestOverview.contest_code == contest_code).scalar()
                user_coins -= value
                db.query(ContestOverview).filter(ContestOverview.user_id == user_id, ContestOverview.contest_code == contest_code).update({"coins": user_coins})
                
                new_bidder = TradeWindow(
                    contest_code = contest_code,
                    user_id = user_id,
                    player_id = player_id,
                    bid_coins = value
                )
                db.add(new_bidder)

                user_traded_out_count -= 1
                db.query(PlayerTradedOutCount).filter(PlayerTradedOutCount.user_id == user_id).update({"traded_out_count": user_traded_out_count})

                db.commit()
        
        else:
            raise HTTPException(status_code=400, detail="Remove a player from your team to be able to bid")
        
        return {"message": "Trade successful"}

@app.post("/tradedout")
async def tradedOut(data: dict, db: Session = Depends(get_db)):
    user_id = data.get("user_id")
    player_id = data.get("player_id")

    bid = db.query(ContestBid).filter(ContestBid.user_id == user_id, ContestBid.player_id == player_id).first()

    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    # Update the bid status
    bid.is_traded_out = True
    bid.is_traded_in = False
    
    user = db.query(PlayerTradedOutCount).filter(PlayerTradedOutCount.user_id == user_id).first()
    if user:
        new_traded_out_count = user.traded_out_count + 1
        user.traded_out_count = new_traded_out_count
        db.commit()
    else:
        new_user = PlayerTradedOutCount(
            user_id = user_id,
            traded_out_count = 1
        )
        db.add(new_user)
        db.commit()
    return {"message": "Tradeout successful"}



@app.get("/userContests")
async def getUserContest(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    username = current_user.username
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return {"username": username, "contest_codes": []}  # User not found

    contest_codes = db.query(ContestOverview.contest_code).filter(ContestOverview.user_id == user.id).all()
    contest_codes = [code[0] for code in contest_codes]

    return {"username": username, "contest_codes": contest_codes}

@app.post("/makeCaptain")
async def makeCaptain(data: dict,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    player_id = data.get("player_id")
    contest_code = data.get("contest_code")

    existing_captain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.player_role == 'CA'
        ).first()
    
    if existing_captain:
        raise HTTPException(status_code=400, detail="You already have a captain")

    contest_bid = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.player_id == player_id,
            ContestBid.user_id == user_id
        ).first()
    
    contest_bid.player_role = 'CA'
    db.commit()
    db.close()

    return {"message": "Player made captain successfully"}

@app.post("/makeViceCaptain")
async def makeViceCaptain(data: dict,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    player_id = data.get("player_id")
    user_id = current_user.id
    contest_code = data.get("contest_code")

    existing_captain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.player_role == 'VC'
        ).first()
    
    if existing_captain:
        raise HTTPException(status_code=400, detail="You already have a vice-captain")

    contest_bid = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.player_id == player_id,
            ContestBid.user_id == user_id
        ).first()
    
    contest_bid.player_role = 'VC'
    db.commit()
    db.close()

    return {"message": "Player made vice-captain successfully"}

@app.get("/leaderboard/{contest_code}")
async def getLeaderboard(contest_code:str, db: Session = Depends(get_db)):
    leaderboard_data = (
            db.query(UserTotal.user_id_points, UserTotal.total_points_user, User.username)
            .join(User, User.id == UserTotal.user_id_points)
            .filter(UserTotal.contest_code == contest_code)
            .order_by(UserTotal.total_points_user.desc())
            .all()
        )

    if not leaderboard_data:
        raise HTTPException(status_code=404, detail="No leaderboard data found for the contest code")

        # Prepare the leaderboard response
    leaderboard_response = [
        {"username": username, "total_points": total_points_user}
            for user_id_points, total_points_user, username in leaderboard_data
    ]

    db.close()
    return leaderboard_response

@app.post("/change_captain")
async def change_captain(data: dict,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    player_id = data.get("player_id")
    contest_code = data.get("contest_code")

    # Check whether person is already a Captain
    existing_captain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.player_id == player_id,
            ContestBid.player_role == 'CA'
        ).first()

    if existing_captain: # check if player is already the captain
        raise HTTPException(status_code=400, detail="Player is already the captain")

    # Check if there are enough coins for the user
    user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == user_id).scalar()

    if user_coins < 120:
        raise HTTPException(status_code=400, detail="Not enough coins to be able to change captains")
        
    # Update player_role to 'CA' in contestbid table
    captain_to_be = db.query(ContestBid).filter(
        ContestBid.contest_code == contest_code,
        ContestBid.user_id == user_id,
        ContestBid.player_id == player_id
    ).first()


    current_vicecaptain = db.query(ContestBid).filter(
        ContestBid.contest_code == contest_code,
        ContestBid.user_id == user_id,
        ContestBid.player_role == 'VC'
    ).first()

    current_captain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.player_role == 'CA'
    ).first()
    
    if not captain_to_be:
        raise HTTPException(status_code=404, detail="Player not in your team")
    
    if current_vicecaptain.player_id == captain_to_be.player_id:
        current_captain.player_role = 'VC'
    else:
        current_captain.player_role = ''

    captain_to_be.player_role = 'CA'

    # Subtract 120 coins from user
    user_coins -= 120
    db.query(ContestOverview).filter(ContestOverview.user_id == user_id).update({"coins": user_coins})
        # Commit the changes to the database
    db.commit()
    db.close()

    return {"message": "Captain changed successfully"}


@app.post("/change_vicecaptain")
async def change_vicecaptain(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    player_id = data.get("player_id")
    contest_code = data.get("contest_code")

    existing_vicecaptain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.player_id == player_id,
            ContestBid.player_role == 'VC'
        ).first()

    if existing_vicecaptain: # check if player is already the vice-captain
        raise HTTPException(status_code=400, detail="Player is already the vice-captain")

    # Check if there are enough coins for the user
    user_coins = db.query(ContestOverview.coins).filter(ContestOverview.user_id == user_id).scalar()

    if user_coins < 80:
        raise HTTPException(status_code=400, detail="Not enough coins to be able to change captains")
    
    #remove the previous captain as VC
    current_vicecaptain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.player_role == 'VC'
        ).first()

    current_captain = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.player_role == 'CA'
    ).first()
    
    # Update player_role to 'VC' in contestbid table
    vice_captain_to_be = db.query(ContestBid).filter(
        ContestBid.contest_code == contest_code,
        ContestBid.user_id == user_id,
        ContestBid.player_id == player_id
    ).first()

    if not vice_captain_to_be:
        raise HTTPException(status_code=404, detail="Player not in your team")

    if current_captain.player_id == vice_captain_to_be.player_id:
        current_vicecaptain.player_role = 'CA'
    else:
        current_vicecaptain.player_role = ''

    vice_captain_to_be.player_role = 'VC'

    # Subtract 80 coins from user
    user_coins -= 80
    db.query(ContestOverview).filter(ContestOverview.user_id == user_id).update({"coins": user_coins})
        # Commit the changes to the database
    db.commit()
    db.close()

    return {"message": "Vice-Captain changed successfully"}

@app.post("/markUnsold")
async def markUnsold(data:dict, db: Session = Depends(get_db)):
    contest_code=data.get("contest_code")
    player_id=data.get("player_id")
    db.query(Auction).filter(
            Auction.contest_code == contest_code,
            Auction.player_id == player_id
        ).update({"status": STATUS_UNSOLD})

    db.commit()
    
     # Add the user_id to the unsold_status_dict for the specified contest_code
    if contest_code not in unsold_players_dict:
        unsold_players_dict[contest_code] = []
    
    unsold_players_dict[contest_code].append(player_id)

    db.close()
    return {"message": "Player marked as unsold"}

@app.get("/getUnsold/{contest_code}")
async def getUnsoldPlayers(contest_code:str, db: Session = Depends(get_db)):

    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  

    unsold_players = db.query(Auction).filter(
            Auction.contest_code == contest_code,
            Auction.status == STATUS_UNSOLD
    ).all()
    # Extract the player IDs from the query result
    unsold_player_ids = [player.player_id for player in unsold_players]
    
    player_data = []
    for unsold_player_id in unsold_player_ids:
            player_id = unsold_player_id

            # Query the Player table to get general player details
            player_info = (
                db.query(Player)
                .filter(Player.id == player_id)
                .first()
            )

            # Query the PlayerStat table to get player statistics
            player_stats = (
                db.query(PlayerStat)
                .filter(PlayerStat.player_id == player_id)
                .first()
            )

            if player_info and player_stats:
                player_data.append({
                    "player_info": {
                        "player_id":player_id,
                        "name": player_info.name,
                        "country": player_info.country,
                        "role": player_info.role,
                        "base_price": float(player_info.base_price),
                        "image_link": player_info.image_link,
                        "points": float(player_info.points),
                    },
                    "player_stats": {
                        "matches": player_stats.matches,
                        "runs": player_stats.runs,
                        "avg": float(player_stats.avg),
                        "hundreds": player_stats.hundreds,
                        "wickets": player_stats.wickets,
                        "bowling_avg": float(player_stats.bowling_avg),
                        "economy": float(player_stats.economy),
                        "ranking": player_stats.ranking,
                    },
                })
    
    return {
            "player_data": player_data
        }
'''
{
"contest_code":"gLPz",
"user_id":"1"
}
'''
@app.post("/getUserPlayers/{contest_code}")
async def getUserPlayers(data:dict,db: Session = Depends(get_db)):
    user_id = data.get("user_id")
    contest_code = data.get("contest_code")

    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  
    
    contestOverview = db.query(ContestOverview).filter(ContestOverview.user_id == user_id, ContestOverview.contest_code == contest_code).first()  
    
    if not contestOverview:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_players = db.query(ContestBid).filter(
            ContestBid.contest_code == contest_code,
            ContestBid.user_id == user_id,
            ContestBid.is_traded_in == True
    ).all()
    # Extract the player IDs from the query result
    user_player_ids_price = [(player.player_id, player.price_bought) for player in user_players]
    player_data = []
    for user_player_id, price_bought in user_player_ids_price:
            player_id = user_player_id

            # Query the Player table to get general player details
            player_info = (
                db.query(Player)
                .filter(Player.id == player_id)
                .first()
            )

            # Query the PlayerStat table to get player statistics
            player_stats = (
                db.query(PlayerStat)
                .filter(PlayerStat.player_id == player_id)
                .first()
            )

            if player_info and player_stats:
                player_data.append({
                    "player_info": {
                        "player_id":player_id,
                        "name": player_info.name,
                        "country": player_info.country,
                        "role": player_info.role,
                        "base_price": float(player_info.base_price),
                        "image_link": player_info.image_link,
                        "points": float(player_info.points),
                        "price_bought": price_bought,
                    },
                    "player_stats": {
                        "matches": player_stats.matches,
                        "runs": player_stats.runs,
                        "avg": float(player_stats.avg),
                        "hundreds": player_stats.hundreds,
                        "wickets": player_stats.wickets,
                        "bowling_avg": float(player_stats.bowling_avg),
                        "economy": float(player_stats.economy),
                        "ranking": player_stats.ranking,
                    },
                })
    
    return {
            "player_data": player_data
        }


@app.post("/markRemainingUnsold")
async def markRemainingUnsold(data: dict, db: Session = Depends(get_db)):
    # user_id = data.get("user_id")
    contest_code = data.get("contest_code")

    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  
    
    # is_auctioneer = db.query(Contest).filter(Contest.code == contest_code, Contest.auctioneer_id == user_id).first()
    # if not is_auctioneer:
    #     raise HTTPException(status_code=404, detail = "User not authorised")  
    
    auction_players = db.query(Auction).filter(Auction.contest_code == contest_code, Auction.status == STATUS_INQUEUE).all()
    for player in auction_players:
        player.status = STATUS_UNSOLD
        db.add(player)

    db.commit()

    return {"200":"All reminaing players have been added to unsold queue"}
    
    # return {"unsold_players": unsold_player_ids}

@app.post("/getCurrentPlayerInAuction")
async def getCurrentPlayerInAuction(dict:dict, db: Session = Depends(get_db)):
    contest_code = dict.get("contest_code")
    
    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  
    
    # Get the first player in the auction queue based on auction_order
    first_player_in_queue = db.query(AuctionQueue.player_id).filter(
        AuctionQueue.contest_code == contest_code,
        AuctionQueue.status == STATUS_INQUEUE 
    ).order_by(asc(AuctionQueue.auction_order)).first()
    
    if not first_player_in_queue:
        raise HTTPException(status_code=404, detail="No player in the auction queue")
    
    player_id = first_player_in_queue[0]  # Extracting the player_id from the result tuple
    
    player_id = first_player_in_queue[0]  # Extracting the player_id from the result tuple

    player_data = []
    # Query the Player table to get general player details
    player_info = (
        db.query(Player)
        .filter(Player.id == player_id)
        .first()
    )

    # Query the PlayerStat table to get player statistics
    player_stats = (
        db.query(PlayerStat)
        .filter(PlayerStat.player_id == player_id)
        .first()
    )

    if player_info and player_stats:
        player_data.append({
            "player_info": {
                "player_id":player_id,
                "name": player_info.name,
                "country": player_info.country,
                "role": player_info.role,
                "base_price": float(player_info.base_price),
                "image_link": player_info.image_link,
                "points": float(player_info.points),
            },
            "player_stats": {
                "matches": player_stats.matches,
                "runs": player_stats.runs,
                "avg": float(player_stats.avg),
                "hundreds": player_stats.hundreds,
                "wickets": player_stats.wickets,
                "bowling_avg": float(player_stats.bowling_avg),
                "economy": float(player_stats.economy),
                "ranking": player_stats.ranking,
            },
        })
    
    return {
            "player_data": player_data
        }

@app.post("/changeTradingWindowStatus")
async def changeTradingWindowStatus(contest_code:str, db: Session = Depends(get_db)):
    contest= db.query(TradingWindowStatus).filter(TradingWindowStatus.contest_code == contest_code).first()
    print(contest)
    if contest:
        new_status = not contest.is_trading_window_over
        contest.is_trading_window_over = new_status
        db.commit()
    
    else:
        new_contest = TradingWindowStatus(
            contest_code = contest_code,
            is_trading_window_over = False
        )
        db.add(new_contest)
        db.commit()
    
    return ({"message": "Trading Window Status Changed"})

'''
{
"contest_code":"abCf",
"coins":"90"
}
'''
@app.post("/addCoins")
async def addCoins(dict:dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contest_code = dict.get("contest_code")
    
    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  
    
    coins = int(dict.get("coins"))//2
    contest.total_pot += coins

    contestOverview = db.query(ContestOverview).filter(ContestOverview.contest_code == contest_code, ContestOverview.user_id == current_user.id).first()
    if contestOverview:
        contestOverview.coins += coins

        db.add(contestOverview)
        db.commit()
        return {"success":"coins have been added"}
    

@app.get("/getTotalPot/{contest_code}")
async def getTotalPot(contest_code:str, db: Session = Depends(get_db)):
    
    contest = db.query(Contest).filter(Contest.code == contest_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail = "No contest exists for this contest code")  
    
    return {"Total_pot":contest.total_pot}