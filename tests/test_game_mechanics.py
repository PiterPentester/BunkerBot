import pytest
from unittest.mock import AsyncMock, patch
from game_data import (
    ACTIONS,
    CONDITIONS,
    generate_character,
    generate_bunker_info,
    evaluate_survival,
)

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
# 3. COMPREHENSIVE TESTS FOR ALL 30 ACTIONS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("action_info", ACTIONS, ids=lambda a: a["type"])
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_all_actions(mock_edit, mock_send, mock_dash, action_info):
    act_type = action_info["type"]
    room = create_mock_room(f"room_act_{act_type}")
    p1 = add_mock_player(room, 101, "Player 1")
    p2 = add_mock_player(room, 102, "Player 2")

    p1["character"]["baggage"] = "Actor Bag"
    p2["character"]["baggage"] = "Target Bag"
    p1["character"]["health"] = "Actor Health"
    p2["character"]["health"] = "Target Health"
    p1["character"]["profession"] = "Actor Prof"
    p2["character"]["profession"] = "Target Prof"
    p1["character"]["hobby"] = "Actor Hobby"
    p2["character"]["hobby"] = "Target Hobby"
    p1["character"]["trait"] = "Actor Trait"
    p2["character"]["trait"] = "Target Trait"
    p1["character"]["fact"] = "Actor Fact"
    p2["character"]["fact"] = "Target Fact"
    p1["character"]["opened"] = []
    p2["character"]["opened"] = []

    p1["character"]["action"] = action_info
    p1["character"]["action_used"] = False

    # Execute either untargeted or targeted callback
    if act_type in main.TARGETED_ACTIONS:
        cb = create_mock_callback(101, f"act_target:room_act_{act_type}:{act_type}:102")
        await main.process_action_target(cb)
    else:
        cb = create_mock_callback(101, f"use_act:room_act_{act_type}")
        await main.use_action(cb)

    # Actor action should be marked as used
    assert p1["character"]["action_used"] is True, (
        f"Action {act_type} did not set action_used = True"
    )

    # Specific outcome assertions per action type:
    if act_type == "SWAP_BAG":
        assert p1["character"]["baggage"] == "Target Bag"
        assert p2["character"]["baggage"] == "Actor Bag"
    elif act_type == "SWAP_HEALTH":
        assert p1["character"]["health"] == "Target Health"
        assert p2["character"]["health"] == "Actor Health"
    elif act_type == "SWAP_PROF":
        assert p1["character"]["profession"] == "Target Prof"
        assert p2["character"]["profession"] == "Actor Prof"
    elif act_type == "SABOTAGE":
        assert room["bunker_seats"] == 1
    elif act_type == "HEAL":
        assert p1["character"]["health"] == "Повністю здоровий(а)"
    elif act_type == "CHECK":
        cb.message.answer.assert_called_once()
        assert "Target Prof" in cb.message.answer.call_args[0][0]
    elif act_type == "PROTECT":
        assert p1["character"]["is_protected"] is True
    elif act_type == "DOUBLE_VOTE":
        assert p1["character"]["double_vote"] is True
    elif act_type == "SILENCE":
        assert p2["character"]["is_silenced"] is True
    elif act_type == "SWAP_HOBBY":
        assert p1["character"]["hobby"] == "Target Hobby"
        assert p2["character"]["hobby"] == "Actor Hobby"
    elif act_type == "STEAL_BAG":
        assert p1["character"]["baggage"] == "Actor Bag + Target Bag"
        assert p2["character"]["baggage"] == "Порожньо (викрадено)"
    elif act_type == "INFECT":
        assert p2["character"]["health"] == "Actor Health"
    elif act_type == "REVEAL_ALL":
        assert len(p1["character"]["opened"]) == 1
        assert len(p2["character"]["opened"]) == 1
    elif act_type == "ADD_SEAT":
        assert room["bunker_seats"] == 3
    elif act_type == "REFLECT_VOTE":
        assert p1["character"]["reflect_vote"] is True
    elif act_type == "REVEAL_FACT":
        cb.message.answer.assert_called_once()
        assert "Target Fact" in cb.message.answer.call_args[0][0]
    elif act_type == "CURE_OTHER":
        assert p2["character"]["health"] == "Повністю здоровий(а)"
    elif act_type == "SWAP_TRAIT":
        assert p1["character"]["trait"] == "Target Trait"
        assert p2["character"]["trait"] == "Actor Trait"
    elif act_type == "SWAP_FACT":
        assert p1["character"]["fact"] == "Target Fact"
        assert p2["character"]["fact"] == "Actor Fact"
    elif act_type == "COPY_BAG":
        assert p1["character"]["baggage"] == "Target Bag"
        assert p2["character"]["baggage"] == "Target Bag"
    elif act_type == "MAKE_SICK":
        assert p2["character"]["health"] == "Невиліковна біологічна хвороба"
    elif act_type == "QUARANTINE":
        assert p2["character"]["is_silenced"] is True
    elif act_type == "FORCE_VOTE_TARGET":
        assert p2["character"]["forced_vote"] is True
    elif act_type == "REVEAL_TARGET_ALL":
        assert len(p2["character"]["opened"]) == len(main.LABELS)
    elif act_type == "CANCEL_VOTES":
        assert p1["character"]["cancel_votes"] is True
    elif act_type == "STEAL_ACTION":
        assert p2["character"]["action_used"] is True
    elif act_type == "LINK_SURVIVAL":
        assert p1["character"]["linked_partner"] == 102


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_action_validation_edge_cases(mock_edit, mock_send, mock_dash):
    room = create_mock_room("room_edge")
    p1 = add_mock_player(room, 101, "Player 1")

    # 1. Action already used
    p1["character"]["action_used"] = True
    p1["character"]["action"] = {"type": "SABOTAGE", "name": "Саботаж"}
    cb1 = create_mock_callback(101, "use_act:room_edge")
    await main.use_action(cb1)
    cb1.answer.assert_called_with("Ви вже використали свою дію!", show_alert=True)

    # 2. Spectator cannot use action
    p2 = add_mock_player(room, 102, "Spectator", is_spectator=True)
    p2["character"]["action"] = {"type": "SABOTAGE", "name": "Саботаж"}
    cb2 = create_mock_callback(102, "use_act:room_edge")
    await main.use_action(cb2)
    cb2.answer.assert_called_with(
        "Спостерігачі не можуть виконувати дії.", show_alert=True
    )

    # 3. Targeted action with no available targets
    p1["character"]["action_used"] = False
    p1["character"]["action"] = {"type": "SWAP_BAG", "name": "Обмін"}
    cb3 = create_mock_callback(101, "use_act:room_edge")
    await main.use_action(cb3)
    cb3.answer.assert_called_with(
        "Немає доступних цілей для цієї дії!", show_alert=True
    )


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_reveal_all_only_unopened_characteristics(
    mock_edit, mock_send, mock_dash
):
    room = create_mock_room("room_reveal_test")
    p1 = add_mock_player(room, 101, "Player 1")
    p2 = add_mock_player(room, 102, "Player 2")

    # p1 already has 7 traits opened, only "fact" remains unopened
    all_keys = list(main.LABELS.keys())
    p1["character"]["opened"] = all_keys[:-1]
    p1["character"]["action"] = {"type": "REVEAL_ALL", "name": "Викривач"}
    p1["character"]["action_used"] = False

    # p2 already has all traits opened
    p2["character"]["opened"] = list(all_keys)

    cb = create_mock_callback(101, "use_act:room_reveal_test")
    await main.use_action(cb)

    # p1 should now have the last unopened trait ("fact") opened
    assert all_keys[-1] in p1["character"]["opened"]
    assert len(p1["character"]["opened"]) == len(all_keys)

    # p2 should still have all traits and no duplicates
    assert len(p2["character"]["opened"]) == len(all_keys)
    assert len(set(p2["character"]["opened"])) == len(all_keys)


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_all_silenced_voters_auto_resolves_round(mock_edit, mock_send, mock_dash):
    room = create_mock_room("room_silence_all", seats=1)
    p1 = add_mock_player(room, 101, "Player 1")
    p2 = add_mock_player(room, 102, "Player 2")

    p1["character"]["is_silenced"] = True
    p2["character"]["is_silenced"] = True

    await main.start_voting_phase("room_silence_all")

    # Both players were silenced, so 0 votes cast -> no eviction -> round advances to round 2
    assert room["round"] == 2
    assert room["status"] == "playing"
    assert p1["character"]["is_silenced"] is False
    assert p2["character"]["is_silenced"] is False


