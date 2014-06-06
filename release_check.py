
from src.modules.module_track_requests import ModuleTrackRequests
from src.ui.ui_track_requests import UITrackRequests
from src.modules.module_track_history import ModuleTrackHistory

# Check that they are False
assert UITrackRequests._DEBUG_SEARCH == False

assert ModuleTrackRequests._DEBUG == False
assert ModuleTrackRequests._DEBUG_DISABLE_WHATCD == False

assert ModuleTrackHistory.DEBUG == False