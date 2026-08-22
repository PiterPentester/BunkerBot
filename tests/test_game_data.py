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


def test_survival_mechanic_and_tools_repair_durability():
    """Перевірка: механік/будівельник з інструментами ремонтує бункер і підвищує його міцність."""
    bunker_info = {
        "years": 5,
        "durability": 35,  # нижче порогу 40%
        "condition": "Аварійний стан (часті протікання води)",
        "resources": "Нормальний рівень",
    }
    alive_players = [
        {
            "name": "BobTheBuilder",
            "character": {
                "gender": "Чоловік",
                "age": 25,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Інженер-механік",
                "baggage": "Набір слюсарних інструментів",
                "hobby": "Аматорська зварка металу",
            },
        },
        {
            "name": "Anna",
            "character": {
                "gender": "Жінка",
                "age": 24,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Будівельник-висотник",
                "baggage": "Великий скотч та ізолента",
                "hobby": "Різьблення по дереву",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert success is True
    assert "Ремонт та укріплення бункера" in report
    assert "BobTheBuilder" in report or "Anna" in report
    assert "витримав" in report


def test_survival_food_and_agronomist_boost_resources():
    """Перевірка: агроном та запаси їжі забезпечують стабільність ресурсів."""
    bunker_info = {
        "years": 10,
        "durability": 70,
        "condition": "Задовільний стан",
        "resources": "Критичний мінімум (значна нестача води)",
    }
    alive_players = [
        {
            "name": "Farmer",
            "character": {
                "gender": "Чоловік",
                "age": 30,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Агроном-гідропонік",
                "baggage": "Мішок насіння пшениці",
                "hobby": "Органічне садівництво",
            },
        },
        {
            "name": "Chef",
            "character": {
                "gender": "Жінка",
                "age": 28,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Шеф-кухар",
                "baggage": "Ящик м'ясних консервів",
                "hobby": "Кулінарія та ферментація їжі",
            },
        },
    ]

    success, report = evaluate_survival("Пекельна посуха", alive_players, bunker_info)
    assert "Продовольча безпека" in report or "Ресурсна автономія" in report
    assert "Farmer" in report or "Chef" in report


def test_survival_doctor_and_medkit_treat_sick_players():
    """Перевірка: наявність лікаря та аптечки стабілізує/виліковує хворих."""
    bunker_info = {
        "years": 4,
        "durability": 60,
        "condition": "Задовільний стан",
        "resources": "Нормальний рівень",
    }
    alive_players = [
        {
            "name": "Doc",
            "character": {
                "gender": "Чоловік",
                "age": 35,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Лікар-хірург",
                "baggage": "Армійська аптечка з антибіотиками",
                "hobby": "Збирання та вивчення лікарських трав",
            },
        },
        {
            "name": "Patient",
            "character": {
                "gender": "Жінка",
                "age": 26,
                "health": "Хронічна астма (потрібен інгалятор)",
                "fact": "Немає",
                "profession": "Вчений-фізик",
                "baggage": "Книга",
                "hobby": "Шахи",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert "Медичне забезпечення" in report or "Стабілізація здоров'я" in report
    assert "Doc" in report


def test_survival_resource_crisis_penalty():
    """Перевірка: дефіцит ресурсів без навичок агрономії чи їжі призводить до штрафу."""
    bunker_info = {
        "years": 10,
        "durability": 80,
        "condition": "Задовільний стан",
        "resources": "Критичний мінімум (значна нестача води)",
    }
    alive_players = [
        {
            "name": "Alex",
            "character": {
                "gender": "Чоловік",
                "age": 25,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Юрист-медіатор",
                "baggage": "Колода карт та кубики",
                "hobby": "Шахи та тактичні ігри",
            },
        },
        {
            "name": "Maria",
            "character": {
                "gender": "Жінка",
                "age": 25,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Вчитель початкових класів",
                "baggage": "Водонепроникний блокнот і олівець",
                "hobby": "Театральне мистецтво (акторство)",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert "Криза ресурсів" in report


def test_survival_energy_and_morale_bonus():
    """Перевірка: сонячна панель/електрик та гітара/психолог дають бонуси до енергонезалежності та моралі."""
    bunker_info = {
        "years": 5,
        "durability": 80,
        "condition": "Задовільний стан",
        "resources": "Нормальний рівень",
    }
    alive_players = [
        {
            "name": "Sparky",
            "character": {
                "gender": "Чоловік",
                "age": 30,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Електрик високої кваліфікації",
                "baggage": "Портативна сонячна панель",
                "hobby": "Аматорська радіоелектроніка",
            },
        },
        {
            "name": "Bard",
            "character": {
                "gender": "Жінка",
                "age": 28,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Психолог-конфліктолог",
                "baggage": "Військова рація (робоча)",
                "hobby": "Гра на акустичній гітарі",
            },
        },
    ]

    success, report = evaluate_survival("Повстання ШІ", alive_players, bunker_info)
    assert "Енергонезалежність та зв'язок" in report
    assert "Моральний дух та згуртованість" in report


def test_survival_terminally_ill_cannot_be_cured_by_doctor():
    """Перевірка: смертельна хвороба не піддається лікуванню навіть за наявності лікаря."""
    bunker_info = {
        "years": 5,
        "durability": 80,
        "condition": "Задовільний стан",
        "resources": "Нормальний рівень",
    }
    alive_players = [
        {
            "name": "SuperDoc",
            "character": {
                "gender": "Чоловік",
                "age": 35,
                "health": "Повністю здоровий(а)",
                "fact": "Немає",
                "profession": "Лікар-хірург",
                "baggage": "Армійська аптечка з антибіотиками",
                "hobby": "Збирання та вивчення лікарських трав",
            },
        },
        {
            "name": "DyingPatient",
            "character": {
                "gender": "Жінка",
                "age": 25,
                "health": "Смертельна хвороба (помре завтра)",
                "fact": "Немає",
                "profession": "Вчений-фізик",
                "baggage": "Книга",
                "hobby": "Шахи",
            },
        },
    ]

    success, report = evaluate_survival("Ядерна зима", alive_players, bunker_info)
    assert "DyingPatient" in report
    assert (
        "Смертельна хвороба" in report or "безсилі" in report or "Невиліковн" in report
    )
