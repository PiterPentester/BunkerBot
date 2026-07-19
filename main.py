# bot.py
import os
import asyncio
import logging
import secrets
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from game_data import APOCALYPSES, generate_character, evaluate_survival

load_dotenv()
API_TOKEN = os.getenv("TG_API_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ROOMS = {}

class RoomCreation(StatesGroup):
    waiting_for_players = State()
    waiting_for_seats = State()

LABELS = {
    "gender": "👤 Стать",
    "age": "⏳ Вік",
    "health": "🧬 Здоров'я",
    "profession": "💼 Професія",
    "baggage": "🎒 Багаж",
    "trait": "🧠 Характер",
    "hobby": "🎨 Хобі"
}

def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Створити гру 🎲", callback_data="init_room")
    return builder.as_markup()

def get_reveal_keyboard(room_id: str, character: dict, is_alive: bool = True):
    """Генерує кнопки відкриття характеристик для особистої картки"""
    builder = InlineKeyboardBuilder()
    if is_alive:
        for key, label in LABELS.items():
            if key not in character["opened"]:
                builder.button(text=f"Відкрити {label}", callback_data=f"rev:{room_id}:{key}")
        builder.adjust(2)
        # Кнопка голосування тепер знаходиться тут — під особистою карткою кожного живого гравця
        builder.row(types.InlineKeyboardButton(text="🗳️ Почати голосування раунду", callback_data=f"init_vote:{room_id}"))
    return builder.as_markup()

def format_personal_card(character: dict):
    """Формує текст для особистої картки гравця"""
    return (
        f"📌 **ТВОЯ ЗАКРІПЛЕНА КАРТКА ПЕРСОНАЖА**\n"
        f"_(Ніхто інший не бачить цей текст, поки ти не відкриєш характеристики)_\n\n"
        f"• Стать: {character['gender']}\n"
        f"• Вік: {character['age']}\n"
        f"• Здоров'я: {character['health']}\n"
        f"• Професія: {character['profession']}\n"
        f"• Багаж: {character['baggage']}\n"
        f"• Характер: {character['trait']}\n"
        f"• Хобі: {character['hobby']}\n"
    )

async def update_live_dashboards(room_id: str):
    """Оновлює чисте Загальне табло без кнопок дій у всіх учасників"""
    room = ROOMS.get(room_id)
    if not room:
        return

    apoc = APOCALYPSES[room["apocalypse"]]
    alive_players = {k: v for k, v in room["players"].items() if not v.get("is_spectator", False)}

    dash_text = (
        f"🌋 **АПОКАЛІПСИС: {room['apocalypse']}**\n"
        f"_{apoc['desc']}_\n\n"
        f"📊 **СТАН КІМНАТИ (Раунд {room['round']}):**\n"
        f"🔒 Місць у бункері: {room['bunker_seats']} | 👥 Живих гравців: {len(alive_players)}\n"
        f"-----------------------------------------\n"
    )

    for p_id, p_data in alive_players.items():
        dash_text += f"👤 **{p_data['name']}**:\n"
        char = p_data["character"]
        for key, label in LABELS.items():
            if key in char["opened"]:
                dash_text += f" ├ {label}: `{char[key]}`\n"
            else:
                dash_text += f" ├ {label}: _[Приховано]_\n"
        dash_text += "\n"

    for p_id, p_data in room["players"].items():
        text_to_send = dash_text if not p_data.get("is_spectator", False) else "👁️ **Режим спостерігача**\n\n" + dash_text
        msg_id = p_data.get("dash_message_id")

        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=p_id,
                    message_id=msg_id,
                    text=text_to_send,
                    reply_markup=None, # Жодних кнопок під табло
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            sent_msg = await bot.send_message(p_id, text_to_send, reply_markup=None, parse_mode="Markdown")
            p_data["dash_message_id"] = sent_msg.message_id

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    args = command.args

    if args:
        room_id = args
        if room_id in ROOMS:
            room = ROOMS[room_id]
            if room["status"] != "waiting":
                await message.answer("❌ Гра в цій кімнаті вже розпочалася.")
                return
            if len(room["players"]) >= room["max_players"]:
                await message.answer("❌ Кімната вже заповнена.")
                return

            user_id = message.from_user.id
            if user_id not in room["players"]:
                room["players"][user_id] = {
                    "name": message.from_user.full_name,
                    "character": generate_character(),
                    "votes": 0,
                    "voted": False,
                    "dash_message_id": None,
                    "card_message_id": None,
                    "is_spectator": False
                }
                await message.answer(f"✅ Ви приєдналися до гри!\nОчікуйте старту.\nГравців у лобі: {len(room['players'])}/{room['max_players']}")
                await bot.send_message(room["host_id"], f"➕ Гравець {message.from_user.full_name} приєднався до кімнати!")
            else:
                await message.answer("🔔 Ви вже знаходитесь у цій кімнаті.")
        else:
            await message.answer("❌ Кімнату не знайдено.")
        return

    await message.answer(
        "Привіт! Я бот для настільної гри **Бункер**.\nНатисни кнопку нижче, щоб створити нову ігрову кімнату.",
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "init_room")
async def init_room_creation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RoomCreation.waiting_for_players)
    await callback.message.answer("Введіть кількість гравців для матчу (від 3 до 20):")

