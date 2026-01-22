from datetime import UTC, datetime

from sqlalchemy.dialects.mysql import JSON

from src.app_factory import db


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    total_games = db.Column(db.Integer, default=0)
    wins_good = db.Column(db.Integer, default=0)
    wins_evil = db.Column(db.Integer, default=0)
    current_room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)

    def __repr__(self):
        return f'<User {self.nickname} ({self.openid})>'

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default='WAITING') # WAITING, PLAYING, ENDED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    version = db.Column(db.Integer, default=1)

    game_state = db.relationship('GameState', backref='room', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Room {self.room_number} [{self.status}]>'

class GameState(db.Model):
    __tablename__ = 'game_states'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), unique=True, nullable=False)
    phase = db.Column(db.String(20), default='TEAM_SELECTION')
    round_num = db.Column(db.Integer, default=1)
    vote_track = db.Column(db.Integer, default=0)
    leader_idx = db.Column(db.Integer, default=0)
    current_team = db.Column(JSON)     # Array of openids
    quest_results = db.Column(JSON)    # Array of booleans/null
    roles_config = db.Column(JSON)     # Dict {openid: role}
    players = db.Column(JSON)          # List of openids in order
    votes = db.Column(JSON)            # Dict {openid: vote_value}
    quest_votes = db.Column(JSON)      # List of success/fail (unordered for secrecy)
    phase_start_time = db.Column(db.DateTime, default=lambda: datetime.now(UTC))  # 阶段开始时间
    timeout_seconds = db.Column(db.Integer, default=60)  # 超时秒数（默认 60 秒）

class GameHistory(db.Model):
    __tablename__ = 'game_history'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(32))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    winner_team = db.Column(db.String(10)) # 'GOOD' or 'EVIL'
    players = db.Column(JSON)
    replay_data = db.Column(JSON)
