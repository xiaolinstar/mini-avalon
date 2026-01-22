from enum import Enum


class GamePhase(Enum):
    WAITING = "WAITING"
    TEAM_SELECTION = "TEAM_SELECTION"
    TEAM_VOTE = "TEAM_VOTE"
    QUEST_PERFORM = "QUEST_PERFORM"
    ASSASSINATION = "ASSASSINATION"
    GAME_OVER = "GAME_OVER"

class AvalonFSM:
    """
    Core Logic for Avalon Game state transitions.
    This class is pure logic and doesn't handle persistence directly.
    """
    
    @staticmethod
    def get_role_distribution(player_count: int) -> dict[str, int]:
        # Standard Avalon distribution (Good vs Evil)
        # 5 players: 3 Good, 2 Evil
        # 6 players: 4 Good, 2 Evil
        # 7 players: 4 Good, 3 Evil
        # 8 players: 5 Good, 3 Evil
        # 9 players: 6 Good, 3 Evil
        # 10 players: 6 Good, 4 Evil
        dist = {
            5: (3, 2),
            6: (4, 2),
            7: (4, 3),
            8: (5, 3),
            9: (6, 3),
            10: (6, 4)
        }
        return dist.get(player_count, (3, 2))

    @staticmethod
    def get_quest_size(player_count: int, round_num: int) -> int:
        # Sizes for Quest 1-5 based on total players
        # Row: Player Count (5-10), Col: Round (1-5)
        matrix = {
            5: [2, 3, 2, 3, 3],
            6: [2, 3, 4, 3, 4],
            7: [2, 3, 3, 4, 4], # Quest 4 needs 2 fails for Evil to win if >7 players
            8: [3, 4, 4, 5, 5],
            9: [3, 4, 4, 5, 5],
            10: [3, 4, 4, 5, 5]
        }
        return matrix[player_count][round_num - 1]

    def check_transition(self, current_phase: str, target_phase: GamePhase) -> bool:
        # Define allowed transitions
        allowed = {
            "WAITING": [GamePhase.TEAM_SELECTION],
            "TEAM_SELECTION": [GamePhase.TEAM_VOTE],
            "TEAM_VOTE": [GamePhase.QUEST_PERFORM, GamePhase.TEAM_SELECTION, GamePhase.GAME_OVER],
            "QUEST_PERFORM": [GamePhase.TEAM_SELECTION, GamePhase.ASSASSINATION, GamePhase.GAME_OVER],
            "ASSASSINATION": [GamePhase.GAME_OVER]
        }
        return target_phase in allowed.get(current_phase, [])