@dp.message(RoomCreation.waiting_for_players)
async def process_players_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (3 <= int(message.text) <= 20):
        await message.answer("Будь ласка, введіть число від 3 до 20:")
        return
    await state.update_data(max_players=int(message.text))
    await state.set_state(RoomCreation.waiting_for_seats)
    await message.answer("Тепер введіть кількість місць у бункері (від 2 до 10, але менше ніж кількість гравців):")

@dp.message(RoomCreation.waiting_for_seats)
async def process_seats_count(message: types.Message, state: FSMContext):
    data = await state.get_data()
    max_players = data["max_players"]

    if not message.text.isdigit() or not (2 <= int(message.text) <= 10) or int(message.text) >= max_players:
        await message.answer(f"Некоректно. Введіть число від 2 до 10 (має бути меншим за {max_players}):")
        return

    bunker_seats = int(message.text)
    await state.clear()

    room_id = secrets.token_hex(4)
    apocalypse_name = secrets.choice(list(APOCALYPSES.keys()))

    ROOMS[room_id] = {
        "host_id": message.from_user.id,
        "max_players": max_players,
        "bunker_seats": bunker_seats,
        "apocalypse": apocalypse_name,
        "players": {
            message.from_user.id: {
                "name": message.from_user.full_name,
                "character": generate_character(),
                "votes": 0,
                "voted": False,
                "dash_message_id": None,
                "card_message_id": None,
                "is_spectator": False
            }
        },
        "status": "waiting",
        "round": 1
    }

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={room_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text="Запустити гру 🚀", callback_data=f"start_game:{room_id}")

    await message.answer(
        f"🏰 **Кімнату створено!**\n\n"
        f"🌋 Катастрофа: **{apocalypse_name}**\n"
        f"👥 Макс. гравців: {max_players}\n"
        f"🔒 Місць в бункері: {bunker_seats}\n\n"
        f"🔗 Надішліть це посилання іншим гравцям для входу:\n`{invite_link}`",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("start_game:"))
async def start_game(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)

    if not room or room["host_id"] != callback.from_user.id:
        await callback.answer("Лише творець кімнати може запустити гру.", show_alert=True)
        return

    if len(room["players"]) < 2:
        await callback.answer("Необхідно мінімум 2 гравці для старту логіки гри!", show_alert=True)
        return

    room["status"] = "playing"
    await callback.message.edit_text("🎮 Гра розпочалася! Картки дій закріплено у ваших чатах.")

    # Надсилаємо та закріплюємо картки з кнопками під ними
    for player_id, p_data in room["players"].items():
        char = p_data["character"]
        personal_card_text = format_personal_card(char)
        reveal_kb = get_reveal_keyboard(room_id, char)

        pinned_msg = await bot.send_message(player_id, personal_card_text, reply_markup=reveal_kb, parse_mode="Markdown")
        p_data["card_message_id"] = pinned_msg.message_id
        try:
            await bot.pin_chat_message(chat_id=player_id, message_id=pinned_msg.message_id, disable_notification=True)
        except Exception:
            pass

    await update_live_dashboards(room_id)

@dp.callback_query(F.data.startswith("rev:"))
async def process_reveal(callback: types.CallbackQuery):
    _, room_id, trait_key = callback.data.split(":")
    room = ROOMS.get(room_id)

    if not room or callback.from_user.id not in room["players"]:
        await callback.answer("Ви не берете участі в цій грі.")
        return

    player = room["players"][callback.from_user.id]

    if player.get("is_spectator", False):
        await callback.answer("Глядачі не можуть відкривати характеристики.")
        return

    char = player["character"]
    if trait_key in char["opened"]:
        await callback.answer("Ця характеристика вже відкрита!", show_alert=True)
        return

    char["opened"].append(trait_key)
    await callback.answer("Характеристику розкрито!")

    # Оновлюємо кнопки під особистою карткою (прибираємо ту, яку вже натиснули)
    new_reveal_kb = get_reveal_keyboard(room_id, char)
    await callback.message.edit_reply_markup(reply_markup=new_reveal_kb)

    # Тихо оновлюємо глобальне табло для всіх учасників
    await update_live_dashboards(room_id)

