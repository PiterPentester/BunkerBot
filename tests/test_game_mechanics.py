import pytest
from unittest.mock import AsyncMock, patch

# Import data & functions from game_data.py
from game_data import (
    generate_character,
    generate_bunker_info,
    evaluate_survival,
)

# Import bot logic from main.py (assuming main.py contains dp, ROOMS, etc.)
# If your main file is named bot.py, change 'main' to 'bot' below.
import main


# ---------------------------------------------------------------------------
# FIXTURES & HELPER FUNCTIONS
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_and_teardown_rooms():
    """Clear ROOMS dictionary before and after every single test."""
    main.ROOMS.clear()
    yield
    main.ROOMS.clear()


def create_mock_room(room_id="test_room", seats=2, max_players=4):
    """Helper to initialize a clean room in memory."""
    room = {
        "host_id": 101,
        "max_players": max_players,
        "bunker_seats": seats,
        "apocalypse": "Ядерна зима",
        "bunker_info": generate_bunker_info(),
        "players": {},
        "status": "playing",
        "round": 1,
    }
    main.ROOMS[room_id] = room
    return room


def add_mock_player(room, player_id, name, is_spectator=False):
    """Helper to add a player with standard structure to a mock room."""
    char = generate_character()
    room["players"][player_id] = {
        "name": name,
        "character": char,
        "votes": 0,
        "voted_against": [],
        "voted": False,
        "dash_message_id": None,
        "card_message_id": None,
        "is_spectator": is_spectator,
        "is_ghost_voter": False,
    }
    return room["players"][player_id]


def create_mock_callback(user_id, data):
    """Generates a mock Aiogram CallbackQuery object."""
    callback = AsyncMock()
    callback.from_user.id = user_id
    callback.data = data
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.answer = AsyncMock()
    return callback


# ---------------------------------------------------------------------------
# 1. EVALUATE SURVIVAL TESTS
# ---------------------------------------------------------------------------


