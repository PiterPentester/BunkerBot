import time
import asyncio
import html
import logging
import os
import random
import secrets
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from game_data import (
    APOCALYPSES,
    FACTS,
    HOBBIES,
    LABELS,
    PROFESSIONS,
    TRAITS,
    evaluate_survival,
    generate_bunker_info,
    generate_character,
)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
API_TOKEN = os.getenv("TG_API_TOKEN")

if not API_TOKEN:
    logger.warning(
        "TG_API_TOKEN не знайдено в змінних середовища! Перевірте файл .env."
    )

ROOMS: Dict[str, dict] = {}


class CreateRoomState(StatesGroup):
    waiting_for_total_players = State()
    waiting_for_bunker_seats = State()
    waiting_for_rematch_seats = State()


bot = Bot(token=API_TOKEN if API_TOKEN else "123456:DummyToken")
dp = Dispatcher(storage=MemoryStorage())

TARGETED_ACTIONS = {
    "SWAP_BAG",
    "SWAP_HEALTH",
    "SWAP_PROF",
    "SWAP_HOBBY",
    "INFECT",
    "STEAL_BAG",
    "CHECK",
    "SILENCE",
    "REVEAL_FACT",
    "CURE_OTHER",
    "SWAP_TRAIT",
    "SWAP_FACT",
    "COPY_BAG",
    "MAKE_SICK",
    "QUARANTINE",
    "REROLL_OTHER_PROF",
    "REVEAL_TARGET_ALL",
    "STEAL_ACTION",
    "LINK_SURVIVAL",
    "FORCE_VOTE_TARGET",
}


def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Створити гру 🎲", callback_data="init_room")
    return builder.as_markup()


def get_rematch_lobby_keyboard(room_id: str, host_id: int):
    builder = InlineKeyboardBuilder()
    room = ROOMS.get(room_id)
    if not room:
        return builder.as_markup()

    # Кнопки видалення гравців (доступні лише хосту)
    for p_id, p_data in room["players"].items():
        if p_id != host_id:  # Хост не може видалити сам себе
            builder.button(
                text=f"❌ Видалити: {p_data['name']}",
                callback_data=f"kick_p:{room_id}:{p_id}",
            )

    builder.button(
        text="⚙️ Змінити місця в бункері", callback_data=f"change_seats:{room_id}"
    )
    builder.button(
        text="🚀 Розпочати нову гру", callback_data=f"restart_game:{room_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_new_game_keyboard(room_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Нова гра з цим складом", callback_data=f"init_rematch:{room_id}"
    )
    builder.button(text="🎲 Створити нову кімнату", callback_data="init_room")
    builder.adjust(1)
    return builder.as_markup()


@dp.callback_query(F.data.startswith("init_rematch:"))
async def init_rematch(callback: types.CallbackQuery):
    old_room_id = callback.data.split(":")[1]
    old_room = ROOMS.get(old_room_id)

    if not old_room:
        await callback.answer("Дані попередньої гри вже застаріли.", show_alert=True)
        return

    user_id = callback.from_user.id
    if user_id != old_room["host_id"]:
        await callback.answer(
            "Лише хост попередньої гри може розпочати рематч!", show_alert=True
        )
        return

    # Створюємо нову кімнату, зберігаючи список гравців
    new_room_id = secrets.token_hex(4)
    apocalypse_name = secrets.choice(list(APOCALYPSES.keys()))
    bunker_info = generate_bunker_info()

    new_players = {}
    for p_id, p_data in old_room["players"].items():
        new_players[p_id] = {
            "name": p_data["name"],
            "character": generate_character(),  # Генерація нових ролей
            "votes": 0,
            "voted_against": [],
            "voted": False,
            "dash_message_id": None,
            "card_message_id": None,
            "is_spectator": False,
            "is_ghost_voter": False,
        }

    ROOMS[new_room_id] = {
        "host_id": user_id,
        "max_players": len(new_players),
        "bunker_seats": min(
            old_room["bunker_seats"],
            len(new_players) - 1 if len(new_players) > 1 else 1,
        ),
        "apocalypse": apocalypse_name,
        "bunker_info": bunker_info,
        "players": new_players,
        "status": "waiting",
        "round": 1,
        "last_activity": time.time(),
        "evaluating_round": False,
    }

    # Очищуємо стару кімнату
    ROOMS.pop(old_room_id, None)

    await render_rematch_lobby(new_room_id)


async def render_rematch_lobby(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        return

    p_list = "\n".join(
        [f"• <b>{html.escape(p['name'])}</b>" for p in room["players"].values()]
    )
    text = (
        f"🔄 <b>ПІДГОТОВКА ДО НОВОЇ ГРИ</b>\n\n"
        f"🌋 Катастрофа: <b>{html.escape(room['apocalypse'])}</b>\n"
        f"👥 Гравців: <b>{len(room['players'])}</b>\n"
        f"🔒 Місць у бункері: <b>{room['bunker_seats']}</b>\n\n"
        f"<b>Склад гравців:</b>\n{p_list}\n\n"
        f"<i>Хост може видалити зайвих гравців або змінити кількість місць у бункері перед стартом.</i>"
    )

    tasks = [
        bot.send_message(
            p_id,
            text,
            reply_markup=get_rematch_lobby_keyboard(room_id, room["host_id"])
            if p_id == room["host_id"]
            else None,
            parse_mode="HTML",
        )
        for p_id in room["players"].keys()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


@dp.callback_query(F.data.startswith("kick_p:"))
async def kick_player(callback: types.CallbackQuery):
    _, room_id, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)
    room = ROOMS.get(room_id)

    if not room or callback.from_user.id != room["host_id"]:
        await callback.answer("Дія недоступна.", show_alert=True)
        return

    if target_id in room["players"]:
        kicked_name = room["players"][target_id]["name"]
        del room["players"][target_id]
        room["max_players"] = len(room["players"])

        # Коригуємо кількість місць, якщо гравців стало менше за кількість місць
        if room["bunker_seats"] >= len(room["players"]):
            room["bunker_seats"] = max(1, len(room["players"]) - 1)

        await callback.answer(f"Гравця {kicked_name} вилучено з гри.")

        # Повідомляємо кикнутого гравця
        try:
            await bot.send_message(
                target_id, "❌ Вас було вилучено з наступної гри хостом."
            )
        except Exception:
            pass

        await render_rematch_lobby(room_id)


@dp.callback_query(F.data.startswith("change_seats:"))
async def change_seats_prompt(callback: types.CallbackQuery, state: FSMContext):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)

    if not room or callback.from_user.id != room["host_id"]:
        await callback.answer("Дія недоступна.", show_alert=True)
        return

    await state.update_data(rematch_room_id=room_id)
    await state.set_state(CreateRoomState.waiting_for_rematch_seats)
    await callback.message.answer(
        f"🔒 Введіть нову кількість місць у бункері (від 1 до {len(room['players']) - 1}):"
    )


