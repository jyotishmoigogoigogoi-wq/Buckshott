import os
import asyncio
import random
import logging
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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
    "load": "⟨ 𝘤𝘩𝘢𝘬-𝘤𝘩𝘢𝘬 ⟩",
    "bang": "𝘽 𝘼 𝙉 𝙂 !",
    "click": "· · · 𝘤𝘭𝘪𝘤𝘬 · · ·",
    "reload": "⟨ 𝘴𝘩𝘶𝘧𝘧𝘭𝘦 ⟩",
    "tension": ". . .",
    "death": "☠️ 𝙁 𝘼 𝙏 𝘼 𝙇 𝙄 𝙏 𝙔 ☠️"
}

HEART = "❤️"
DEAD_HEART = "🖤"
LIVE_SHELL = "🔴"
BLANK_SHELL = "⚪"
UNKNOWN_SHELL = "❓"


@app.route('/')
def health():
    return "🔫 BUCKSHOT ROULETTE BOT IS LIVE"


def run_flask():
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', int(os.environ.get("PORT", 10000)), app, threaded=True)
    server.serve_forever()


def get_hp_display(hp: int, max_hp: int = 3) -> str:
    return HEART * hp + DEAD_HEART * (max_hp - hp)


def generate_shells() -> tuple:
    live = random.randint(1, 4)
    blank = random.randint(1, 4)
    shells = ['L'] * live + ['B'] * blank
    random.shuffle(shells)
    return ''.join(shells), live, blank


# ═══════════════════════════════════════
#           WELCOME MESSAGE
# ═══════════════════════════════════════

def get_welcome_msg() -> str:
    return """
╔═══════════════════════════════════════╗
║                                       ║
║   🔫  𝐁𝐔𝐂𝐊𝐒𝐇𝐎𝐓  𝐑𝐎𝐔𝐋𝐄𝐓𝐓𝐄  🔫        ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   🎮  Welcome to Buckshot Roulette!   ║
║                                       ║
║   ─────────────────────────────       ║
║                                       ║
║   📜  RULES:                          ║
║   • Shotgun loaded with LIVE 🔴       ║
║     and BLANK ⚪ shells               ║
║                                       ║
║   • Shoot your opponent or            ║
║     shoot yourself!                   ║
║                                       ║
║   • BLANK on self = Extra turn! 🍀   ║
║                                       ║
║   • 3 HP depleted = Game Over! 💀    ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   🎯  HOW TO PLAY:                    ║
║   ─────────────────────────────       ║
║                                       ║
║   🤖  /buckshotpv                     ║
║       → Play vs AI (Private Chat)     ║
║                                       ║
║   👥  /buckshot                       ║
║       → Play vs Friend (Group Chat)   ║
║                                       ║
╚═══════════════════════════════════════╝
"""


# ═══════════════════════════════════════
#           GROUP LOBBY MESSAGES
# ═══════════════════════════════════════

def get_lobby_msg(players: list, max_players: int = 2) -> str:
    count = len(players)

    if count == 0:
        player_list = "   ⏳ Waiting for players..."
    elif count == 1:
        p1_name = f"@{players[0]['username']}" if players[0]['username'] else players[0]['name']
        player_list = f"   1️⃣ {p1_name}"
    else:
        p1_name = f"@{players[0]['username']}" if players[0]['username'] else players[0]['name']
        p2_name = f"@{players[1]['username']}" if players[1]['username'] else players[1]['name']
        player_list = f"   1️⃣ {p1_name}\n   2️⃣ {p2_name}"

    status_bar = "🟢" * count + "⚫" * (max_players - count)

    return f"""
╔═══════════════════════════════════════╗
║                                       ║
║   🔫  𝐁𝐔𝐂𝐊𝐒𝐇𝐎𝐓  𝐋𝐎𝐁𝐁𝐘  🔫            ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   👥  PLAYERS:  {count}/{max_players}                      ║
║   ─────────────────────────────       ║
║                                       ║
{player_list}
║                                       ║
║   {status_bar}                          ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   ⏳ Waiting for players to join...   ║
║                                       ║
║   👇 Click the button below to JOIN!  ║
║                                       ║
╚═══════════════════════════════════════╝
"""


