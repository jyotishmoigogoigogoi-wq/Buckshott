import os
import asyncio
import random
import logging
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# Config
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")

# In-Memory Game Storage
private_games = {}
group_games = {}

# SFX Text Effects
SFX = {
    "load": "⟪ ᴄʜᴀᴋ-ᴄʜᴀᴋ ⟫",
    "bang": "▂▃▄▅ 𝘽𝘼𝙉𝙂 ▅▄▃▂",
    "click": "· · · ᶜˡⁱᶜᵏ · · ·",
    "shuffle": "⟪ sʜᴜғғʟᴇ ⟫",
    "tension": "· · ·",
    "death": "☠️ 𝔉𝔄𝔗𝔄𝔏𝔈𝔗𝔜 ☠️"
}

# Emojis
HEART = "♥️"
DEAD_HEART = "🖤"
LIVE_SHELL = "🩸"
BLANK_SHELL = "💨"
UNKNOWN_SHELL = "❓"


@app.route('/')
def health():
    return "🔫 BUCKSHOT ROULETTE BOT IS LIVE"


def run_flask():
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', int(os.environ.get("PORT", 8000)), app, threaded=True)
    server.serve_forever()


def get_hp_display(hp: int, max_hp: int = 3) -> str:
    """Generate HP display with hearts"""
    return HEART * hp + DEAD_HEART * (max_hp - hp)


def generate_shells() -> tuple:
    """Generate random shells for the shotgun"""
    live = random.randint(1, 4)
    blank = random.randint(1, 4)
    shells = ['L'] * live + ['B'] * blank
    random.shuffle(shells)
    return ''.join(shells), live, blank


# ═══════════════════════════════════════
#           WELCOME MESSAGE
# ═══════════════════════════════════════

def get_welcome_msg() -> str:
    """Welcome message with rules and commands"""
    return """
⛧═══════════════════════════════════⛧

              𝔅𝔘ℭ𝔎𝔖ℌ𝔒𝔗
              ℜ𝔒𝔘𝔏𝔈𝔗𝔗𝔈

⛧═══════════════════════════════════⛧

      ☠️ 𝘋𝘦𝘢𝘵𝘩 𝘢𝘸𝘢𝘪𝘵𝘴... ☠️

═══════════════════════════════════════

📜 𝐑𝐔𝐋𝐄𝐒:

┊ 🩸 LIVE shell = Damage (-1 HP)
┊ 💨 BLANK shell = No damage
┊ 🍀 BLANK on self = Extra turn!
┊ 💀 0 HP = Game Over

═══════════════════════════════════════

🎯 𝐇𝐎𝐖 𝐓𝐎 𝐏𝐋𝐀𝐘:

┊ 🤖 /buckshotpv
┊    ➜ Play vs AI (Private Chat)
┊
┊ 👥 /buckshot  
┊    ➜ Play vs Friend (Group Chat)

═══════════════════════════════════════

    ༺ 𝘓𝘰𝘢𝘥. 𝘚𝘩𝘰𝘰𝘵. 𝘚𝘶𝘳𝘷𝘪𝘷𝘦. ༻

⛧═══════════════════════════════════⛧
"""


# ═══════════════════════════════════════
#           GROUP LOBBY MESSAGES
# ═══════════════════════════════════════

def get_lobby_msg(players: list, max_players: int = 2) -> str:
    """Lobby waiting screen for group games"""
    count = len(players)

    if count == 0:
        p1_line = "⦾ ᴡᴀɪᴛɪɴɢ..."
        p2_line = "⦾ ᴡᴀɪᴛɪɴɢ..."
    elif count == 1:
        p1_name = f"@{players[0]['username']}" if players[0]['username'] else players[0]['name']
        p1_line = f"⦿ {p1_name[:18]}"
        p2_line = "⦾ ᴡᴀɪᴛɪɴɢ..."
    else:
        p1_name = f"@{players[0]['username']}" if players[0]['username'] else players[0]['name']
        p2_name = f"@{players[1]['username']}" if players[1]['username'] else players[1]['name']
        p1_line = f"⦿ {p1_name[:18]}"
        p2_line = f"⦿ {p2_name[:18]}"

    return f"""
༺═══════════════════════════════════༻

          𝔻𝔼𝔸𝕋ℍ 𝕃𝕆𝔹𝔹𝕐

༺═══════════════════════════════════༻

👥 ᴘʟᴀʏᴇʀs: {count}/{max_players}

════════════════════════════════════

{p1_line}

{p2_line}

════════════════════════════════════

⏳ 𝘈𝘸𝘢𝘪𝘵𝘪𝘯𝘨 𝘷𝘪𝘤𝘵𝘪𝘮...

👇 ᴄʟɪᴄᴋ ᴊᴏɪɴ ᴛᴏ ᴇɴᴛᴇʀ

༺═══════════════════════════════════༻
"""