@dp.message(CreateRoomState.waiting_for_rematch_seats)
async def process_rematch_seats(message: types.Message, state: FSMContext):
    data = await state.get_data()
    room_id = data.get("rematch_room_id")
    room = ROOMS.get(room_id)

    if not room:
        await state.clear()
        await message.answer("❌ Кімнату не знайдено.")
        return

    max_allowed = len(room["players"]) - 1
    if not message.text.isdigit() or not (1 <= int(message.text) <= max_allowed):
        await message.answer(f"❌ Число має бути від 1 до {max_allowed}.")
        return

    room["bunker_seats"] = int(message.text)
    await state.clear()
    await message.answer("✅ Кількість місць оновлено.")
    await render_rematch_lobby(room_id)


@dp.callback_query(F.data.startswith("restart_game:"))
async def restart_game(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)

    if not room or callback.from_user.id != room["host_id"]:
        await callback.answer("Лише хост може зародити гру!", show_alert=True)
        return

    if len(room["players"]) < 2:
        await callback.answer(
            "Для старту гри потрібно мінімум 2 гравці!", show_alert=True
        )
        return

    room["status"] = "playing"

    for player_id, p_data in room["players"].items():
        char = p_data["character"]
        pinned_msg = await bot.send_message(
            player_id,
            format_personal_card(char),
            reply_markup=get_reveal_keyboard(room_id, char),
            parse_mode="HTML",
        )
        p_data["card_message_id"] = pinned_msg.message_id

    await update_live_dashboards(room_id)


def get_reveal_keyboard(room_id: str, character: dict, is_alive: bool = True):
    builder = InlineKeyboardBuilder()
    if is_alive:
        for key, label in LABELS.items():
            if key not in character["opened"]:
                builder.button(
                    text=f"Відкрити {label}", callback_data=f"rev:{room_id}:{key}"
                )
        builder.adjust(2)

        if not character.get("action_used", False):
            act = character["action"]
            builder.row(
                types.InlineKeyboardButton(
                    text=f"⚡ Застосувати дію: {act['name']}",
                    callback_data=f"use_act:{room_id}",
                )
            )

        builder.row(
            types.InlineKeyboardButton(
                text="🗳️ Почати голосування раунду", callback_data=f"init_vote:{room_id}"
            )
        )
    return builder.as_markup()


def format_personal_card(character: dict) -> str:
    act = character["action"]
    cond = character["condition"]
    return (
        f"📌 <b>ТВОЯ ЗАКРІПЛЕНА КАРТКА ПЕРСОНАЖА</b>\n"
        f"<i>(Прихована від інших гравців)</i>\n\n"
        f"• Стать: {html.escape(str(character['gender']))}\n"
        f"• Вік: {character['age']}\n"
        f"• Здоров'я: {html.escape(str(character['health']))}\n"
        f"• Професія: {html.escape(str(character['profession']))}\n"
        f"• Багаж: {html.escape(str(character['baggage']))}\n"
        f"• Характер: {html.escape(str(character['trait']))}\n"
        f"• Хобі: {html.escape(str(character['hobby']))}\n"
        f"• 📜 Факт: {html.escape(str(character['fact']))}\n\n"
        f"⚡ <b>Твоя дія:</b> {html.escape(act['name'])}\n<i>{html.escape(act['desc'])}</i>\n\n"
        f"⚠️ <b>Твій заповіт (умова вибування):</b>\n<i>{html.escape(cond['desc'])}</i>\n"
    )