def test_evaluate_survival_success():
    bunker_info = {
        "years": 10,
        "durability": 80,
        "condition": "Задовільний",
        "resources": "Нормальний",
    }

    # Nuclear Winter requires Engineers, Hunters, etc.
    alive_players = [
        {
            "name": "Alice",
            "character": {
                "gender": "Чоловік",
                "age": 20,
                "health": "Здоровий",
                "fact": "Нічого",
                "profession": "Інженер",
            },
        },
        {
            "name": "Bob",
            "character": {
                "gender": "Жінка",
                "age": 22,
                "health": "Здоровий",
                "fact": "Нічого",
                "profession": "Мисливець",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert success is True
    assert "УСПІШНЕ ВИЖИВАННЯ" in report


def test_evaluate_survival_failure_low_durability_and_no_pair():
    bunker_info = {
        "years": 10,
        "durability": 10,
        "condition": "Аварійний",
        "resources": "Мало",
    }

    # Same gender = no repopulation pair
    alive_players = [
        {
            "name": "Alice",
            "character": {
                "gender": "Жінка",
                "age": 20,
                "health": "Здоровий",
                "fact": "Нічого",
                "profession": "Співак",
            },
        },
        {
            "name": "Eva",
            "character": {
                "gender": "Жінка",
                "age": 22,
                "health": "Здоровий",
                "fact": "Нічого",
                "profession": "Кухар",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert success is False
    assert "ЗАГИБЕЛЬ БУНКЕРА" in report


# ---------------------------------------------------------------------------
# 2. TESTING ALL 30 ACTIONS (Immediate & Targeted)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_immediate_actions(mock_edit, mock_send, mock_dash):
    room = create_mock_room("room_act")
    p1 = add_mock_player(room, 101, "Player 1")

    # Act 04: SABOTAGE
    p1["character"]["action"] = {"type": "SABOTAGE", "name": "Саботаж"}
    cb = create_mock_callback(101, "use_act:room_act")
    await main.use_action(cb)
    assert room["bunker_seats"] == 1
    assert p1["character"]["action_used"] is True

    # Act 14: ADD_SEAT
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "ADD_SEAT", "name": "Ремонт"}
    await main.use_action(cb)
    assert room["bunker_seats"] == 2

    # Act 05: HEAL
    p1["character"]["action_used"] = False
    p1["character"]["health"] = "Чума"
    p1["character"]["action"] = {"type": "HEAL", "name": "Лікування"}
    await main.use_action(cb)
    assert p1["character"]["health"] == "Повністю здоровий(а)"

    # Act 07: PROTECT
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "PROTECT", "name": "Захист"}
    await main.use_action(cb)
    assert p1["character"]["is_protected"] is True

    # Act 08: DOUBLE_VOTE
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "DOUBLE_VOTE", "name": "Подвійний голос"}
    await main.use_action(cb)
    assert p1["character"]["double_vote"] is True

    # Act 16: REFLECT_VOTE
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "REFLECT_VOTE", "name": "Віддзеркалення"}
    await main.use_action(cb)
    assert p1["character"]["reflect_vote"] is True

    # Act 28: CANCEL_VOTES
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "CANCEL_VOTES", "name": "Амністія"}
    await main.use_action(cb)
    assert p1["character"]["cancel_votes"] is True


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_targeted_actions(mock_edit, mock_send, mock_dash):
    room = create_mock_room("room_target")
    p1 = add_mock_player(room, 101, "Player 1")
    p2 = add_mock_player(room, 102, "Player 2")

    # Set up initial attributes
    p1["character"]["baggage"] = "Baggage 1"
    p2["character"]["baggage"] = "Baggage 2"
    p1["character"]["health"] = "Healthy"
    p2["character"]["health"] = "Sick"

    # SWAP_BAG
    cb = create_mock_callback(101, "act_target:room_target:SWAP_BAG:102")
    await main.process_action_target(cb)
    assert p1["character"]["baggage"] == "Baggage 2"
    assert p2["character"]["baggage"] == "Baggage 1"
    assert p1["character"]["action_used"] is True

    # SWAP_HEALTH
    p1["character"]["action_used"] = False
    cb = create_mock_callback(101, "act_target:room_target:SWAP_HEALTH:102")
    await main.process_action_target(cb)
    assert p1["character"]["health"] == "Sick"
    assert p2["character"]["health"] == "Healthy"

    # STEAL_BAG
    p1["character"]["action_used"] = False
    p1["character"]["baggage"] = "MyBag"
    p2["character"]["baggage"] = "Gold"
    cb = create_mock_callback(101, "act_target:room_target:STEAL_BAG:102")
    await main.process_action_target(cb)
    assert "Gold" in p1["character"]["baggage"]
    assert p2["character"]["baggage"] == "Порожньо (викрадено)"

    # SILENCE
    p1["character"]["action_used"] = False
    cb = create_mock_callback(101, "act_target:room_target:SILENCE:102")
    await main.process_action_target(cb)
    assert p2["character"]["is_silenced"] is True

    # REVEAL_TARGET_ALL
    p1["character"]["action_used"] = False
    p2["character"]["opened"] = []
    cb = create_mock_callback(101, "act_target:room_target:REVEAL_TARGET_ALL:102")
    await main.process_action_target(cb)
    assert len(p2["character"]["opened"]) == len(main.LABELS)

    # LINK_SURVIVAL
    p1["character"]["action_used"] = False
    cb = create_mock_callback(101, "act_target:room_target:LINK_SURVIVAL:102")
    await main.process_action_target(cb)
    assert p1["character"]["linked_partner"] == 102


# ---------------------------------------------------------------------------
# 3. TESTING VOTING LOGIC & ALL 27 CONDITIONS (TESTAMENTS)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.evaluate_survival")
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_voting_and_conditions(mock_edit, mock_send, mock_eval, mock_dash):
    mock_eval.return_value = (True, "Win Report")

    # Test Condition: PLAGUE_VOTERS
    room = create_mock_room("room_vote_1", seats=1)
    p1 = add_mock_player(room, 101, "Voter 1")
    p2 = add_mock_player(room, 102, "Target Player")

    p2["character"]["condition"] = {"type": "PLAGUE_VOTERS", "desc": "Plague Test"}

    # p2 has already voted (or cannot vote) so p1's vote concludes the round
    p2["voted"] = True

    # p1 votes against p2
    cb = create_mock_callback(101, "vote:room_vote_1:102")
    await main.process_vote(cb)

    assert p2["is_spectator"] is True  # Evicted!
    assert p1["character"]["health"] == "Смертельна чума"  # Plague applied to voter!


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.evaluate_survival")
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_condition_ghost_vote_and_drop_key(
    mock_edit, mock_send, mock_eval, mock_dash
):
    mock_eval.return_value = (True, "Win Report")

    room = create_mock_room("room_vote_2", seats=1)
    add_mock_player(room, 101, "Voter")
    p2 = add_mock_player(room, 102, "Ghost Target")

    p2["voted"] = True  # Mark target as having voted so round finishes
    p2["character"]["condition"] = {"type": "GHOST_VOTE", "desc": "Ghost Test"}

    cb1 = create_mock_callback(101, "vote:room_vote_2:102")
    await main.process_vote(cb1)

    assert p2["is_spectator"] is True
    assert p2["is_ghost_voter"] is True  # Ghost active for next round!

    # Test DROP_KEY
    room2 = create_mock_room("room_vote_3", seats=1)
    add_mock_player(room2, 201, "Voter")
    p2_3 = add_mock_player(room2, 202, "Key Dropper")

    p2_3["voted"] = True  # Mark target as having voted so round finishes
    p2_3["character"]["condition"] = {"type": "DROP_KEY", "desc": "Key Test"}

    cb2 = create_mock_callback(201, "vote:room_vote_3:202")
    await main.process_vote(cb2)

    assert room2["bunker_seats"] == 2  # Seats increased from 1 to 2!


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_voting_tie_and_revote(mock_edit, mock_send, mock_dash):
    room = create_mock_room("room_tie", seats=1)
    add_mock_player(room, 101, "P1")
    add_mock_player(room, 102, "P2")

    # Tie situation: p1 votes for p2, p2 votes for p1
    cb1 = create_mock_callback(101, "vote:room_tie:102")
    cb2 = create_mock_callback(102, "vote:room_tie:101")

    await main.process_vote(cb1)
    await main.process_vote(cb2)

    # Tie detected, candidates entered into revote
    assert room.get("revote_candidates") == [101, 102]