def get_match_start_msg(p1: dict, p2: dict) -> str:
    p1_name = f"@{p1['username']}" if p1['username'] else p1['name']
    p2_name = f"@{p2['username']}" if p2['username'] else p2['name']

    return f"""
╔═══════════════════════════════════════╗
║                                       ║
║   ⚔️  𝐌𝐀𝐓𝐂𝐇 𝐅𝐎𝐔𝐍𝐃!  ⚔️               ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║        🔴  {p1_name[:12]:^12}            ║
║                                       ║
║              ⚔️ VS ⚔️                  ║
║                                       ║
║        🔵  {p2_name[:12]:^12}            ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║        {SFX['load']}             ║
║                                       ║
║     🔫 Loading the shotgun...         ║
║                                       ║
╚═══════════════════════════════════════╝
"""


# ═══════════════════════════════════════
#           GAME DISPLAY MESSAGES
# ═══════════════════════════════════════

def get_game_display(game: dict, is_group: bool = False) -> str:
    p1_hp = get_hp_display(game['p1_hp'])
    p2_hp = get_hp_display(game['p2_hp'])

    if is_group:
        p1_name = f"@{game['p1']['username']}" if game['p1']['username'] else game['p1']['name']
        p2_name = f"@{game['p2']['username']}" if game['p2']['username'] else game['p2']['name']
        p1_display = p1_name[:10]
        p2_display = p2_name[:10]
    else:
        p1_display = "YOU"
        p2_display = "DEALER"

    remaining = len(game['shells']) - game['shell_idx']
    shells_display = UNKNOWN_SHELL * min(remaining, 8)

    turn_name = p1_display if game['turn'] == 1 else p2_display
    turn_emoji = "🔴" if game['turn'] == 1 else "🔵" if is_group else "🤖"

    return f"""
╔═══════════════════════════════════════╗
║                                       ║
║   🔫  𝐁𝐔𝐂𝐊𝐒𝐇𝐎𝐓  𝐑𝐎𝐔𝐋𝐄𝐓𝐓𝐄  🔫        ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   {p1_hp}  {p1_display:^10}              ║
║                                       ║
║            ⚔️ VS ⚔️                    ║
║                                       ║
║   {p2_hp}  {p2_display:^10}              ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║         🔫 SHOTGUN                    ║
║   ┌─────────────────────────┐         ║
║   │  {shells_display:^23}│         ║
║   └─────────────────────────┘         ║
║                                       ║
║   Loaded:  {LIVE_SHELL} {game['live']:^2}  │  {BLANK_SHELL} {game['blank']:^2}        ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   {turn_emoji}  {turn_name}'s TURN                  ║
║                                       ║
╚═══════════════════════════════════════╝
"""


def get_shot_result(is_live: bool, shooter: str, target: str, is_self: bool) -> str:
    if is_live:
        if is_self:
            return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃   🔫 {shooter} shoots themselves...   ┃
┃                                       ┃
┃              {SFX['tension']}                 ┃
┃                                       ┃
┃          💥 {SFX['bang']} 💥            ┃
┃                                       ┃
┃         {LIVE_SHELL} IT WAS LIVE!              ┃
┃                                       ┃
┃       😵 DAMAGE TAKEN!                ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
        else:
            return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃   🔫 {shooter} shoots {target}!       ┃
┃                                       ┃
┃              {SFX['tension']}                 ┃
┃                                       ┃
┃          💥 {SFX['bang']} 💥            ┃
┃                                       ┃
┃         {LIVE_SHELL} IT WAS LIVE!              ┃
┃                                       ┃
┃       🎯 DIRECT HIT!                  ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
    else:
        if is_self:
            return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃   🔫 {shooter} shoots themselves...   ┃
