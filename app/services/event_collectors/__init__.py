from app.services.event_collectors.crypto_calendar import CryptoCalendarCollector
from app.services.event_collectors.macro_calendar import MacroCalendarCollector
from app.services.event_collectors.regulation_calendar import RegulationCalendarCollector
from app.services.event_collectors.security_calendar import SecurityCalendarCollector
from app.services.event_collectors.tech_calendar import TechCalendarCollector
from app.services.event_collectors.token_unlocks import TokenUnlockCollector


COLLECTORS = {
    "宏观数据": MacroCalendarCollector,
    "Web3": CryptoCalendarCollector,
    "Token解锁": TokenUnlockCollector,
    "AI科技": TechCalendarCollector,
    "监管": RegulationCalendarCollector,
    "网络安全": SecurityCalendarCollector,
}
