from src.wechat.commands import CommandType
from src.wechat.parser import parser


def test_parse_create_room():
    cmd = parser.parse("建房", "user1")
    assert cmd.command_type == CommandType.CREATE_ROOM
    
    cmd = parser.parse("创建房间", "user1")
    assert cmd.command_type == CommandType.CREATE_ROOM

def test_parse_join_room():
    cmd = parser.parse("/join 1234", "user1")
    assert cmd.command_type == CommandType.JOIN_ROOM
    assert cmd.args == ["1234"]
    
    cmd = parser.parse("加入 8888", "user1")
    assert cmd.command_type == CommandType.JOIN_ROOM
    assert cmd.args == ["8888"]

def test_parse_pick_team():
    cmd = parser.parse("/pick 1 3 5", "user1")
    assert cmd.command_type == CommandType.PICK_TEAM
    assert cmd.args == ["1", "3", "5"]

def test_parse_vote():
    cmd = parser.parse("/vote yes", "user1")
    assert cmd.command_type == CommandType.VOTE
    assert cmd.args == ["yes"]
    
    cmd = parser.parse("投票 反对", "user1")
    assert cmd.command_type == CommandType.VOTE
    assert cmd.args == ["no"]

def test_parse_unknown():
    cmd = parser.parse("乱七八糟的内容", "user1")
    assert cmd.command_type == CommandType.UNKNOWN