┃                                       ┃
┃              {SFX['tension']}                 ┃
┃                                       ┃
┃           {SFX['click']}             ┃
┃                                       ┃
┃         {BLANK_SHELL} IT WAS BLANK!            ┃
┃                                       ┃
┃     🍀 LUCKY! SHOOT AGAIN!            ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
        else:
            return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃   🔫 {shooter} shoots {target}!       ┃
┃                                       ┃
┃              {SFX['tension']}                 ┃
┃                                       ┃
┃           {SFX['click']}             ┃
┃                                       ┃
┃         {BLANK_SHELL} IT WAS BLANK!            ┃
┃                                       ┃
┃       😮‍💨 {target} SURVIVES!           ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def get_reload_msg(live: int, blank: int) -> str:
    shells_visual = (LIVE_SHELL * live) + (BLANK_SHELL * blank)
    return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃          {SFX['load']}            ┃
┃                                       ┃
┃      🔫 RELOADING SHOTGUN...          ┃
┃                                       ┃
┃          {SFX['reload']}           ┃
┃                                       ┃
┃      {shells_visual}      ┃
┃                                       ┃
┃    {LIVE_SHELL} LIVE: {live}    {BLANK_SHELL} BLANK: {blank}           ┃
┃                                       ┃
┃          {SFX['reload']}           ┃
┃                                       ┃
┃      ❓ SHUFFLED & LOADED!            ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def get_game_over_msg(winner: str, loser: str) -> str:
    return f"""
╔═══════════════════════════════════════╗
║                                       ║
║          {SFX['death']}          ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║           𝐆𝐀𝐌𝐄  𝐎𝐕𝐄𝐑!                 ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║     🏆  WINNER:  {winner[:15]:^15}    ║
║                                       ║
║     💀  LOSER:   {loser[:15]:^15}    ║
║                                       ║
╠═══════════════════════════════════════╣
║                                       ║
║   🎉  Congratulations {winner[:10]}!   ║
║                                       ║
╚═══════════════════════════════════════╝
"""


def get_ai_thinking_msg() -> str:
    return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                       ┃
┃        🤖 DEALER'S TURN...            ┃
┃                                       ┃
┃              {SFX['tension']}                 ┃
┃                                       ┃
┃      🔫 Dealer is thinking...         ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


# ═══════════════════════════════════════
#               KEYBOARDS
# ═══════════════════════════════════════

def get_private_game_kb(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 SHOOT DEALER", callback_data=f"pv_dealer_{game_id}")],
        [InlineKeyboardButton("🔫 SHOOT YOURSELF", callback_data=f"pv_self_{game_id}")],
    ])


def get_group_game_kb(chat_id: str, p1_id: int, p2_id: int, current_turn_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 SHOOT OPPONENT", callback_data=f"gp_opp_{chat_id}_{p1_id}_{p2_id}_{current_turn_id}")],
        [InlineKeyboardButton("🔫 SHOOT YOURSELF", callback_data=f"gp_self_{chat_id}_{p1_id}_{p2_id}_{current_turn_id}")],
    ])


def get_lobby_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 JOIN GAME", callback_data=f"join_{chat_id}")]
    ])