def get_match_start_msg(p1: dict, p2: dict) -> str:
    """Match found message when 2 players join"""
    p1_name = f"@{p1['username']}" if p1['username'] else p1['name']
    p2_name = f"@{p2['username']}" if p2['username'] else p2['name']

    return f"""
⛧═══════════════════════════════════⛧

          ⚔️ 𝕄𝔸𝕋ℂℍ 𝔽𝕆𝕌ℕ𝔻 ⚔️

⛧═══════════════════════════════════⛧

════════════════════════════════════

        🔴 {p1_name[:15]}

            ⚔️ ᴠs ⚔️

        🔵 {p2_name[:15]}

════════════════════════════════════

        {SFX['load']}

      🔫 ʟᴏᴀᴅɪɴɢ sʜᴏᴛɢᴜɴ...

⛧═══════════════════════════════════⛧
"""


# ═══════════════════════════════════════
#           GAME DISPLAY MESSAGES
# ═══════════════════════════════════════

def get_game_display(game: dict, is_group: bool = False) -> str:
    """Main game display showing HP, shells, and turn info"""
    p1_hp = get_hp_display(game['p1_hp'])
    p2_hp = get_hp_display(game['p2_hp'])

    if is_group:
        p1_name = f"@{game['p1']['username']}" if game['p1']['username'] else game['p1']['name']
        p2_name = f"@{game['p2']['username']}" if game['p2']['username'] else game['p2']['name']
        p1_display = p1_name[:12]
        p2_display = p2_name[:12]
    else:
        p1_display = "𝕐𝕆𝕌"
        p2_display = "𝔻𝔼𝔸𝕃𝔼ℝ"

    remaining = len(game['shells']) - game['shell_idx']
    shells_display = UNKNOWN_SHELL * min(remaining, 8)

    turn_name = p1_display if game['turn'] == 1 else p2_display
    turn_indicator = "🔴" if game['turn'] == 1 else ("🔵" if is_group else "🤖")

    return f"""
◢◤═══════════════════════════════◢◤

          𝔅𝔘ℭ𝔎𝔖ℌ𝔒𝔗
          ℜ𝔒𝔘𝔏𝔈𝔗𝔗𝔈

◢◤═══════════════════════════════◢◤

♰ {p1_display}
{p1_hp}

            ⚔️ ᴠs ⚔️

♰ {p2_display}
{p2_hp}

════════════════════════════════════

⌁ 𝐒𝐇𝐎𝐓𝐆𝐔𝐍 ⌁

░▒▓ {shells_display} ▓▒░

🩸 ʟɪᴠᴇ: {game['live']}    💨 ʙʟᴀɴᴋ: {game['blank']}

════════════════════════════════════

{turn_indicator} {turn_name}'s ᴛᴜʀɴ

◢◤═══════════════════════════════◢◤
"""


def get_shot_result_live_opponent(shooter: str, target: str) -> str:
    """Shot result when LIVE shell hits opponent"""
    return f"""
⛧═══════════════════════════════════⛧

🔫 {shooter} ➤ {target}

{SFX['tension']}

💥 {SFX['bang']} 💥

════════════════════════════════════

🩸 𝐋𝐈𝐕𝐄 𝐒𝐇𝐄𝐋𝐋

════════════════════════════════════

⚰️ ᴅɪʀᴇᴄᴛ ʜɪᴛ! −1 ♥️

⛧═══════════════════════════════════⛧
"""