# ---------------------------------------------------------------------------
# 4. COMPREHENSIVE TESTS FOR ALL 27 CONDITIONS (TESTAMENTS)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("cond_info", CONDITIONS, ids=lambda c: c["type"])
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.evaluate_survival")
@patch("main.bot.send_message", new_callable=AsyncMock)
@patch("main.bot.edit_message_text", new_callable=AsyncMock)
async def test_all_conditions(mock_edit, mock_send, mock_eval, mock_dash, cond_info):
    mock_eval.return_value = (True, "Win Report")
    cond_type = cond_info["type"]
    room = create_mock_room(f"room_cond_{cond_type}", seats=1)
    p1 = add_mock_player(room, 101, "Voter")
    p2 = add_mock_player(room, 102, "Evicted Player")

    p2["character"]["condition"] = cond_info
    p2["voted"] = True  # Ensure voting phase concludes when p1 votes

    cb = create_mock_callback(101, f"vote:room_cond_{cond_type}:102")
    await main.process_vote(cb)

    assert p2["is_spectator"] is True, f"Condition {cond_type}: player was not evicted"

    # Specific mechanical assertions
    if cond_type == "PLAGUE_VOTERS":
        assert p1["character"]["health"] == "Смертельна чума"
    elif cond_type == "INFECT_VOTERS":
        assert p1["character"]["health"] == "Легка застуда"
    elif cond_type == "DESTROY_BAG":
        assert p2["character"]["baggage"] == "Знищено при вигнанні"
    elif cond_type == "STEAL_FOOD":
        assert room["bunker_seats"] == 0
    elif cond_type == "CURSE_HOST":
        assert (
            room["players"][101]["character"]["baggage"] == "Втрачено через прокляття"
        )
    elif cond_type == "REVEAL_SECRET":
        assert "fact" in p2["character"]["opened"]
    elif cond_type == "SWAP_ON_EXIT":
        assert (
            p1["character"]["baggage"] == p2["character"]["baggage"]
            or p2["character"]["baggage"] == "Передано при вигнанні"
        )
    elif cond_type == "LOCK_DOOR":
        assert p1["character"]["is_silenced"] is True
    elif cond_type == "GIFT_BAG":
        assert (
            p1["character"]["baggage"] == p2["character"]["baggage"]
            or p2["character"]["baggage"] == "Подаровано при вигнанні"
        )
    elif cond_type == "GHOST_VOTE":
        assert p2["is_ghost_voter"] is True
    elif cond_type == "BLIND_VOTERS":
        assert p1["character"]["health"] == "Куряча сліпота"
    elif cond_type == "CURE_RANDOM":
        assert p1["character"]["health"] == "Повністю здоровий(а)"
    elif cond_type == "DROP_KEY":
        assert room["bunker_seats"] == 2
    elif cond_type == "EXPOSE_TRAIT":
        assert "trait" in p1["character"]["opened"]
    elif cond_type == "SILENCE_VOTERS":
        assert p1["character"]["is_silenced"] is True


