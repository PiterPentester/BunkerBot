import pytest
from unittest.mock import AsyncMock, patch
from aiogram.fsm.context import FSMContext

from main import (
    ROOMS,
    CreateRoomState,
    process_total_players,
    process_bunker_seats,
    use_action,
    generate_character,
)


@pytest.fixture(autouse=True)
def clear_rooms():
    """Очищає словник кімнат перед кожним тестом."""
    ROOMS.clear()


@pytest.fixture
def mock_message():
    """Створює мок-об'єкт повідомлення Telegram."""
    msg = AsyncMock()
    msg.from_user.id = 12345
    msg.from_user.full_name = "Test User"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_state():
    """Створює мок для FSM Context."""
    state = AsyncMock(spec=FSMContext)
    data = {}

    async def mock_update_data(**kwargs):
        data.update(kwargs)

    async def mock_get_data():
        return data

    state.update_data = AsyncMock(side_effect=mock_update_data)
    state.get_data = AsyncMock(side_effect=mock_get_data)
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    return state


@pytest.mark.asyncio
async def test_create_room_fsm_flow(mock_message, mock_state):
    """Тестування створення кімнати через FSM."""
    # Крок 1: Введення кількості гравців
    mock_message.text = "6"
    await process_total_players(mock_message, mock_state)

    mock_state.update_data.assert_called_with(total_players=6)
    mock_state.set_state.assert_called_with(CreateRoomState.waiting_for_bunker_seats)

    # Крок 2: Введення місць у бункері та створення кімнати
    mock_message.text = "3"
    await process_bunker_seats(mock_message, mock_state)

    assert len(ROOMS) == 1
    room_id = list(ROOMS.keys())[0]
    room = ROOMS[room_id]

    assert room["max_players"] == 6
    assert room["bunker_seats"] == 3
    assert room["host_id"] == 12345
    assert 12345 in room["players"]


@pytest.mark.asyncio
async def test_action_sabotage():
    """Тест дії 'Саботаж' — зменшення кількості місць у бункері."""
    room_id = "test_room"
    user_id = 999

    # Використовуємо повну структуру персонажа
    character = generate_character()
    character["action"] = {
        "type": "SABOTAGE",
        "name": "Саботаж",
        "desc": "Зменшує місця",
    }
    character["action_used"] = False

    ROOMS[room_id] = {
        "bunker_seats": 4,
        "players": {
            user_id: {"name": "Saboteur", "character": character, "is_spectator": False}
        },
    }

    callback = AsyncMock()
    callback.data = f"use_act:{room_id}"
    callback.from_user.id = user_id
    callback.message.answer = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()

    with patch("main.update_live_dashboards", new=AsyncMock()):
        await use_action(callback)

    assert ROOMS[room_id]["bunker_seats"] == 3
    assert ROOMS[room_id]["players"][user_id]["character"]["action_used"] is True
    callback.message.answer.assert_called_once()
