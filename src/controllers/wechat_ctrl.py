from flask import Blueprint, g, make_response, request
from wechatpy import create_reply, parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import check_signature

from src.config.settings import settings
from src.utils.logger import get_logger

wechat_bp = Blueprint("wechat", __name__)
logger = get_logger(__name__)

@wechat_bp.route("/", methods=["GET", "POST"])
def wechat():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    echo_str = request.args.get("echostr", "")

    try:
        check_signature(settings.WECHAT_TOKEN, signature, timestamp, nonce)
    except InvalidSignatureException:
        logger.error("Invalid signature from WeChat")
        return make_response("Invalid Signature", 403)

    if request.method == "GET":
        return echo_str

    # POST - Message handling
    msg = parse_message(request.data)
    # Store message in g for global error handler access
    g.wechat_msg = msg
    
    if msg.type == 'text':
        openid = msg.source
        content = msg.content
        logger.info(f"Received text message from {openid}: {content}")
        
        from src.repositories.user_repository import user_repo
        from src.wechat.parser import parser
        from src.wechat.handlers import dispatcher

        # 1. Ensure user exists
        user_repo.create_or_update(openid)

        # 2. Parse Command
        cmd = parser.parse(content, openid)
        
        # 3. Handle Command via Strategy Pattern
        reply_text = dispatcher.dispatch(cmd)

        reply = create_reply(reply_text, message=msg)
        return reply.render()
    else:
        reply = create_reply("目前仅支持文本消息交互", message=msg)
        return reply.render()