def test_cleanup_stale_rooms():
    create_mock_room("room_active")
    create_mock_room("room_stale")

    import time

    current_time = time.time()
    main.ROOMS["room_active"]["last_activity"] = current_time
    main.ROOMS["room_stale"]["last_activity"] = current_time - 100000  # Older than 24h

    purged = main.cleanup_stale_rooms(max_age_seconds=86400)
    assert purged == 1
    assert "room_active" in main.ROOMS
    assert "room_stale" not in main.ROOMS


# ---------------------------------------------------------------------------
# 5. REMATCH & REMATCH LOBBY MANAGEMENT TESTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("main.render_rematch_lobby", new_callable=AsyncMock)
async def test_init_rematch_success(mock_render):
    """Перевірка створення рематч-кімнати з попереднім складом гравців."""
    old_room_id = "old_room"
    old_room = create_mock_room(old_room_id, seats=2, max_players=2)
    add_mock_player(old_room, 101, "Host Player")
    add_mock_player(old_room, 102, "Guest Player")

    cb = create_mock_callback(101, f"init_rematch:{old_room_id}")
    await main.init_rematch(cb)

    # Стара кімната видаляється з пам'яті
    assert old_room_id not in main.ROOMS
    # У пам'яті створюється нова кімната з тими ж гравцями
    assert len(main.ROOMS) == 1

    new_room_id = list(main.ROOMS.keys())[0]
    new_room = main.ROOMS[new_room_id]

    assert new_room["host_id"] == 101
    assert len(new_room["players"]) == 2
    assert 101 in new_room["players"]
    assert 102 in new_room["players"]
    assert new_room["status"] == "waiting"
    mock_render.assert_called_once_with(new_room_id)


