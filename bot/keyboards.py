from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .i18n import SUPPORTED_LANGUAGES, t


def language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=code.upper(), callback_data=f"lang_{code}")]
        for code in SUPPORTED_LANGUAGES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sex_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=t(lang, "sex_m"))],
        [KeyboardButton(text=t(lang, "sex_f"))],
        [KeyboardButton(text=t(lang, "sex_other"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def activity_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=t(lang, "activity_low"))],
        [KeyboardButton(text=t(lang, "activity_medium"))],
        [KeyboardButton(text=t(lang, "activity_high"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def nutrition_goal_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=t(lang, "goal_weight_loss"))],
        [KeyboardButton(text=t(lang, "goal_maintenance"))],
        [KeyboardButton(text=t(lang, "goal_weight_gain"))],
        [KeyboardButton(text=t(lang, "goal_symptom_control"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def skip_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "skip"))]], resize_keyboard=True, one_time_keyboard=True
    )


def none_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "none_button"))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text=t(lang, "menu_log_meal")),
            KeyboardButton(text=t(lang, "menu_photo_meal")),
        ],
        [KeyboardButton(text=t(lang, "menu_water")), KeyboardButton(text=t(lang, "menu_weight"))],
        [KeyboardButton(text=t(lang, "menu_stats"))],
        [KeyboardButton(text=t(lang, "btn_fridge")), KeyboardButton(text=t(lang, "btn_budget"))],
        [KeyboardButton(text=t(lang, "btn_recipes"))],
        [KeyboardButton(text=t(lang, "menu_ask_dietitian"))],
        [KeyboardButton(text=t(lang, "btn_profile"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def profile_edit_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t(lang, "profile_field_weight"), callback_data="edit_weight")],
        [InlineKeyboardButton(text=t(lang, "profile_field_height"), callback_data="edit_height")],
        [InlineKeyboardButton(text=t(lang, "profile_field_activity_level"), callback_data="edit_activity")],
        [InlineKeyboardButton(text=t(lang, "profile_field_nutrition_goal"), callback_data="edit_goal")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def meal_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t(lang, "meal_type_breakfast"), callback_data="mealtype_breakfast")],
        [InlineKeyboardButton(text=t(lang, "meal_type_lunch"), callback_data="mealtype_lunch")],
        [InlineKeyboardButton(text=t(lang, "meal_type_dinner"), callback_data="mealtype_dinner")],
        [InlineKeyboardButton(text=t(lang, "meal_type_snack"), callback_data="mealtype_snack")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def water_presets_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t(lang, "water_preset_200"), callback_data="water_ml_200")],
        [InlineKeyboardButton(text=t(lang, "water_preset_250"), callback_data="water_ml_250")],
        [InlineKeyboardButton(text=t(lang, "water_preset_300"), callback_data="water_ml_300")],
        [InlineKeyboardButton(text=t(lang, "water_preset_500"), callback_data="water_ml_500")],
        [InlineKeyboardButton(text=t(lang, "water_other_amount"), callback_data="water_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