def get_shot_result_live_self(shooter: str) -> str:
    """Shot result when LIVE shell hits self"""
    return f"""
⛧═══════════════════════════════════⛧

🔫 {shooter} ➤ 𝕊𝔼𝕃𝔽

{SFX['tension']}

💥 {SFX['bang']} 💥

════════════════════════════════════

🩸 𝐋𝐈𝐕𝐄 𝐒𝐇𝐄𝐋𝐋

════════════════════════════════════

😵 sᴇʟғ ᴅᴀᴍᴀɢᴇ! −1 ♥️

⛧═══════════════════════════════════⛧
"""


def get_shot_result_blank_opponent(shooter: str, target: str) -> str:
    """Shot result when BLANK shell at opponent"""
    return f"""
༺═══════════════════════════════════༻

🔫 {shooter} ➤ {target}

{SFX['tension']}

{SFX['click']}

════════════════════════════════════

💨 𝐁𝐋𝐀𝐍𝐊 𝐒𝐇𝐄𝐋𝐋

════════════════════════════════════

😮‍💨 {target} sᴜʀᴠɪᴠᴇs!

༺═══════════════════════════════════༻
"""


def get_shot_result_blank_self(shooter: str) -> str:
    """Shot result when BLANK shell at self - EXTRA TURN"""
    return f"""
༺═══════════════════════════════════༻

🔫 {shooter} ➤ 𝕊𝔼𝕃𝔽

{SFX['tension']}

{SFX['click']}

════════════════════════════════════

💨 𝐁𝐋𝐀𝐍𝐊 𝐒𝐇𝐄𝐋𝐋

════════════════════════════════════

🍀 ʟᴜᴄᴋʏ! ᴇxᴛʀᴀ ᴛᴜʀɴ!

༺═══════════════════════════════════༻
"""


def get_reload_msg(live: int, blank: int) -> str:
    """Reload message when shells run out"""
    shells_visual = (LIVE_SHELL * live) + (BLANK_SHELL * blank)
    unknown_visual = UNKNOWN_SHELL * (live + blank)

    return f"""
░▒▓█═══════════════════════════█▓▒░

          𝐑𝐄𝐋𝐎𝐀𝐃𝐈𝐍𝐆

░▒▓█═══════════════════════════█▓▒░

{SFX['load']}

════════════════════════════════════

{shells_visual}

════════════════════════════════════

{SFX['shuffle']}

════════════════════════════════════

{unknown_visual}

════════════════════════════════════

🩸 ʟɪᴠᴇ: {live}    💨 ʙʟᴀɴᴋ: {blank}

════════════════════════════════════

༒ 𝘓𝘰𝘢𝘥𝘦𝘥 & 𝘚𝘩𝘶𝘧𝘧𝘭𝘦𝘥 ༒

░▒▓█═══════════════════════════█▓▒░
"""


def get_game_over_msg(winner: str, loser: str, winner_mention: str = None) -> str:
    """Game over message with winner and loser"""
    mention_line = f"\n\n🎊 ɢɢ ᴡᴘ {winner_mention}!" if winner_mention else ""

    return f"""
⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧

          {SFX['death']}

⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧

════════════════════════════════════

            𝐆𝐀𝐌𝐄 𝐎𝐕𝐄𝐑

════════════════════════════════════

👑 𝕎𝕀ℕℕ𝔼ℝ
{winner}

════════════════════════════════════

⚰️ 𝕃𝕆𝕊𝔼ℝ
{loser}

════════════════════════════════════

✧ 𝘝𝘪𝘤𝘵𝘰𝘳𝘺 𝘪𝘴 𝘤𝘭𝘢𝘪𝘮𝘦𝘥 ✧{mention_line}

⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧⛧
"""


def get_ai_thinking_msg() -> str:
    """AI thinking message"""
    return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

          🤖 𝔻𝔼𝔸𝕃𝔼ℝ

              {SFX['tension']}

          🔮 ᴛʜɪɴᴋɪɴɢ...

              {SFX['tension']}

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def get_extra_turn_msg(name: str) -> str:
    """Extra turn notification"""
    return f"""
༺═══════════════════════════════════༻

          🍀 𝐄𝐗𝐓𝐑𝐀 𝐓𝐔𝐑𝐍

════════════════════════════════════

{name} ɢᴇᴛs ᴀɴᴏᴛʜᴇʀ sʜᴏᴛ!

༺═══════════════════════════════════༻
"""


# ═══════════════════════════════════════
#               KEYBOARDS
# ═══════════════════════════════════════

