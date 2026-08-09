from game_data import (
    evaluate_survival,
    generate_character,
    generate_bunker_info,
)


def test_generate_character():
    """Перевірка коректної генерації структури персонажа."""
    char = generate_character()
    assert "gender" in char
    assert "age" in char
    assert isinstance(char["age"], int)
    assert "profession" in char
    assert char["action_used"] is False
    assert "opened" in char
    assert isinstance(char["opened"], list)


def test_generate_bunker_info():
    """Перевірка генерації параметрів бункера."""
    bunker = generate_bunker_info()
    assert "years" in bunker
    assert "durability" in bunker
    assert 30 <= bunker["durability"] <= 100
    assert "condition" in bunker
    assert "resources" in bunker


def test_survival_reproduction_underage_to_adult():
    """Критичний тест: діти (13 років) досягають статевої зрілості за 6 років у бункері (19 років на виході)."""
    bunker_info = {
        "years": 6,
        "durability": 80,
        "condition": "Ідеальний стан",
        "resources": "Нормальний рівень",
    }

    alive_players = [
        {
            "name": "Boy13",
            "character": {
                "gender": "Чоловік",
                "age": 13,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Фізик-ядерник",
            },
        },
        {
            "name": "Girl13",
            "character": {
                "gender": "Жінка",
                "age": 13,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Лікар",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)

    assert success is True
    assert "Boy13 (зараз 13, досяг 19 р.)" in report
    assert "Girl13 (зараз 13, досягла 19 р.)" in report
    assert "Відновлення популяції можливе!" in report


def test_survival_failure_due_to_infertility():
    """Перевірка: навіть якщо вік підходить, безпліддя блокує відновлення популяції."""
    bunker_info = {"years": 10, "durability": 80, "condition": "ОК", "resources": "ОК"}

    alive_players = [
        {
            "name": "InfertileMan",
            "character": {
                "gender": "Чоловік",
                "age": 20,
                "health": "Безпліддя",
                "fact": "Немає",
                "profession": "Фізик-ядерник",
            },
        },
        {
            "name": "Woman",
            "character": {
                "gender": "Жінка",
                "age": 20,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Інженер-енергетик",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)

    assert "Популяція приречена на вимирання" in report


def test_survival_bunker_durability_penalty():
    """Перевірка впливу низької міцності бункера на виживання."""
    bunker_info = {
        "years": 2,
        "durability": 10,
        "condition": "Зруйнований",
        "resources": "Критично",
    }

    alive_players = [
        {
            "name": "Doctor",
            "character": {
                "gender": "Чоловік",
                "age": 30,
                "health": "Здоровий",
                "fact": "",
                "profession": "Вірусолог",
            },
        },
        {
            "name": "Chemist",
            "character": {
                "gender": "Жінка",
                "age": 30,
                "health": "Здоровий",
                "fact": "",
                "profession": "Хімік",
            },
        },
    ]

    success, report = evaluate_survival("Біологічна чума", alive_players, bunker_info)
    assert "занадто слабким" in report


def test_all_apocalypses_structure():
    """Перевірка валідності структури всіх сценаріїв апокаліпсису."""
    from game_data import APOCALYPSES

    assert len(APOCALYPSES) >= 30
    for name, data in APOCALYPSES.items():
        assert "desc" in data and isinstance(data["desc"], str)
        assert "required" in data and isinstance(data["required"], list)
        assert "required_lower" in data and isinstance(data["required_lower"], list)
        assert "min_healthy" in data
        assert "repopulation_needed" in data and isinstance(
            data["repopulation_needed"], bool
        )