async def update_live_dashboards(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        return

    apoc = APOCALYPSES[room["apocalypse"]]
    bunker = room["bunker_info"]
    alive_players = {
        k: v for k, v in room["players"].items() if not v.get("is_spectator", False)
    }

    dash_text = (
        f"🌋 <b>АПОКАЛІПСИС: {html.escape(room['apocalypse'])}</b>\n"
        f"<i>{html.escape(apoc['desc'])}</i>\n\n"
        f"🏰 <b>ХАРАКТЕРИСТИКИ БУНКЕРА:</b>\n"
        f"⏳ Час перебування: <b>{bunker['years']} років</b>\n"
        f"🛠️ Стан: <b>{html.escape(bunker['condition'])}</b> (Міцність: {bunker['durability']}%)\n"
        f"🍞 Ресурси: <b>{html.escape(bunker['resources'])}</b>\n\n"
        f"📊 <b>СТАН КІМНАТИ (Раунд {room['round']}):</b>\n"
        f"🔒 Місць у бункері: {room['bunker_seats']} | 👥 Приєдналися: {len(room['players'])}/{room['max_players']}\n"
        f"-----------------------------------------\n"
    )

    for p_id, p_data in alive_players.items():
        p_name = html.escape(p_data["name"])
        dash_text += f"👤 <b>{p_name}</b>"
        if p_data["character"].get("is_protected"):
            dash_text += " 🛡️"
        if p_data["character"].get("is_silenced"):
            dash_text += " 🔇"
        dash_text += ":\n"

        char = p_data["character"]
        for key, label in LABELS.items():
            if key in char["opened"]:
                dash_text += f" ├ {label}: <code>{html.escape(str(char[key]))}</code>\n"
            else:
                dash_text += f" ├ {label}: <i>[Приховано]</i>\n"
        dash_text += "\n"

    async def _update_single_player(p_id: int, p_data: dict):
        text_to_send = (
            dash_text
            if not p_data.get("is_spectator", False)
            else "👁️ <b>Режим спостерігача</b>\n\n" + dash_text
        )
        msg_id = p_data.get("dash_message_id")

        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=p_id,
                    message_id=msg_id,
                    text=text_to_send,
                    parse_mode="HTML",
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e).lower():
                    try:
                        sent_msg = await bot.send_message(
                            p_id, text_to_send, parse_mode="HTML"
                        )
                        p_data["dash_message_id"] = sent_msg.message_id
                    except Exception:
                        pass
            except Exception:
                pass
        else:
            try:
                sent_msg = await bot.send_message(p_id, text_to_send, parse_mode="HTML")
                p_data["dash_message_id"] = sent_msg.message_id
            except Exception:
                pass

    tasks = [
        _update_single_player(p_id, p_data) for p_id, p_data in room["players"].items()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    args = command.args

    if args and args in ROOMS:
        room = ROOMS[args]
        if room["status"] != "waiting":
            await message.answer("❌ Гра вже розпочалася.")
            return

        if len(room["players"]) >= room["max_players"]:
            await message.answer("❌ У цій кімнаті вже немає вільних місць!")
            return

        user_id = message.from_user.id
        if user_id not in room["players"]:
            room["players"][user_id] = {
                "name": message.from_user.full_name,
                "character": generate_character(),
                "votes": 0,
                "voted_against": [],
                "voted": False,
                "dash_message_id": None,
                "card_message_id": None,
                "is_spectator": False,
                "is_ghost_voter": False,
            }
            await message.answer(
                f"✅ Ви приєдналися до гри ({len(room['players'])}/{room['max_players']})!"
            )
            await bot.send_message(
                room["host_id"],
                f"➕ Гравець <b>{html.escape(message.from_user.full_name)}</b> приєднався! ({len(room['players'])}/{room['max_players']})",
                parse_mode="HTML",
            )
        return

    await message.answer(
        "Ласкаво просимо до гри <b>Бункер</b>!",
        reply_markup=get_start_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "init_room")
async def init_room_creation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CreateRoomState.waiting_for_total_players)
    await callback.message.answer(
        "👥 Надішли <b>загальну кількість гравців</b> (наприклад, <code>6</code>):",
        parse_mode="HTML",
    )


