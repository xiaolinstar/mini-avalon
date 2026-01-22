import json
from datetime import date, datetime
from typing import Any


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def json_dumps(data: Any) -> str:
    return json.dumps(data, cls=EnhancedJSONEncoder)

def json_loads(data: str) -> Any:
    if not data:
        return None
    return json.loads(data)
