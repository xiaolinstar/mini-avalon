from flask import g, jsonify, make_response

from src.exceptions.base import BaseGameException
from src.utils.logger import get_logger

logger = get_logger(__name__)

def register_error_handlers(app):
    
    @app.errorhandler(BaseGameException)
    def handle_game_exception(e):
        logger.warning(f"Business logic error: {e.error_code} - {e.message}")
        return _format_error_reply(e.message, 200)

    @app.errorhandler(404)
    def handle_not_found(e):
        return _format_error_reply("接口不存在", 404)

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        # In dev mode, return more info, in prod return generic msg
        msg = "系统繁忙，请稍后再试"
        if app.config.get("DEBUG") or app.config.get("TESTING"):
             msg = f"系统错误: {str(e)}"
        
        return _format_error_reply(msg, 500)

def _format_error_reply(message, status_code):
    wechat_msg = getattr(g, 'wechat_msg', None)
    if wechat_msg:
        from wechatpy import create_reply
        # 业务异常显示"提示"，系统异常显示"错误"
        prefix = "提示" if status_code == 200 else "错误"
        reply = create_reply(f"{prefix}: {message}", message=wechat_msg)
        return make_response(reply.render(), 200)
    
    return jsonify({
        "status": "error",
        "message": message
    }), status_code