def get_private_game_kb(game_id: str) -> InlineKeyboardMarkup:
    """Keyboard for private game actions"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 𝐒𝐇𝐎𝐎𝐓 𝐃𝐄𝐀𝐋𝐄𝐑", callback_data=f"pv_dealer_{game_id}")],
        [InlineKeyboardButton("🔫 𝐒𝐇𝐎𝐎𝐓 𝐘𝐎𝐔𝐑𝐒𝐄𝐋𝐅", callback_data=f"pv_self_{game_id}")],
    ])


def get_group_game_kb(chat_id: str, p1_id: int, p2_id: int, current_turn_id: int) -> InlineKeyboardMarkup:
    """Keyboard for group game actions"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 𝐒𝐇𝐎𝐎𝐓 𝐎𝐏𝐏𝐎𝐍𝐄𝐍𝐓", callback_data=f"gp_opp_{chat_id}_{p1_id}_{p2_id}_{current_turn_id}")],
        [InlineKeyboardButton("🔫 𝐒𝐇𝐎𝐎𝐓 𝐘𝐎𝐔𝐑𝐒𝐄𝐋𝐅", callback_data=f"gp_self_{chat_id}_{p1_id}_{p2_id}_{current_turn_id}")],
    ])


def get_lobby_kb(chat_id: str) -> InlineKeyboardMarkup:
    """Keyboard for lobby join button"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ 𝐉𝐎𝐈𝐍 𝐆𝐀𝐌𝐄", callback_data=f"join_{chat_id}")]
    ])


def get_play_again_kb(is_private: bool) -> InlineKeyboardMarkup:
    """Keyboard for play again option"""
    if is_private:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 𝐏𝐋𝐀𝐘 𝐀𝐆𝐀𝐈𝐍", callback_data="play_again_pv")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 𝐍𝐄𝐖 𝐆𝐀𝐌𝐄", callback_data="play_again_gp")]
        ])


# ═══════════════════════════════════════
#              COMMANDS
# ═══════════════════════════════════════

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Welcome message - Private only"""
    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(get_welcome_msg())


async def buckshotpv_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Private game vs AI"""
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ!\n\n"
            "👥 ᴡᴀɴᴛ ᴛᴏ ᴘʟᴀʏ ᴡɪᴛʜ ғʀɪᴇɴᴅs? ᴜsᴇ /buckshot ɪɴ ᴀ ɢʀᴏᴜᴘ!"
        )
        return

    user = update.effective_user
    user_id = str(user.id)

    # Check if already playing
    if user_id in private_games and private_games[user_id].get('status') == 'playing':
        await update.message.reply_text("⚠️ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ!")
        return

    # Generate shells
    shells, live, blank = generate_shells()

    # Create game
    private_games[user_id] = {
        'status': 'playing',
        'p1_hp': 3,
        'p2_hp': 3,
        'shells': shells,
        'shell_idx': 0,
        'live': live,
        'blank': blank,
        'turn': 1,
        'message_id': None
    }

    # Show reload animation
    reload_msg = get_reload_msg(live, blank)
    msg = await update.message.reply_text(reload_msg)
    private_games[user_id]['message_id'] = msg.message_id

    await asyncio.sleep(2)

    # Show game
    game_display = get_game_display(private_games[user_id], is_group=False)
    await msg.edit_text(game_display, reply_markup=get_private_game_kb(user_id))


async def buckshot_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Group game - 2 players"""
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ ɢʀᴏᴜᴘ ᴄʜᴀᴛ!\n\n"
            "🤖 ᴡᴀɴᴛ ᴛᴏ ᴘʟᴀʏ ᴠs ᴀɪ? ᴜsᴇ /buckshotpv ʜᴇʀᴇ!"
        )
        return

    chat_id = str(update.effective_chat.id)

    # Check if game already running
    if chat_id in group_games:
        status = group_games[chat_id].get('status')
        if status == 'waiting' or status == 'playing':
            await update.message.reply_text(
                "⚠️ ᴀ ɢᴀᴍᴇ ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴘʀᴏɢʀᴇss!\n"
                "⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ɪᴛ ᴛᴏ ғɪɴɪsʜ."
            )
            return

    user = update.effective_user

    # Create lobby
    group_games[chat_id] = {
        'status': 'waiting',
        'players': [{
            'id': user.id,
            'username': user.username,
            'name': user.first_name or "Player1"
        }],
        'message_id': None
    }

    lobby_msg = get_lobby_msg(group_games[chat_id]['players'])
    msg = await update.message.reply_text(lobby_msg, reply_markup=get_lobby_kb(chat_id))
    group_games[chat_id]['message_id'] = msg.message_id


