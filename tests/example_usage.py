"""
异常使用示例
展示了如何在代码中使用 ClientException、BizException 和 ServerException
"""

from src.exceptions.base import AppException, ClientException, BizException, ServerException


# 客户端异常使用示例
class UserService:
    def validate_input(self, user_data):
        # 当用户输入不符合要求时，抛出 ClientException
        if not user_data.get('openid'):
            raise ClientException(
                message="缺少必需参数 openid",
                error_code="USER-VALIDATION-001",
                details={'missing_field': 'openid'},
                http_status=400
            )
        
        if len(user_data.get('nickname', '')) > 50:
            raise ClientException(
                message="昵称长度不能超过50个字符",
                error_code="USER-VALIDATION-002",
                details={
                    'field': 'nickname',
                    'actual_length': len(user_data.get('nickname', '')),
                    'max_length': 50
                },
                http_status=400
            )

    def check_permission(self, openid, required_role):
        # 当用户权限不足时，抛出 ClientException
        if not self.has_role(openid, required_role):
            raise ClientException(
                message=f"权限不足，需要 {required_role} 角色",
                error_code="USER-PERMISSION-001",
                details={'required_role': required_role, 'user_openid': openid},
                http_status=403  # 权限不足使用403状态码
            )

    def has_role(self, openid, role):
        # 模拟权限检查
        return False


# 业务异常使用示例
class GameService:
    def validate_game_state(self, room_id, current_phase, expected_phase):
        # 当游戏状态不符合操作要求时，抛出 BizException
        if current_phase != expected_phase:
            raise BizException(
                message=f"当前游戏阶段为 {current_phase}，无法执行此操作（期望: {expected_phase}）",
                error_code="GAME-STATE-001",
                details={
                    'room_id': room_id,
                    'current_phase': current_phase,
                    'expected_phase': expected_phase
                },
                http_status=200  # 业务逻辑错误，非HTTP错误
            )

    def check_player_in_game(self, player_openid, room_id):
        # 当玩家不在游戏中时，抛出 BizException
        if not self.is_player_in_room(player_openid, room_id):
            raise BizException(
                message="您不在当前游戏中",
                error_code="GAME-AUTH-001",
                details={'player_openid': player_openid, 'room_id': room_id},
                http_status=200  # 业务逻辑错误，非HTTP错误
            )

    def is_player_in_room(self, openid, room_id):
        # 模拟玩家房间检查
        return False


# 服务端异常使用示例
class DatabaseService:
    def connect_to_db(self):
        # 当数据库连接失败时，抛出 ServerException
        try:
            # 模拟数据库连接
            raise ConnectionError("无法连接到数据库服务器")
        except ConnectionError as e:
            raise ServerException(
                message="数据库连接失败",
                error_code="DB-CONNECTION-001",
                details={'connection_error': str(e)},
                cause=e,
                http_status=500
            )

    def fetch_data(self, query):
        # 当外部服务调用失败时，抛出 ServerException
        try:
            # 模拟数据查询
            raise TimeoutError("查询超时")
        except TimeoutError as e:
            raise ServerException(
                message="数据查询超时",
                error_code="DB-TIMEOUT-001",
                details={'query': query},
                cause=e,
                http_status=500
            )


# 使用示例
def example_usage():
    user_service = UserService()
    game_service = GameService()
    db_service = DatabaseService()

    try:
        # 客户端异常示例
        user_service.validate_input({'nickname': 'a' * 60})  # 昵称太长
    except ClientException as e:
        print(f"客户端错误: {e}, HTTP状态码: {e.http_status}")  # [USER-VALIDATION-002] 昵称长度不能超过50个字符

    try:
        # 业务异常示例
        game_service.check_player_in_game('some_openid', 'room_123')
    except BizException as e:
        print(f"业务错误: {e}, HTTP状态码: {e.http_status}")  # [GAME-AUTH-001] 您不在当前游戏中

    try:
        # 服务端异常示例
        db_service.connect_to_db()
    except ServerException as e:
        print(f"服务端错误: {e}, HTTP状态码: {e.http_status}")  # [DB-CONNECTION-001] 数据库连接失败

if __name__ == "__main__":
    example_usage()