@dp.callback_query(F.data.startswith("init_vote:"))
async def init_vote(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)

    if not room:
        await callback.answer("Гру не знайдено.")
        return

    user_id = callback.from_user.id
    if user_id not in room["players"] or room["players"][user_id].get("is_spectator", False):
        await callback.answer("Тільки живі гравці можуть запускати голосування.", show_alert=True)
        return

    if room["status"] == "voting":
        await callback.answer("Голосування вже триває.", show_alert=True)
        return

    room["status"] = "voting"
    alive_players = {k: v for k, v in room["players"].items() if not v.get("is_spectator", False)}

    for p_id in room["players"].keys():
        room["players"][p_id]["votes"] = 0
        room["players"][p_id]["voted"] = False

    for p_id, p_data in alive_players.items():
        builder = InlineKeyboardBuilder()
        for target_id, target_data in alive_players.items():
            if target_id != p_id:
                builder.button(text=target_data["name"], callback_data=f"vote:{room_id}:{target_id}")
        builder.adjust(1)

        try:
            await bot.send_message(p_id, f"🗳️ **РАУНД {room['round']}: ГОЛОСУВАННЯ**\nОберіть, хто має залишитися за дверима бункера:", reply_markup=builder.as_markup(), parse_mode="Markdown")
        except Exception:
            pass

@dp.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: types.CallbackQuery):
    _, room_id, target_id = callback.data.split(":")
    target_id = int(target_id)
    room = ROOMS.get(room_id)

    if not room or room["status"] != "voting":
        await callback.answer("Голосування не активне.")
        return

    voter_id = callback.from_user.id
    if voter_id not in room["players"] or room["players"][voter_id].get("is_spectator", False):
        await callback.answer("Ви не можете голосувати.")
        return

    if room["players"][voter_id]["voted"]:
        await callback.answer("Ви вже проголосували!", show_alert=True)
        return

    room["players"][voter_id]["voted"] = True
    room["players"][target_id]["votes"] += 1

    await callback.message.edit_text(f"👌 Голос проти гравця {room['players'][target_id]['name']} зараховано.")

    alive_players = {k: v for k, v in room["players"].items() if not v.get("is_spectator", False)}
    all_voted = all(p["voted"] for p in alive_players.values())

    if all_voted:
        kicked_id = max(alive_players, key=lambda k: alive_players[k]["votes"])
        kicked_name = room["players"][kicked_id]["name"]

        room["players"][kicked_id]["is_spectator"] = True

        for p_id in room["players"].keys():
            await bot.send_message(p_id, f"🚪 Гравець **{kicked_name}** вибуває за результатами голосування та стає спостерігачем. 👁️🔴", parse_mode="Markdown")

        try:
            await bot.unpin_chat_message(chat_id=kicked_id)
            # Прибираємо інтерфейс кнопок під особистою карткою у того, хто вибув
            await bot.edit_message_reply_markup(chat_id=kicked_id, message_id=room["players"][kicked_id]["card_message_id"], reply_markup=None)
        except Exception:
            pass

        await update_live_dashboards(room_id)

        current_alive = [v for v in room["players"].values() if not v.get("is_spectator", False)]

        if len(current_alive) <= room["bunker_seats"]:
            success, final_msg = evaluate_survival(room["apocalypse"], current_alive)
            survivor_names = ", ".join([p["name"] for p in current_alive])

            for p_id in room["players"].keys():
                try:
                    await bot.send_message(p_id, f"🏁 **ФІНАЛ ГРИ! ДВЕРІ ЗАЧИНЕНО**\n\n👥 До бункеру потрапили: **{survivor_names}**\n\n{final_msg}", parse_mode="Markdown")
                    await bot.send_message(p_id, "Бажаєте зіграти ще раз? Створіть нову кімнату нижче:", reply_markup=get_start_keyboard())
                except Exception:
                    pass

            del ROOMS[room_id]
        else:
            room["round"] += 1
            room["status"] = "playing"

            # Після зміни раунду оновлюємо інтерфейс кнопок під картками УСІХ живих гравців (щоб з'явилася кнопка голосування на новий раунд)
            for p_id, p_data in room["players"].items():
                if not p_data.get("is_spectator", False):
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=p_id,
                            message_id=p_data["card_message_id"],
                            reply_markup=get_reveal_keyboard(room_id, p_data["character"])
                        )
                    except Exception:
                        pass

            await update_live_dashboards(room_id)

            for p_id, p_data in room["players"].items():
                if not p_data.get("is_spectator", False):
                    await bot.send_message(p_id, f"🔄 **Розпочався раунд {room['round']}.**\nОбговоріть ситуацію та відкрийте нову характеристику за допомогою кнопок під вашою закріпленою карткою персонажа.")

async def main():
    print("BunkerBot успішно запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
