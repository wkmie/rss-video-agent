from app.services.web3_hot_collectors.rss import RSSHotFeedCollector
from app.services.web3_hot_collectors.social import LunarCrushCollector, XRecentSearchCollector

HOT_COLLECTORS = [RSSHotFeedCollector, XRecentSearchCollector, LunarCrushCollector]

__all__ = ["HOT_COLLECTORS", "RSSHotFeedCollector", "XRecentSearchCollector", "LunarCrushCollector"]