# ═══════════════════════════════════════
#           CALLBACK HANDLERS
# ═══════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    data = query.data
    user = query.from_user

    # ─────────────────────────────────
    # JOIN GROUP GAME
    # ─────────────────────────────────
    if data.startswith("join_"):
        chat_id = data.split("_")[1]

        if chat_id not in group_games:
            await query.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        game = group_games[chat_id]

        if game['status'] != 'waiting':
            await query.answer("❌ ɢᴀᴍᴇ ᴀʟʀᴇᴀᴅʏ sᴛᴀʀᴛᴇᴅ!", show_alert=True)
            return

        # Check if already joined
        for p in game['players']:
            if p['id'] == user.id:
                await query.answer("⚠️ ʏᴏᴜ ʜᴀᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴊᴏɪɴᴇᴅ!", show_alert=True)
                return

        # Check if full
        if len(game['players']) >= 2:
            await query.answer("❌ ʟᴏʙʙʏ ɪs ғᴜʟʟ!", show_alert=True)
            return

        # Add player
        game['players'].append({
            'id': user.id,
            'username': user.username,
            'name': user.first_name or "Player2"
        })

        await query.answer("✅ ʏᴏᴜ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ɢᴀᴍᴇ!")

        # Check if ready to start
        if len(game['players']) == 2:
            # Show match found
            match_msg = get_match_start_msg(game['players'][0], game['players'][1])
            await query.edit_message_text(match_msg)
            await asyncio.sleep(2)

            # Initialize game
            shells, live, blank = generate_shells()
            game['status'] = 'playing'
            game['p1'] = game['players'][0]
            game['p2'] = game['players'][1]
            game['p1_hp'] = 3
            game['p2_hp'] = 3
            game['shells'] = shells
            game['shell_idx'] = 0
            game['live'] = live
            game['blank'] = blank
            game['turn'] = 1

            # Show reload
            reload_msg = get_reload_msg(live, blank)
            await query.edit_message_text(reload_msg)
            await asyncio.sleep(2)

            # Show game
            game_display = get_game_display(game, is_group=True)
            current_turn_id = game['p1']['id'] if game['turn'] == 1 else game['p2']['id']
            await query.edit_message_text(
                game_display, 
                reply_markup=get_group_game_kb(chat_id, game['p1']['id'], game['p2']['id'], current_turn_id)
            )
        else:
            # Update lobby
            lobby_msg = get_lobby_msg(game['players'])
            await query.edit_message_text(lobby_msg, reply_markup=get_lobby_kb(chat_id))

        return

    # ─────────────────────────────────
    # PRIVATE GAME - SHOOT DEALER
    # ─────────────────────────────────
    if data.startswith("pv_dealer_"):
        user_id = data.split("_")[2]

        if user_id != str(user.id):
            await query.answer("❌ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)
            return

        if user_id not in private_games:
            await query.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        game = private_games[user_id]

        if game['turn'] != 1:
            await query.answer("⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ʏᴏᴜʀ ᴛᴜʀɴ!", show_alert=True)
            return

        await process_private_shot(query, user_id, target="dealer")
        return

    # ─────────────────────────────────
    # PRIVATE GAME - SHOOT SELF
    # ─────────────────────────────────
    if data.startswith("pv_self_"):
        user_id = data.split("_")[2]

        if user_id != str(user.id):
            await query.answer("❌ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)
            return

        if user_id not in private_games:
            await query.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        game = private_games[user_id]

        if game['turn'] != 1:
            await query.answer("⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ʏᴏᴜʀ ᴛᴜʀɴ!", show_alert=True)
            return

        await process_private_shot(query, user_id, target="self")
        return

    # ─────────────────────────────────
    # GROUP GAME - SHOOT OPPONENT
    # ─────────────────────────────────
    if data.startswith("gp_opp_"):
        parts = data.split("_")
        chat_id = parts[2]
        p1_id = int(parts[3])
        p2_id = int(parts[4])
        current_turn_id = int(parts[5])

        # Check if user is part of the game
        if user.id != p1_id and user.id != p2_id:
            await query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴘᴀʀᴛ ᴏғ ᴛʜɪs ɢᴀᴍᴇ!", show_alert=True)
            return

        # Check if it's their turn
        if user.id != current_turn_id:
            await query.answer("⏳ ᴋɪɴᴅʟʏ ᴡᴀɪᴛ ғᴏʀ ʏᴏᴜʀ ᴛᴜʀɴ!", show_alert=True)
            return

        if chat_id not in group_games:
            await query.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        await process_group_shot(query, chat_id, user.id, target="opponent")
        return

    # ─────────────────────────────────
    # GROUP GAME - SHOOT SELF
    # ─────────────────────────────────
    if data.startswith("gp_self_"):
        parts = data.split("_")
        chat_id = parts[2]
        p1_id = int(parts[3])
        p2_id = int(parts[4])
        current_turn_id = int(parts[5])

        # Check if user is part of the game
        if user.id != p1_id and user.id != p2_id:
            await query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴘᴀʀᴛ ᴏғ ᴛʜɪs ɢᴀᴍᴇ!", show_alert=True)
            return

        # Check if it's their turn
        if user.id != current_turn_id:
            await query.answer("⏳ ᴋɪɴᴅʟʏ ᴡᴀɪᴛ ғᴏʀ ʏᴏᴜʀ ᴛᴜʀɴ!", show_alert=True)
            return

        if chat_id not in group_games:
            await query.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        await process_group_shot(query, chat_id, user.id, target="self")
        return

    # ─────────────────────────────────
    # PLAY AGAIN
    # ─────────────────────────────────
    if data == "play_again_pv":
        await query.answer()

        user_id = str(user.id)
        shells, live, blank = generate_shells()

        private_games[user_id] = {
            'status': 'playing',
            'p1_hp': 3,
            'p2_hp': 3,
            'shells': shells,
            'shell_idx': 0,
            'live': live,
            'blank': blank,
            'turn': 1,
            'message_id': query.message.message_id
        }

        reload_msg = get_reload_msg(live, blank)
        await query.edit_message_text(reload_msg)
        await asyncio.sleep(2)

        game_display = get_game_display(private_games[user_id], is_group=False)
        await query.edit_message_text(game_display, reply_markup=get_private_game_kb(user_id))
        return

    if data == "play_again_gp":
        await query.answer("👆 sᴇɴᴅ /buckshot ᴛᴏ sᴛᴀʀᴛ ᴀ ɴᴇᴡ ɢᴀᴍᴇ!", show_alert=True)
        return

    await query.answer()


# ═══════════════════════════════════════
#          GAME LOGIC - PRIVATE
# ═══════════════════════════════════════

async def process_private_shot(query, user_id: str, target: str):
    """Process a shot in private game"""
    await query.answer()

    game = private_games[user_id]

    # Get shell
    shell = game['shells'][game['shell_idx']]
    is_live = shell == 'L'
    game['shell_idx'] += 1

    if is_live:
        game['live'] -= 1
    else:
        game['blank'] -= 1

    # Process shot
    extra_turn = False

    if target == "dealer":
        shooter = "𝕐𝕆𝕌"
        target_name = "𝔻𝔼𝔸𝕃𝔼ℝ"
        if is_live:
            game['p2_hp'] -= 1
            result_msg = get_shot_result_live_opponent(shooter, target_name)
        else:
            result_msg = get_shot_result_blank_opponent(shooter, target_name)
        game['turn'] = 2
    else:
        shooter = "𝕐𝕆𝕌"
        if is_live:
            game['p1_hp'] -= 1
            game['turn'] = 2
            result_msg = get_shot_result_live_self(shooter)
        else:
            extra_turn = True
            result_msg = get_shot_result_blank_self(shooter)

    # Show result
    await query.edit_message_text(result_msg)
    await asyncio.sleep(2)

    # Check game over
    if game['p1_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg("𝔻𝔼𝔸𝕃𝔼ℝ 🤖", "𝕐𝕆𝕌 😵")
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
        return

    if game['p2_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg("𝕐𝕆𝕌 👑", "𝔻𝔼𝔸𝕃𝔼ℝ 🤖")
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
        return

    # Check reload
    if game['shell_idx'] >= len(game['shells']):
        shells, live, blank = generate_shells()
        game['shells'] = shells
        game['shell_idx'] = 0
        game['live'] = live
        game['blank'] = blank

        reload_msg = get_reload_msg(live, blank)
        await query.edit_message_text(reload_msg)
        await asyncio.sleep(2)

    # Extra turn or AI turn
    if extra_turn:
        extra_msg = get_extra_turn_msg("𝕐𝕆𝕌")
        await query.edit_message_text(extra_msg)
        await asyncio.sleep(1.5)

        game_display = get_game_display(game, is_group=False)
        await query.edit_message_text(game_display, reply_markup=get_private_game_kb(user_id))
    else:
        # AI Turn
        await process_ai_turn(query, user_id)


async def process_ai_turn(query, user_id: str):
    """Process AI (dealer) turn"""
    game = private_games[user_id]

    while game['turn'] == 2 and game['status'] == 'playing':
        # AI thinking
        await query.edit_message_text(get_ai_thinking_msg())
        await asyncio.sleep(1.5)

        # AI decision - simple strategy
        remaining = len(game['shells']) - game['shell_idx']
        live_ratio = game['live'] / remaining if remaining > 0 else 0

        # If low chance of live, shoot self for potential extra turn
        if live_ratio < 0.4 and random.random() > 0.3:
            ai_target = "self"
        else:
            ai_target = "player"

        # Get shell
        shell = game['shells'][game['shell_idx']]
        is_live = shell == 'L'
        game['shell_idx'] += 1

        if is_live:
            game['live'] -= 1
        else:
            game['blank'] -= 1

        # Process
        extra_turn = False

        if ai_target == "player":
            if is_live:
                game['p1_hp'] -= 1
                result_msg = get_shot_result_live_opponent("𝔻𝔼𝔸𝕃𝔼ℝ", "𝕐𝕆𝕌")
            else:
                result_msg = get_shot_result_blank_opponent("𝔻𝔼𝔸𝕃𝔼ℝ", "𝕐𝕆𝕌")
            game['turn'] = 1
        else:
            if is_live:
                game['p2_hp'] -= 1
                game['turn'] = 1
                result_msg = get_shot_result_live_self("𝔻𝔼𝔸𝕃𝔼ℝ")
            else:
                extra_turn = True
                result_msg = get_shot_result_blank_self("𝔻𝔼𝔸𝕃𝔼ℝ")

        # Show result
        await query.edit_message_text(result_msg)
        await asyncio.sleep(2)

        # Check game over
        if game['p1_hp'] <= 0:
            game['status'] = 'finished'
            game_over = get_game_over_msg("𝔻𝔼𝔸𝕃𝔼ℝ 🤖", "𝕐𝕆𝕌 😵")
            await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
            return

        if game['p2_hp'] <= 0:
            game['status'] = 'finished'
            game_over = get_game_over_msg("𝕐𝕆𝕌 👑", "𝔻𝔼𝔸𝕃𝔼ℝ 🤖")
            await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
            return

        # Check reload
        if game['shell_idx'] >= len(game['shells']):
            shells, live, blank = generate_shells()
            game['shells'] = shells
            game['shell_idx'] = 0
            game['live'] = live
            game['blank'] = blank

            reload_msg = get_reload_msg(live, blank)
            await query.edit_message_text(reload_msg)
            await asyncio.sleep(2)

        if extra_turn:
            extra_msg = get_extra_turn_msg("𝔻𝔼𝔸𝕃𝔼ℝ")
            await query.edit_message_text(extra_msg)
            await asyncio.sleep(1.5)
        else:
            break

    # Player's turn
    if game['status'] == 'playing':
        game_display = get_game_display(game, is_group=False)
        await query.edit_message_text(game_display, reply_markup=get_private_game_kb(user_id))


# ═══════════════════════════════════════
#          GAME LOGIC - GROUP
# ═══════════════════════════════════════

async def process_group_shot(query, chat_id: str, shooter_id: int, target: str):
    """Process a shot in group game"""
    await query.answer()

    game = group_games[chat_id]

    # Determine shooter and opponent
    if game['turn'] == 1:
        shooter = game['p1']
        opponent = game['p2']
        shooter_hp_key = 'p1_hp'
        opponent_hp_key = 'p2_hp'
    else:
        shooter = game['p2']
        opponent = game['p1']
        shooter_hp_key = 'p2_hp'
        opponent_hp_key = 'p1_hp'

    shooter_name = f"@{shooter['username']}" if shooter['username'] else shooter['name']
    opponent_name = f"@{opponent['username']}" if opponent['username'] else opponent['name']

    # Get shell
    shell = game['shells'][game['shell_idx']]
    is_live = shell == 'L'
    game['shell_idx'] += 1

    if is_live:
        game['live'] -= 1
    else:
        game['blank'] -= 1

    # Process shot
    extra_turn = False

    if target == "opponent":
        if is_live:
            game[opponent_hp_key] -= 1
            result_msg = get_shot_result_live_opponent(shooter_name[:12], opponent_name[:12])
        else:
            result_msg = get_shot_result_blank_opponent(shooter_name[:12], opponent_name[:12])
        game['turn'] = 2 if game['turn'] == 1 else 1
    else:
        if is_live:
            game[shooter_hp_key] -= 1
            game['turn'] = 2 if game['turn'] == 1 else 1
            result_msg = get_shot_result_live_self(shooter_name[:12])
        else:
            extra_turn = True
            result_msg = get_shot_result_blank_self(shooter_name[:12])

    # Show result
    await query.edit_message_text(result_msg)
    await asyncio.sleep(2)

    # Check game over - with winner mention
    p1_name = f"@{game['p1']['username']}" if game['p1']['username'] else game['p1']['name']
    p2_name = f"@{game['p2']['username']}" if game['p2']['username'] else game['p2']['name']

    if game['p1_hp'] <= 0:
        game['status'] = 'finished'
        # Winner is p2, mention them
        winner_mention = f"@{game['p2']['username']}" if game['p2']['username'] else None
        game_over = get_game_over_msg(p2_name + " 👑", p1_name + " 💀", winner_mention)
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(False))
        del group_games[chat_id]
        return

    if game['p2_hp'] <= 0:
        game['status'] = 'finished'
        # Winner is p1, mention them
        winner_mention = f"@{game['p1']['username']}" if game['p1']['username'] else None
        game_over = get_game_over_msg(p1_name + " 👑", p2_name + " 💀", winner_mention)
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(False))
        del group_games[chat_id]
        return

    # Check reload
    if game['shell_idx'] >= len(game['shells']):
        shells, live, blank = generate_shells()
        game['shells'] = shells
        game['shell_idx'] = 0
        game['live'] = live
        game['blank'] = blank

        reload_msg = get_reload_msg(live, blank)
        await query.edit_message_text(reload_msg)
        await asyncio.sleep(2)

    # Extra turn message
    if extra_turn:
        extra_msg = get_extra_turn_msg(shooter_name[:12])
        await query.edit_message_text(extra_msg)
        await asyncio.sleep(1.5)

    # Show game
    game_display = get_game_display(game, is_group=True)
    current_turn_id = game['p1']['id'] if game['turn'] == 1 else game['p2']['id']
    await query.edit_message_text(
        game_display, 
        reply_markup=get_group_game_kb(chat_id, game['p1']['id'], game['p2']['id'], current_turn_id)
    )


# ═══════════════════════════════════════
#               MAIN
# ═══════════════════════════════════════

async def main():
    """Main function to run the bot"""
    logger.info("🔫 Starting Buckshot Roulette Bot...")

    bot = Application.builder().token(TOKEN).build()

    # Commands
    bot.add_handler(CommandHandler("start", start_cmd))
    bot.add_handler(CommandHandler("buckshotpv", buckshotpv_cmd))
    bot.add_handler(CommandHandler("buckshot", buckshot_cmd))

    # Callbacks
    bot.add_handler(CallbackQueryHandler(callback_handler))

    # Flask for health check
    Thread(target=run_flask, daemon=True).start()

    # Start bot
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling(drop_pending_updates=True)

    logger.info("🔫 BUCKSHOT ROULETTE BOT READY!")

    try:
        while True:
            await asyncio.sleep(3600)
    except:
        pass
    finally:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