@dp.message(CreateRoomState.waiting_for_total_players)
async def process_total_players(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 2:
        await message.answer("❌ Введи число більше або рівне 2.")
        return

    total_players = int(message.text)
    await state.update_data(total_players=total_players)
    await state.set_state(CreateRoomState.waiting_for_bunker_seats)
    await message.answer(
        f"🔒 Скільки людей <b>зможе вижити в бункері</b>? (Має бути менше ніж {total_players}):",
        parse_mode="HTML",
    )


@dp.message(CreateRoomState.waiting_for_bunker_seats)
async def process_bunker_seats(message: types.Message, state: FSMContext):
    data = await state.get_data()
    total_players = data.get("total_players")

    if not total_players:
        await state.set_state(CreateRoomState.waiting_for_total_players)
        await message.answer(
            "❌ Сталася помилка сесії. Надішли **загальну кількість гравців**:"
        )
        return

    if (
        not message.text.isdigit()
        or int(message.text) >= total_players
        or int(message.text) < 1
    ):
        await message.answer(f"❌ Число має бути від 1 до {total_players - 1}.")
        return

    bunker_seats = int(message.text)
    await state.clear()

    room_id = secrets.token_hex(4)
    apocalypse_name = secrets.choice(list(APOCALYPSES.keys()))
    bunker_info = generate_bunker_info()

    ROOMS[room_id] = {
        "host_id": message.from_user.id,
        "max_players": total_players,
        "bunker_seats": bunker_seats,
        "apocalypse": apocalypse_name,
        "bunker_info": bunker_info,
        "players": {
            message.from_user.id: {
                "name": message.from_user.full_name,
                "character": generate_character(),
                "votes": 0,
                "voted_against": [],
                "voted": False,
                "dash_message_id": None,
                "card_message_id": None,
                "is_spectator": False,
                "is_ghost_voter": False,
            }
        },
        "status": "waiting",
        "round": 1,
        "last_activity": time.time(),
        "evaluating_round": False,
    }

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={room_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text="Запустити гру 🚀", callback_data=f"start_game:{room_id}")

    await message.answer(
        f"🏰 <b>Кімнату успішно створено!</b>\n\n"
        f"🌋 Катастрофа: <b>{html.escape(apocalypse_name)}</b>\n"
        f"⏳ Час перебування: <b>{bunker_info['years']} років</b>\n"
        f"🛠️ Стан бункера: <b>{bunker_info['condition']}</b>\n"
        f"🍞 Ресурси: <b>{bunker_info['resources']}</b>\n"
        f"👥 Гравців: <b>{total_players}</b>\n"
        f"🔒 Місць у бункері: <b>{bunker_seats}</b>\n\n"
        f"🔗 Надішли це посилання учасникам:\n<code>{invite_link}</code>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("start_game:"))
async def start_game(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)

    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    if callback.from_user.id != room["host_id"]:
        await callback.answer("Лише хост може розпочати гру!", show_alert=True)
        return

    room["status"] = "playing"
    await callback.message.edit_text("🎮 Гра розпочалася!")

    for player_id, p_data in room["players"].items():
        char = p_data["character"]
        pinned_msg = await bot.send_message(
            player_id,
            format_personal_card(char),
            reply_markup=get_reveal_keyboard(room_id, char),
            parse_mode="HTML",
        )
        p_data["card_message_id"] = pinned_msg.message_id

    await update_live_dashboards(room_id)


@dp.callback_query(F.data.startswith("rev:"))
async def process_reveal(callback: types.CallbackQuery):
    _, room_id, trait_key = callback.data.split(":")
    room = ROOMS.get(room_id)
    if not room:
        await callback.answer("Кімнату закрито.")
        return

    player = room["players"].get(callback.from_user.id)
    if not player or player.get("is_spectator"):
        await callback.answer("Ви не є активним гравцем.")
        return

    char = player["character"]
    if trait_key not in char["opened"]:
        char["opened"].append(trait_key)
        await callback.answer("Характеристику розкрито!")
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_reveal_keyboard(room_id, char)
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        await update_live_dashboards(room_id)


@dp.callback_query(F.data.startswith("use_act:"))
async def use_action(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)
    if not room:
        await callback.answer("Кімнату не знайдено.")
        return

    user_id = callback.from_user.id
    player = room["players"].get(user_id)
    if not player or player.get("is_spectator"):
        await callback.answer("Спостерігачі не можуть виконувати дії.", show_alert=True)
        return

    char = player["character"]
    if char.get("action_used", False):
        await callback.answer("Ви вже використали свою дію!", show_alert=True)
        return

    act = char["action"]
    act_type = act["type"]

    # --- МИТТЄВІ ДІЇ БЕЗ ЦІЛІ ---
    if act_type == "SABOTAGE":
        room["bunker_seats"] = max(1, room["bunker_seats"] - 1)
        char["action_used"] = True
        await callback.message.answer(
            "💥 <b>Ви вчинили саботаж!</b> Кількість місць у бункері зменшено на 1.",
            parse_mode="HTML",
        )

    elif act_type == "ADD_SEAT":
        room["bunker_seats"] += 1
        char["action_used"] = True
        await callback.message.answer(
            "🛠️ <b>Ви відремонтували бункер!</b> Додано +1 місце.", parse_mode="HTML"
        )

    elif act_type == "HEAL":
        char["health"] = "Повністю здоровий(а)"
        char["action_used"] = True
        await callback.message.answer(
            "💉 <b>Ви використали ліки!</b> Тепер ви повністю здорові.",
            parse_mode="HTML",
        )

    elif act_type == "PROTECT":
        char["is_protected"] = True
        char["action_used"] = True
        await callback.message.answer(
            "🛡️ <b>Штурмовий щит активовано!</b> Ви захищені від вигнання у цьому раунді.",
            parse_mode="HTML",
        )

    elif act_type == "DOUBLE_VOTE":
        char["double_vote"] = True
        char["action_used"] = True
        await callback.message.answer(
            "🗳️ <b>Ваш голос у цьому раунді буде вираховуватися за два!</b>",
            parse_mode="HTML",
        )

    elif act_type == "REVEAL_ALL":
        char["action_used"] = True
        for p_id, p_data in room["players"].items():
            if not p_data.get("is_spectator"):
                p_char = p_data["character"]
                unopened = [
                    k for k in LABELS.keys() if k not in p_char.get("opened", [])
                ]
                if unopened:
                    chosen = random.choice(unopened)
                    p_char["opened"].append(chosen)

                if p_data.get("card_message_id") and p_id != user_id:
                    try:
                        await bot.edit_message_text(
                            chat_id=p_id,
                            message_id=p_data["card_message_id"],
                            text=format_personal_card(p_char),
                            reply_markup=get_reveal_keyboard(room_id, p_char),
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        await callback.message.answer(
            "📢 <b>Викривач!</b> Відкрито по 1 прихованій характеристиці кожного гравця.",
            parse_mode="HTML",
        )

    elif act_type == "REROLL_SELF":
        char["profession"] = random.choice(PROFESSIONS)
        char["hobby"] = random.choice(HOBBIES)
        char["action_used"] = True
        await callback.message.answer(
            f"🎭 <b>Особистість змінено!</b> Нова професія: {char['profession']}, Хобі: {char['hobby']}",
            parse_mode="HTML",
        )

    elif act_type == "REROLL_TRAIT_FACT":
        char["trait"] = random.choice(TRAITS)
        char["fact"] = random.choice(FACTS)
        char["action_used"] = True
        await callback.message.answer(
            f"🎭 <b>Двійник!</b> Новий характер: {char['trait']}, Факт: {char['fact']}",
            parse_mode="HTML",
        )

    elif act_type == "REFLECT_VOTE":
        char["reflect_vote"] = True
        char["action_used"] = True
        await callback.message.answer(
            "🃏 <b>Дзеркальний щит активовано!</b> Голоси проти вас повернуться тим, хто проголосував.",
            parse_mode="HTML",
        )

    elif act_type == "CANCEL_VOTES":
        char["cancel_votes"] = True
        char["action_used"] = True
        await callback.message.answer(
            "🕊️ <b>Амністія!</b> Усі голоси проти вас у цьому раунді будуть анульовані.",
            parse_mode="HTML",
        )

    # --- ЦІЛЬОВІ ДІЇ ---
    elif act_type in TARGETED_ACTIONS:
        alive_players = {
            k: v
            for k, v in room["players"].items()
            if not v.get("is_spectator", False) and k != user_id
        }

        if not alive_players:
            await callback.answer(
                "Немає доступних цілей для цієї дії!", show_alert=True
            )
            return

        builder = InlineKeyboardBuilder()
        for target_id, target_data in alive_players.items():
            builder.button(
                text=target_data["name"],
                callback_data=f"act_target:{room_id}:{act_type}:{target_id}",
            )
        builder.adjust(1)

        await callback.message.answer(
            f"🎯 <b>Обери ціль для дії '{html.escape(act['name'])}':</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        return
    else:
        await callback.answer(f"❌ Невідомий тип дії: {act_type}", show_alert=True)
        return

    # Оновлення інтерфейсу після виконання нецільових дій
    try:
        await callback.message.edit_text(
            format_personal_card(char),
            reply_markup=get_reveal_keyboard(room_id, char),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await update_live_dashboards(room_id)


@dp.callback_query(F.data.startswith("act_target:"))
async def process_action_target(callback: types.CallbackQuery):
    _, room_id, act_type, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)
    room = ROOMS.get(room_id)
    if not room:
        await callback.answer("Кімнату не знайдено.")
        return

    user_id = callback.from_user.id
    actor = room["players"].get(user_id)
    target = room["players"].get(target_id)

    if not actor or not target:
        await callback.answer("Помилка цілі.")
        return

    actor_char = actor["character"]
    target_char = target["character"]

    if actor_char.get("action_used", False):
        await callback.answer("Дія вже була використана!", show_alert=True)
        return

    msg = ""
    actor_name = html.escape(actor["name"])
    target_name = html.escape(target["name"])

    if act_type == "SWAP_BAG":
        actor_char["baggage"], target_char["baggage"] = (
            target_char["baggage"],
            actor_char["baggage"],
        )
        msg = f"🔄 <b>{actor_name}</b> обмінявся багажем із <b>{target_name}</b>!"

    elif act_type == "SWAP_HEALTH":
        actor_char["health"], target_char["health"] = (
            target_char["health"],
            actor_char["health"],
        )
        msg = (
            f"🧬 <b>{actor_name}</b> обмінявся станом здоров'я з <b>{target_name}</b>!"
        )

    elif act_type == "SWAP_PROF":
        actor_char["profession"], target_char["profession"] = (
            target_char["profession"],
            actor_char["profession"],
        )
        msg = f"💼 <b>{actor_name}</b> обмінявся професією з <b>{target_name}</b>!"

    elif act_type == "SWAP_HOBBY":
        actor_char["hobby"], target_char["hobby"] = (
            target_char["hobby"],
            actor_char["hobby"],
        )
        msg = f"🎨 <b>{actor_name}</b> обмінявся хобі з <b>{target_name}</b>!"

    elif act_type == "SWAP_TRAIT":
        actor_char["trait"], target_char["trait"] = (
            target_char["trait"],
            actor_char["trait"],
        )
        msg = f"💣 <b>{actor_name}</b> обмінявся характером з <b>{target_name}</b>!"

    elif act_type == "SWAP_FACT":
        actor_char["fact"], target_char["fact"] = (
            target_char["fact"],
            actor_char["fact"],
        )
        msg = f"📜 <b>{actor_name}</b> обмінявся прихованим фактом з <b>{target_name}</b>!"

    elif act_type == "COPY_BAG":
        actor_char["baggage"] = target_char["baggage"]
        msg = f"📦 <b>{actor_name}</b> скопіював багаж гравця <b>{target_name}</b>!"

    elif act_type == "INFECT":
        target_char["health"] = actor_char["health"]
        msg = f"☣️ <b>{actor_name}</b> передав свою хворобу гравцю <b>{target_name}</b>!"

    elif act_type == "MAKE_SICK":
        target_char["health"] = "Невиліковна біологічна хвороба"
        msg = f"🧪 <b>{actor_name}</b> заразив <b>{target_name}</b> невиліковною хворобою!"

    elif act_type == "STEAL_BAG":
        actor_char["baggage"] = f"{actor_char['baggage']} + {target_char['baggage']}"
        target_char["baggage"] = "Порожньо (викрадено)"
        msg = f"🎒 <b>{actor_name}</b> викрав багаж у <b>{target_name}</b>!"

    elif act_type == "CHECK":
        all_info = "\n".join(
            [f"• {label}: {target_char[key]}" for key, label in LABELS.items()]
        )
        msg = f"🔍 <b>{actor_name}</b> провів розвідку щодо {target_name}."
        await callback.message.answer(
            f"🔍 <b>Розвідка про {target_name}:</b>\n\n{html.escape(all_info)}",
            parse_mode="HTML",
        )

    elif act_type == "REVEAL_FACT":
        msg = f"🔮 <b>{actor_name}</b> дізнався прихований факт та характер {target_name}."
        await callback.message.answer(
            f"🔮 <b>Таємниці {target_name}:</b>\n\n"
            f"• Характер: {html.escape(str(target_char['trait']))}\n"
            f"• Прихований факт: {html.escape(str(target_char['fact']))}",
            parse_mode="HTML",
        )

    elif act_type == "SILENCE":
        target_char["is_silenced"] = True
        msg = f"🔇 <b>{actor_name}</b> змусив замовкнути <b>{target_name}</b> на цей раунд!"

    elif act_type == "QUARANTINE":
        target_char["is_silenced"] = True
        msg = f"🔒 <b>{actor_name}</b> відправив <b>{target_name}</b> на карантин (заблоковано голосування)!"

    elif act_type == "CURE_OTHER":
        target_char["health"] = "Повністю здоровий(а)"
        msg = f"🩺 <b>{actor_name}</b> вилікував гравця <b>{target_name}</b>!"

    elif act_type == "REROLL_OTHER_PROF":
        target_char["profession"] = random.choice(PROFESSIONS)
        msg = f"⚡ <b>{actor_name}</b> змінив професію гравця <b>{target_name}</b>!"

    elif act_type == "REVEAL_TARGET_ALL":
        for k in LABELS.keys():
            if k not in target_char["opened"]:
                target_char["opened"].append(k)
        msg = f"🕵️ <b>{actor_name}</b> оприлюднив ВСІ характеристики гравця <b>{target_name}</b>!"

    elif act_type == "STEAL_ACTION":
        target_char["action_used"] = True
        msg = f"🧲 <b>{actor_name}</b> заблокував особливу дію гравцю <b>{target_name}</b>!"

    elif act_type == "LINK_SURVIVAL":
        actor_char["linked_partner"] = target_id
        msg = f"🤝 <b>{actor_name}</b> уклав союз виживання з <b>{target_name}</b>!"

    elif act_type == "FORCE_VOTE_TARGET":
        target_char["forced_vote"] = True
        msg = f"📣 <b>{actor_name}</b> змусив <b>{target_name}</b> проголосувати проти вашої цілі!"

    actor_char["action_used"] = True

    # Прибираємо повідомлення вибору цілі
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Оновлюємо картку того, хто викликав дію
    try:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=actor["card_message_id"],
            text=format_personal_card(actor_char),
            reply_markup=get_reveal_keyboard(room_id, actor_char),
            parse_mode="HTML",
        )
    except Exception:
        pass

    # Оновлюємо закріплену картку цілі
    if target.get("card_message_id"):
        try:
            await bot.edit_message_text(
                chat_id=target_id,
                message_id=target["card_message_id"],
                text=format_personal_card(target_char),
                reply_markup=get_reveal_keyboard(room_id, target_char),
                parse_mode="HTML",
            )
        except Exception:
            pass

    broadcast_tasks = [
        bot.send_message(p_id, f"⚡ <b>ПОДІЯ:</b> {msg}", parse_mode="HTML")
        for p_id in room["players"].keys()
    ]
    await asyncio.gather(*broadcast_tasks, return_exceptions=True)

    await update_live_dashboards(room_id)


@dp.callback_query(F.data.startswith("init_vote:"))
async def init_vote(callback: types.CallbackQuery):
    room_id = callback.data.split(":")[1]
    room = ROOMS.get(room_id)
    if not room:
        await callback.answer("Кімнату закрито.")
        return

    room["status"] = "voting"
    room.pop("revote_candidates", None)

    await start_voting_phase(room_id)


async def start_voting_phase(
    room_id: str, revote_candidates: Optional[List[int]] = None
):
    room = ROOMS.get(room_id)
    if not room:
        return

    eligible_voters = {
        k: v
        for k, v in room["players"].items()
        if not v.get("is_spectator", False) or v.get("is_ghost_voter", False)
    }

    for p_id in room["players"].keys():
        room["players"][p_id]["votes"] = 0
        room["players"][p_id]["voted_against"] = []
        room["players"][p_id]["voted"] = False

    if revote_candidates:
        alive_targets = {
            k: v
            for k, v in room["players"].items()
            if k in revote_candidates and not v.get("is_spectator", False)
        }
    else:
        alive_targets = {
            k: v for k, v in room["players"].items() if not v.get("is_spectator", False)
        }

    for p_id, p_data in eligible_voters.items():
        if p_data["character"].get("is_silenced"):
            await bot.send_message(
                p_id,
                "🔇 <b>Вас заглушено/відправлено на карантин. Ви не можете голосувати!</b>",
                parse_mode="HTML",
            )
            p_data["voted"] = True
            continue

        builder = InlineKeyboardBuilder()
        for target_id, target_data in alive_targets.items():
            if target_id != p_id:
                builder.button(
                    text=target_data["name"],
                    callback_data=f"vote:{room_id}:{target_id}",
                )
        builder.adjust(1)

        prefix = (
            "⚖️ <b>ПЕРЕГОЛОСУВАННЯ!</b>\nОберіть серед тих, хто набрав однакову кількість голосів:\n"
            if revote_candidates
            else (
                "👻 <b>ГОЛОСУВАННЯ ПРИВИДА</b>\n"
                if p_data.get("is_ghost_voter")
                else f"🗳️ <b>ГОЛОСУВАННЯ РАУНДУ {room['round']}</b>\n"
            )
        )

        await bot.send_message(
            p_id,
            f"{prefix}Оберіть, кого вигнати з бункера:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


@dp.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: types.CallbackQuery):
    _, room_id, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)
    room = ROOMS.get(room_id)
    if not room:
        await callback.answer("Гра завершена.")
        return

    voter_id = callback.from_user.id
    voter = room["players"].get(voter_id)

    if not voter or voter.get("voted"):
        await callback.answer(
            "Ви вже проголосували або не можете голосувати!", show_alert=True
        )
        return

    voter["voted"] = True
    if voter.get("is_ghost_voter"):
        voter["is_ghost_voter"] = False

    vote_weight = 2 if voter["character"].get("double_vote") else 1

    room["players"][target_id]["votes"] += vote_weight
    room["players"][target_id]["voted_against"].append(voter_id)

    await callback.message.edit_text("👌 Голос зараховано.")

    voters_in_round = [
        p
        for p in room["players"].values()
        if not p.get("is_spectator", False) or p.get("is_ghost_voter", False)
    ]

    if all(p["voted"] for p in voters_in_round):
        alive_players = {
            k: v for k, v in room["players"].items() if not v.get("is_spectator", False)
        }

        # Пасивні здібності захисту/віддзеркалення
        for pid, pdata in alive_players.items():
            char = pdata["character"]
            if char.get("cancel_votes"):
                pdata["votes"] = 0
            if char.get("reflect_vote") and pdata["voted_against"]:
                for attacker_id in pdata["voted_against"]:
                    if attacker_id in alive_players:
                        alive_players[attacker_id]["votes"] += 1
                pdata["votes"] = 0

        max_votes = -1
        candidates = []

        for pid, pdata in alive_players.items():
            if pdata["character"].get("is_protected"):
                continue
            if pdata["votes"] > max_votes:
                max_votes = pdata["votes"]
                candidates = [pid]
            elif pdata["votes"] == max_votes:
                candidates.append(pid)

        # Нічия / Переголосування
        if not candidates or max_votes <= 0:
            for p_id in room["players"].keys():
                await bot.send_message(
                    p_id,
                    "🤝 <b>Ніхто не отримав голосів. Нікого не вигнано!</b>",
                    parse_mode="HTML",
                )

        elif len(candidates) > 1:
            candidate_names = ", ".join(
                [
                    f"<b>{html.escape(room['players'][c]['name'])}</b>"
                    for c in candidates
                ]
            )

            if room.get("revote_candidates") == candidates:
                for p_id in room["players"].keys():
                    await bot.send_message(
                        p_id,
                        f"⚖️ <b>Повторне переголосування знову завершилося нічиєю між {candidate_names}!</b>\nУ цьому раунді нікого не вигнано.",
                        parse_mode="HTML",
                    )
                room.pop("revote_candidates", None)
            else:
                room["revote_candidates"] = candidates
                for p_id in room["players"].keys():
                    await bot.send_message(
                        p_id,
                        f"⚠️ <b>Нічия!</b> Гравці {candidate_names} набрали однакову кількість голосів ({max_votes}).\n\n🔄 <b>Оголошується ПЕРЕГОЛОСУВАННЯ між ними!</b>",
                        parse_mode="HTML",
                    )
                await start_voting_phase(room_id, revote_candidates=candidates)
                return

        else:
            # Вигнання гравця
            kicked_id = candidates[0]
            kicked_player = room["players"][kicked_id]
            kicked_player["is_spectator"] = True
            room.pop("revote_candidates", None)

            # Перевірка союзу виживання (LINK_SURVIVAL)
            # Якщо вигнаний гравець був обраний як партнер, захист отримує той, хто застосував дію
            # Перевірка союзу виживання (LINK_SURVIVAL)
            for p_id, p_data in room["players"].items():
                if not p_data.get("is_spectator"):
                    # Якщо цей гравець (Гравець 1) прив'язався до вигнаного гравця (kicked_id)
                    if p_data["character"].get("linked_partner") == kicked_id:
                        p_data["character"]["is_protected"] = True
                        await bot.send_message(
                            p_id,
                            "🤝 <b>Ваш партнер вибув! Ви отримуєте щит захисту на наступний раунд.</b>",
                            parse_mode="HTML",
                        )

            cond = kicked_player["character"]["condition"]
            kicked_name = html.escape(kicked_player["name"])
            cond_msg = f"🚪 <b>{kicked_name}</b> вибуває з бункера!\n\n⚠️ <b>СПРАЦЮВАВ ЗАПОВІТ:</b>\n<i>{html.escape(cond['desc'])}</i>"

            # --- ОБРОБКА ЗАПОВІТІВ (CONDITIONS) ---
            voters = kicked_player.get("voted_against", [])

            if cond["type"] == "PLAGUE_VOTERS":
                for voter_pid in voters:
                    if voter_pid in room["players"]:
                        room["players"][voter_pid]["character"]["health"] = (
                            "Смертельна чума"
                        )
                cond_msg += (
                    "\n☠️ <i>Усі, хто проголосував проти нього, заразилися чумою!</i>"
                )

            elif cond["type"] == "INFECT_VOTERS":
                for voter_pid in voters:
                    if voter_pid in room["players"]:
                        room["players"][voter_pid]["character"]["health"] = (
                            "Легка застуда"
                        )
                cond_msg += (
                    "\n🤧 <i>Усі, хто проголосував проти нього, підхопили застуду!</i>"
                )

            elif cond["type"] == "DESTROY_BAG":
                kicked_player["character"]["baggage"] = "Знищено при вигнанні"

            elif cond["type"] == "STEAL_FOOD":
                room["bunker_seats"] = max(0, room["bunker_seats"] - 1)
                cond_msg += "\n🚪 <i>Кількість місць у бункері зменшено на 1!</i>"

            elif cond["type"] == "CURSE_HOST":
                host_id = room.get("host_id")
                if host_id and host_id in room["players"]:
                    room["players"][host_id]["character"]["baggage"] = (
                        "Втрачено через прокляття"
                    )
                cond_msg += "\n🔮 <i>Найбагатший гравець (гост) втратив свій багаж!</i>"

            elif cond["type"] == "LOCK_DOOR":
                for p_data in room["players"].values():
                    if not p_data.get("is_spectator"):
                        p_data["character"]["next_round_silenced"] = True
                cond_msg += "\n🔒 <i>Двері бункера заблоковано!</i>"

            elif cond["type"] == "GIFT_BAG":
                if voters:
                    first_voter_id = voters[0]
                    if first_voter_id in room["players"]:
                        room["players"][first_voter_id]["character"]["baggage"] = (
                            kicked_player["character"]["baggage"]
                        )
                        kicked_player["character"]["baggage"] = (
                            "Подаровано при вигнанні"
                        )
                cond_msg += "\n🎁 <i>Багаж подаровано першому виборцю!</i>"

            elif cond["type"] == "GHOST_VOTE":
                kicked_player["is_ghost_voter"] = True
                cond_msg += "\n👻 <i>Привид гравця зможе проголосувати один раз у наступному раунді!</i>"

            elif cond["type"] == "DROP_KEY":
                room["bunker_seats"] += 1
                cond_msg += (
                    "\n🗝️ <i>Гравець залишив ключ! Додано +1 місце в бункері.</i>"
                )

            elif cond["type"] == "BLIND_VOTERS":
                for voter_pid in voters:
                    if voter_pid in room["players"]:
                        room["players"][voter_pid]["character"]["health"] = (
                            "Куряча сліпота"
                        )
                cond_msg += (
                    "\n🙈 <i>Усі, хто голосував проти, отримали курячу сліпоту!</i>"
                )

            elif cond["type"] == "SILENCE_VOTERS":
                for voter_pid in voters:
                    if voter_pid in room["players"]:
                        room["players"][voter_pid]["character"][
                            "next_round_silenced"
                        ] = True
                cond_msg += (
                    "\n🤐 <i>Усі, хто голосував проти, мовчать у наступному раунді!</i>"
                )

            elif cond["type"] == "CURE_RANDOM":
                alive = [
                    p for p in room["players"].values() if not p.get("is_spectator")
                ]
                if alive:
                    lucky = random.choice(alive)
                    lucky["character"]["health"] = "Повністю здоровий(а)"
                    cond_msg += f"\n🕊️ <i>Наостанок зцілено гравця <b>{html.escape(lucky['name'])}</b>!</i>"

            elif cond["type"] == "REVEAL_SECRET":
                if "fact" not in kicked_player["character"]["opened"]:
                    kicked_player["character"]["opened"].append("fact")
                cond_msg += f"\n📢 <i>Прихований факт вигнаного: <b>{html.escape(kicked_player['character']['fact'])}</b></i>"

            elif cond["type"] == "EXPOSE_TRAIT":
                for voter_pid in voters:
                    if voter_pid in room["players"]:
                        v_char = room["players"][voter_pid]["character"]
                        if "trait" not in v_char["opened"]:
                            v_char["opened"].append("trait")
                cond_msg += "\n🧠 <i>Розкрито характер усіх, хто голосував проти!</i>"

            elif cond["type"] == "SWAP_ON_EXIT":
                active_players = [
                    p for p in room["players"].values() if not p.get("is_spectator")
                ]
                if active_players:
                    min_votes = min(p["votes"] for p in active_players)
                    candidates_p = [
                        p for p in active_players if p["votes"] == min_votes
                    ]
                    recipient = random.choice(candidates_p)
                    recipient["character"]["baggage"] = kicked_player["character"][
                        "baggage"
                    ]
                    kicked_player["character"]["baggage"] = "Передано при вигнанні"
                    cond_msg += f"\n🔄 <i>Багаж передано гравцю <b>{html.escape(recipient['name'])}</b>!</i>"

            # Оновлюємо закріплену картку вигнаного гравця (знімаємо кнопки)
            if kicked_player.get("card_message_id"):
                try:
                    await bot.edit_message_text(
                        chat_id=kicked_id,
                        message_id=kicked_player["card_message_id"],
                        text=format_personal_card(kicked_player["character"]),
                        reply_markup=get_reveal_keyboard(
                            room_id, kicked_player["character"], is_alive=False
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            broadcast_tasks = [
                bot.send_message(p_id, cond_msg, parse_mode="HTML")
                for p_id in room["players"].keys()
            ]
            await asyncio.gather(*broadcast_tasks, return_exceptions=True)

        # Скидання разових статутних підсилень раунду
        for pdata in room["players"].values():
            pdata["character"]["is_protected"] = False
            pdata["character"]["double_vote"] = False
            pdata["character"]["cancel_votes"] = False
            pdata["character"]["reflect_vote"] = False
            pdata["character"]["is_silenced"] = pdata["character"].pop(
                "next_round_silenced", False
            )

        await update_live_dashboards(room_id)

        # Фінал гри
        current_alive = [
            v for v in room["players"].values() if not v.get("is_spectator", False)
        ]
        if len(current_alive) <= room["bunker_seats"]:
            success, final_msg = evaluate_survival(
                room["apocalypse"], current_alive, room["bunker_info"]
            )

            final_tasks = [
                bot.send_message(
                    p_id,
                    f"🏁 <b>ФІНАЛ ГРИ!</b>\n\n{final_msg}",
                    reply_markup=get_new_game_keyboard(room_id),  # Передаємо room_id
                    parse_mode="HTML",
                )
                for p_id in room["players"].keys()
            ]
            await asyncio.gather(*final_tasks, return_exceptions=True)
            # Keep room data so "Нова гра з цим складом" (init_rematch) can still access players.
            # Room will be removed when rematch starts or by stale cleanup later.
            room["status"] = "finished"
            room["last_activity"] = time.time()
        else:
            room["round"] += 1
            room["status"] = "playing"


def cleanup_stale_rooms(max_age_seconds: int = 86400) -> int:
    """Очищає кімнати з ROOMS, які були неактивні понад max_age_seconds (за замовчуванням 24 години)."""
    current_time = time.time()
    stale_room_ids = [
        r_id
        for r_id, r_data in ROOMS.items()
        if current_time - r_data.get("last_activity", current_time) > max_age_seconds
    ]
    for r_id in stale_room_ids:
        ROOMS.pop(r_id, None)
    if stale_room_ids:
        logger.info(f"Очищено {len(stale_room_ids)} неактивних кімнат.")
    return len(stale_room_ids)


async def _stale_rooms_cleanup_loop(
    interval_seconds: int = 3600, max_age_seconds: int = 86400
) -> None:
    """Фоновий цикл періодичного очищення застарілих кімнат."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            cleaned = cleanup_stale_rooms(max_age_seconds=max_age_seconds)
            if cleaned:
                logger.info(f"Таймер очищення: видалено {cleaned} кімнат(и).")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"Помилка в циклі очищення кімнат: {e}")


async def main():
    if not API_TOKEN:
        logger.error("Токен бота не вказано! Вкажіть змінну оточення TG_API_TOKEN.")
        return
    logger.info("Бот успішно запущений та готовий до роботи!")
    cleanup_task = asyncio.create_task(
        _stale_rooms_cleanup_loop(interval_seconds=3600, max_age_seconds=86400)
    )
    try:
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
