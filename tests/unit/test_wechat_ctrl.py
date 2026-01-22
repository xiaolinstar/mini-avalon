from unittest.mock import patch

import pytest


@pytest.fixture
def client(app):
    return app.test_client()

def test_wechat_get_verification(client):
    # WeChat verification uses GET with signature, timestamp, nonce, echostr
    params = {
        "signature": "any",
        "timestamp": "any",
        "nonce": "any",
        "echostr": "hello"
    }
    with patch('src.controllers.wechat_ctrl.check_signature', return_value=True):
        response = client.get('/', query_string=params)
        assert response.status_code == 200
        assert response.data.decode() == "hello"

def test_wechat_post_help(client):
    xml_data = """
    <xml>
        <ToUserName><![CDATA[gh_123]]></ToUserName>
        <FromUserName><![CDATA[user_openid]]></FromUserName>
        <CreateTime>123456</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[帮助]]></Content>
    </xml>
    """
    with patch('src.controllers.wechat_ctrl.check_signature', return_value=True):
        response = client.post('/', data=xml_data, content_type='text/xml')
        assert response.status_code == 200
        decoded_data = response.data.decode()
        # If it failed, the error message from the global handler might be here
        assert "阿瓦隆指令帮助" in decoded_data, f"Response body: {decoded_data}"

def test_wechat_post_profile(client, app):
    xml_data = """
    <xml>
        <ToUserName><![CDATA[gh_123]]></ToUserName>
        <FromUserName><![CDATA[user_openid]]></FromUserName>
        <CreateTime>123456</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[/profile]]></Content>
    </xml>
    """
    with app.app_context():
        # Setup user
        from src.repositories.user_repository import user_repo
        user_repo.create_or_update("user_openid", nickname="Tester")
        
        with patch('src.controllers.wechat_ctrl.check_signature', return_value=True):
            # Also mock game_service.get_user_stats
            with patch('src.services.game_service.GameService.get_user_stats', return_value="Stats Result"):
                response = client.post('/', data=xml_data, content_type='text/xml')
                assert response.status_code == 200
                assert "Stats Result" in response.data.decode()

def test_wechat_error_handler(client):
    xml_data = """
    <xml>
        <ToUserName><![CDATA[gh_123]]></ToUserName>
        <FromUserName><![CDATA[user_openid]]></FromUserName>
        <CreateTime>123456</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[建房]]></Content>
    </xml>
    """
    from src.exceptions.room import RoomException
    
    with patch('src.controllers.wechat_ctrl.check_signature', return_value=True):
        # Mock room_service.create_room to raise a DomainException
        with patch('src.services.room_service.room_service.create_room', side_effect=RoomException(message="测试异常", error_code="TEST-001")):
            response = client.post('/', data=xml_data, content_type='text/xml')
            assert response.status_code == 200
            assert "提示: 测试异常" in response.data.decode()