@pytest.mark.asyncio
async def test_init_rematch_only_host():
    """Перевірка заборони виклику рематчу не-хостом."""
    old_room_id = "old_room"
    old_room = create_mock_room(old_room_id)
    add_mock_player(old_room, 101, "Host Player")
    add_mock_player(old_room, 102, "Guest Player")

    # Спроба рематчу від імені зазвичайного гравця (не хоста)
    cb = create_mock_callback(102, f"init_rematch:{old_room_id}")
    await main.init_rematch(cb)

    cb.answer.assert_called_once_with(
        "Лише хост попередньої гри може розпочати рематч!", show_alert=True
    )
    # Кімната залишається без змін
    assert old_room_id in main.ROOMS


@pytest.mark.asyncio
@patch("main.render_rematch_lobby", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
async def test_kick_player_and_auto_adjust_seats(mock_send, mock_render):
    """Перевірка вилучення гравця хостом та автоматичного коригування місць у бункері."""
    room_id = "rematch_room"
    room = create_mock_room(room_id, seats=2, max_players=3)
    add_mock_player(room, 101, "Host")
    add_mock_player(room, 102, "Player To Kick")
    add_mock_player(room, 103, "Other Player")

    # Хост кикає 102
    cb = create_mock_callback(101, f"kick_p:{room_id}:102")
    await main.kick_player(cb)

    assert 102 not in room["players"]
    assert len(room["players"]) == 2
    assert room["max_players"] == 2
    # Оскільки залишилось 2 гравців, а місць було 2, seats мало коригуватись на len-1 (тобто 1)
    assert room["bunker_seats"] == 1
    mock_send.assert_called_once_with(
        102, "❌ Вас було вилучено з наступної гри хостом."
    )
    mock_render.assert_called_once_with(room_id)


@pytest.mark.asyncio
@patch("main.render_rematch_lobby", new_callable=AsyncMock)
async def test_process_rematch_seats_valid_and_invalid(mock_render):
    """Перевірка зміни кількості місць у бункері під час рематчу."""
    room_id = "rematch_seats_room"
    room = create_mock_room(room_id, seats=1, max_players=3)
    add_mock_player(room, 101, "Host")
    add_mock_player(room, 102, "Player 2")
    add_mock_player(room, 103, "Player 3")

    state = AsyncMock()
    state.get_data.return_value = {"rematch_room_id": room_id}

    # 1. Невалідний ввід (забагато місць, має бути < кількість гравців)
    msg_invalid = AsyncMock()
    msg_invalid.text = "3"
    msg_invalid.answer = AsyncMock()

    await main.process_rematch_seats(msg_invalid, state)
    msg_invalid.answer.assert_called_once_with("❌ Число має бути від 1 до 2.")
    assert room["bunker_seats"] == 1

    # 2. Валідний ввід
    msg_valid = AsyncMock()
    msg_valid.text = "2"
    msg_valid.answer = AsyncMock()

    await main.process_rematch_seats(msg_valid, state)
    assert room["bunker_seats"] == 2
    state.clear.assert_called_once()
    mock_render.assert_called_once_with(room_id)


@pytest.mark.asyncio
@patch("main.update_live_dashboards", new_callable=AsyncMock)
@patch("main.bot.send_message", new_callable=AsyncMock)
async def test_restart_game(mock_send, mock_dash):
    """Перевірка повторного запуску гри після підготовки в лобі."""
    room_id = "restart_room"
    room = create_mock_room(room_id, seats=1, max_players=2)
    room["status"] = "waiting"
    add_mock_player(room, 101, "Host")
    add_mock_player(room, 102, "Player 2")

    mock_send.return_value = AsyncMock(message_id=999)

    cb = create_mock_callback(101, f"restart_game:{room_id}")
    await main.restart_game(cb)

    assert room["status"] == "playing"
    assert mock_send.call_count == 2
    mock_dash.assert_called_once_with(room_id)
