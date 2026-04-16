import os
from vars import OWNER, CREDIT
from settings_persistence import get_setting

processing_request = False
cancel_requested = False
caption = get_setting('caption', '/cc1')
endfilename = get_setting('endfilename', '/d')
thumb = get_setting('thumb', '/d')
CR = get_setting('credit', f"{CREDIT}")
cwtoken = get_setting('cwtoken', os.environ.get('CWTOKEN', ''))
cptoken = get_setting('cptoken', os.environ.get('CPTOKEN', ''))
pwtoken = get_setting('pwtoken', os.environ.get('PWTOKEN', ''))
vidwatermark = get_setting('vidwatermark', '/d')
raw_text2 = get_setting('raw_text2', '480')
quality = get_setting('quality', '480p')
res = get_setting('res', '854x480')
topic = get_setting('topic', '/d')

# FIX: Track active conversations to prevent duplicate handler triggers
# This prevents infinite loops when bot.listen() is waiting for input
active_conversations = {}
processed_download_messages = {}
listener_consumed_messages = {}

# History feature settings
history_enabled = True
history_auto_resume = True

# History override: set by history_drm_handler before calling drm_handler
# Keys: file_hash, is_resumable, resume_index, b_name
history_override = {}