def get_play_again_kb(is_private: bool) -> InlineKeyboardMarkup:
    if is_private:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 PLAY AGAIN", callback_data="play_again_pv")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 PLAY AGAIN", callback_data="play_again_gp")]
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
            "❌ This command only works in PRIVATE CHAT!\n\n"
            "👥 Want to play with friends? Use /buckshot in a group!"
        )
        return

    user = update.effective_user
    user_id = str(user.id)

    # Check if already playing
    if user_id in private_games and private_games[user_id].get('status') == 'playing':
        await update.message.reply_text(
            "⚠️ You already have an active game!"
        )
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

    # Show reload
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
            "❌ This command only works in GROUP CHAT!\n\n"
            "🤖 Want to play vs AI? Use /buckshotpv here!"
        )
        return

    chat_id = str(update.effective_chat.id)

    # Check if game already running
    if chat_id in group_games:
        status = group_games[chat_id].get('status')
        if status == 'waiting' or status == 'playing':
            await update.message.reply_text(
                "⚠️ A game is already in progress!\n"
                "⏳ Please wait for it to finish."
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
    query = update.callback_query
    data = query.data
    user = query.from_user

    # ─────────────────────────────────
    # JOIN GROUP GAME
    # ─────────────────────────────────
    if data.startswith("join_"):
        chat_id = data.split("_")[1]

        if chat_id not in group_games:
            await query.answer("❌ Game not found!", show_alert=True)
            return

        game = group_games[chat_id]

        if game['status'] != 'waiting':
            await query.answer("❌ Game already started!", show_alert=True)
            return

        # Check if already joined
        for p in game['players']:
            if p['id'] == user.id:
                await query.answer("⚠️ You have already joined!", show_alert=True)
                return

        # Check if full
        if len(game['players']) >= 2:
            await query.answer("❌ Lobby is full!", show_alert=True)
            return

        # Add player
        game['players'].append({
            'id': user.id,
            'username': user.username,
            'name': user.first_name or "Player2"
        })

        await query.answer("✅ You joined the game!")

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
            await query.answer("❌ This is not your game!", show_alert=True)
            return

        if user_id not in private_games:
            await query.answer("❌ Game not found!", show_alert=True)
            return

        game = private_games[user_id]

        if game['turn'] != 1:
            await query.answer("⏳ Please wait for your turn!", show_alert=True)
            return

        await process_private_shot(query, user_id, target="dealer")
        return

    # ─────────────────────────────────
    # PRIVATE GAME - SHOOT SELF
    # ─────────────────────────────────
    if data.startswith("pv_self_"):
        user_id = data.split("_")[2]

        if user_id != str(user.id):
            await query.answer("❌ This is not your game!", show_alert=True)
            return

        if user_id not in private_games:
            await query.answer("❌ Game not found!", show_alert=True)
            return

        game = private_games[user_id]

        if game['turn'] != 1:
            await query.answer("⏳ Please wait for your turn!", show_alert=True)
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
            await query.answer("❌ You are not part of this game!", show_alert=True)
            return

        # Check if it's their turn
        if user.id != current_turn_id:
            await query.answer("⏳ Kindly wait for your turn!", show_alert=True)
            return

        if chat_id not in group_games:
            await query.answer("❌ Game not found!", show_alert=True)
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
            await query.answer("❌ You are not part of this game!", show_alert=True)
            return

        # Check if it's their turn
        if user.id != current_turn_id:
            await query.answer("⏳ Kindly wait for your turn!", show_alert=True)
            return

        if chat_id not in group_games:
            await query.answer("❌ Game not found!", show_alert=True)
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
        await query.answer("👆 Send /buckshot to start a new game!", show_alert=True)
        return

    await query.answer()


# ═══════════════════════════════════════
#          GAME LOGIC - PRIVATE
# ═══════════════════════════════════════

async def process_private_shot(query, user_id: str, target: str):
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
        shooter = "YOU"
        target_name = "DEALER"
        if is_live:
            game['p2_hp'] -= 1
        game['turn'] = 2
    else:
        shooter = "YOU"
        target_name = "self"
        if is_live:
            game['p1_hp'] -= 1
            game['turn'] = 2
        else:
            extra_turn = True

    # Show result
    result_msg = get_shot_result(is_live, shooter, target_name, target == "self")
    await query.edit_message_text(result_msg)
    await asyncio.sleep(2)

    # Check game over
    if game['p1_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg("DEALER 🤖", "YOU 😵")
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
        return

    if game['p2_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg("YOU 👑", "DEALER 🤖")
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
        game_display = get_game_display(game, is_group=False)
        game_display += "\n\n🍀 LUCKY! Shoot again!"
        await query.edit_message_text(game_display, reply_markup=get_private_game_kb(user_id))
    else:
        # AI Turn
        await process_ai_turn(query, user_id)


async def process_ai_turn(query, user_id: str):
    game = private_games[user_id]

    while game['turn'] == 2 and game['status'] == 'playing':
        # AI thinking
        await query.edit_message_text(get_ai_thinking_msg())
        await asyncio.sleep(1.5)

        # AI decision
        remaining = len(game['shells']) - game['shell_idx']
        live_ratio = game['live'] / remaining if remaining > 0 else 0

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
            game['turn'] = 1
            target_name = "YOU"
        else:
            if is_live:
                game['p2_hp'] -= 1
                game['turn'] = 1
            else:
                extra_turn = True
            target_name = "self"

        # Show result
        result_msg = get_shot_result(is_live, "DEALER", target_name, ai_target == "self")
        await query.edit_message_text(result_msg)
        await asyncio.sleep(2)

        # Check game over
        if game['p1_hp'] <= 0:
            game['status'] = 'finished'
            game_over = get_game_over_msg("DEALER 🤖", "YOU 😵")
            await query.edit_message_text(game_over, reply_markup=get_play_again_kb(True))
            return

        if game['p2_hp'] <= 0:
            game['status'] = 'finished'
            game_over = get_game_over_msg("YOU 👑", "DEALER 🤖")
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

        if not extra_turn:
            break

    # Player's turn
    if game['status'] == 'playing':
        game_display = get_game_display(game, is_group=False)
        await query.edit_message_text(game_display, reply_markup=get_private_game_kb(user_id))


# ═══════════════════════════════════════
#          GAME LOGIC - GROUP
# ═══════════════════════════════════════

async def process_group_shot(query, chat_id: str, shooter_id: int, target: str):
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
        game['turn'] = 2 if game['turn'] == 1 else 1
        result_msg = get_shot_result(is_live, shooter_name[:10], opponent_name[:10], False)
    else:
        if is_live:
            game[shooter_hp_key] -= 1
            game['turn'] = 2 if game['turn'] == 1 else 1
        else:
            extra_turn = True
        result_msg = get_shot_result(is_live, shooter_name[:10], "self", True)

    # Show result
    await query.edit_message_text(result_msg)
    await asyncio.sleep(2)

    # Check game over
    p1_name = f"@{game['p1']['username']}" if game['p1']['username'] else game['p1']['name']
    p2_name = f"@{game['p2']['username']}" if game['p2']['username'] else game['p2']['name']

    if game['p1_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg(p2_name + " 👑", p1_name + " 💀")
        await query.edit_message_text(game_over, reply_markup=get_play_again_kb(False))
        del group_games[chat_id]
        return

    if game['p2_hp'] <= 0:
        game['status'] = 'finished'
        game_over = get_game_over_msg(p1_name + " 👑", p2_name + " 💀")
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

    # Show game
    game_display = get_game_display(game, is_group=True)

    if extra_turn:
        game_display += f"\n\n🍀 {shooter_name} gets another shot!"

    current_turn_id = game['p1']['id'] if game['turn'] == 1 else game['p2']['id']
    await query.edit_message_text(
        game_display, 
        reply_markup=get_group_game_kb(chat_id, game['p1']['id'], game['p2']['id'], current_turn_id)
    )


# ═══════════════════════════════════════
#               MAIN
# ═══════════════════════════════════════

async def main():
    logger.info("🔫 Starting Buckshot Roulette Bot...")

    bot = Application.builder().token(TOKEN).build()

    # Commands
    bot.add_handler(CommandHandler("start", start_cmd))
    bot.add_handler(CommandHandler("buckshotpv", buckshotpv_cmd))
    bot.add_handler(CommandHandler("buckshot", buckshot_cmd))

    # Callbacks
    bot.add_handler(CallbackQueryHandler(callback_handler))

    # Flask
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
