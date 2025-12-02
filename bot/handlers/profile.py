from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from .. import db
from ..i18n import t
from ..keyboards import activity_keyboard, main_menu, nutrition_goal_keyboard, profile_edit_keyboard
from ..models import (
    BiometryEntry,
    DietPreferences,
    DiseaseHistory,
    HealthExamination,
    LabResultItem,
    LabResultSet,
    Medication,
    Supplement,
    SymptomEntry,
    User,
)

router = Router()


class EditProfile(StatesGroup):
    waiting_weight = State()
    waiting_height = State()
    waiting_activity = State()
    waiting_goal = State()


class ExaminationManual(StatesGroup):
    waiting_type = State()
    waiting_region = State()
    waiting_date = State()
    waiting_summary = State()


class LabManual(StatesGroup):
    waiting_date = State()
    waiting_lab_name = State()
    waiting_items = State()


class DocumentUpload(StatesGroup):
    waiting_file = State()


class SymptomFlow(StatesGroup):
    waiting_description = State()
    waiting_severity = State()
    waiting_location = State()
    waiting_triggers = State()
    waiting_meal_flag = State()


class DiseaseFlow(StatesGroup):
    waiting_name = State()
    waiting_year = State()
    waiting_notes = State()


class MedicationFlow(StatesGroup):
    waiting_name = State()
    waiting_dosage = State()
    waiting_schedule = State()
    waiting_indication = State()
    waiting_start = State()
    waiting_end = State()
    waiting_current = State()


class SupplementFlow(StatesGroup):
    waiting_name = State()
    waiting_dosage = State()
    waiting_schedule = State()
    waiting_purpose = State()
    waiting_current = State()


class DietFlow(StatesGroup):
    forbidden = State()
    limited = State()
    preferred = State()
    notes = State()


class BiometryFlow(StatesGroup):
    weight = State()
    waist = State()
    bp = State()
    hr = State()


# ---------- keyboards ----------


def profile_sections_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Обследования", callback_data="section_exams"),
            InlineKeyboardButton(text="Анализы", callback_data="section_labs"),
        ],
        [
            InlineKeyboardButton(text="Симптомы", callback_data="section_symptoms"),
            InlineKeyboardButton(text="История болезней", callback_data="section_history"),
        ],
        [
            InlineKeyboardButton(text="Лекарства", callback_data="section_meds"),
            InlineKeyboardButton(text="БАДы", callback_data="section_supps"),
        ],
        [
            InlineKeyboardButton(text="Диета", callback_data="section_diet"),
            InlineKeyboardButton(text="Биометрия", callback_data="section_biometry"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manual_upload_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить вручную", callback_data=f"{prefix}_manual")],
            [InlineKeyboardButton(text="Отправить фото/файл", callback_data=f"{prefix}_upload")],
        ]
    )


def yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def symptom_meal_keyboard() -> InlineKeyboardMarkup:
    return yes_no_keyboard("symptom_meal")


def current_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return yes_no_keyboard(prefix)


# ---------- helpers ----------


async def _load_user(bot: object, telegram_id: int) -> User | None:
    async with db.async_session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


def _parse_date(text: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except Exception:
            continue
    return None


def _parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except Exception:
        return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _parse_bp(text: str) -> tuple[int | None, int | None]:
    if "/" in text:
        parts = text.split("/", 1)
        return _parse_int(parts[0].strip()), _parse_int(parts[1].strip())
    return None, None


def _format_profile(user: User) -> str:
    def display(value: Any) -> str:
        return str(value) if value else "-"

    return "\n".join(
        [
            "Основные данные:",
            f"Пол: {display(user.sex)}",
            f"Дата рождения: {display(user.date_of_birth)}",
            f"Рост (см): {display(user.height_cm)}",
            f"Вес (кг): {display(user.current_weight_kg)}",
            f"Целевой вес (кг): {display(user.goal_weight_kg)}",
            f"Проблемы ЖКТ: {display(user.gi_diagnoses)}",
            f"Диагнозы: {display(user.other_diagnoses)}",
            f"Лекарства: {display(user.medications)}",
            f"Аллергии/непереносимости: {display(user.allergies_intolerances)}",
            f"Активность: {display(user.activity_level)}",
            f"Цель питания: {display(user.nutrition_goal)}",
        ]
    )


async def _download_bytes(message: Message) -> tuple[bytes | None, str | None]:
    file_id: str | None = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        return None, None

    bot = message.bot
    try:
        file = await bot.get_file(file_id)
        file_obj = await bot.download_file(file.file_path)
        file_bytes = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
        return file_bytes, file_id
    except Exception:
        return None, file_id


# ---------- entry points ----------


async def _show_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        return

    await message.answer(_format_profile(user), reply_markup=profile_edit_keyboard(user.language))
    await message.answer("Профиль: выберите раздел для заполнения/обновления.", reply_markup=profile_sections_keyboard())


@router.message(Command("profile"))
async def view_profile(message: Message, state: FSMContext) -> None:
    await _show_profile(message, state)


async def view_profile_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text.startswith("/profile") or text == "профиль":
        await _show_profile(message, state)


@router.callback_query(F.data == "section_exams")
async def section_exams(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(mode="exams")
    await callback.message.answer("Обследования: выберите способ добавления.", reply_markup=manual_upload_keyboard("exams"))
    await callback.answer()


@router.callback_query(F.data == "exams_manual")
async def exams_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExaminationManual.waiting_type)
    await state.update_data(mode="exams")
    await callback.message.answer("Укажите тип обследования (МРТ, КТ, УЗИ, ФГДС, Колоноскопия, ЭКГ и т.п.).")
    await callback.answer()


@router.message(ExaminationManual.waiting_type)
async def exams_type(message: Message, state: FSMContext) -> None:
    exam_type = (message.text or "").strip()
    if not exam_type:
        await message.answer("Введите тип обследования.")
        return
    await state.update_data(exam_type=exam_type)
    await state.set_state(ExaminationManual.waiting_region)
    await message.answer("Область/регион (например, 'брюшная полость', 'поясница'). Можно пропустить '-'")


@router.message(ExaminationManual.waiting_region)
async def exams_region(message: Message, state: FSMContext) -> None:
    region = (message.text or "").strip()
    await state.update_data(exam_region=None if region == "-" else region)
    await state.set_state(ExaminationManual.waiting_date)
    await message.answer("Дата обследования (ГГГГ-ММ-ДД) или '-' если неизвестно.")


@router.message(ExaminationManual.waiting_date)
async def exams_date(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    exam_date = _parse_date(txt) if txt and txt != "-" else None
    await state.update_data(exam_date=exam_date)
    await state.set_state(ExaminationManual.waiting_summary)
    await message.answer("Краткое заключение по обследованию.")


@router.message(ExaminationManual.waiting_summary)
async def exams_summary(message: Message, state: FSMContext) -> None:
    summary = (message.text or "").strip()
    data = await state.get_data()
    if not summary:
        await message.answer("Введите краткое заключение.")
        return

    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        await state.clear()
        return

    async with db.async_session_maker() as session:
        session.add(
            HealthExamination(
                user_id=user.id,
                type=data.get("exam_type"),
                body_region=data.get("exam_region"),
                date=data.get("exam_date"),
                summary=summary,
                raw_text=summary,
                file_id=None,
            )
        )
        await session.commit()

    await message.answer("Обследование сохранено.", reply_markup=main_menu(user.language))
    await state.clear()


@router.callback_query(F.data == "exams_upload")
async def exams_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DocumentUpload.waiting_file)
    await state.update_data(mode="exams")
    await callback.message.answer("Отправьте фото или файл с результатом обследования.")
    await callback.answer()


@router.callback_query(F.data == "section_labs")
async def section_labs(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(mode="labs")
    await callback.message.answer("Анализы: выберите способ добавления.", reply_markup=manual_upload_keyboard("labs"))
    await callback.answer()


@router.callback_query(F.data == "labs_manual")
async def labs_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LabManual.waiting_date)
    await state.update_data(mode="labs")
    await callback.message.answer("Дата сдачи (ГГГГ-ММ-ДД) или '-' если неизвестно.")
    await callback.answer()


@router.message(LabManual.waiting_date)
async def labs_date(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    lab_date = _parse_date(txt) if txt and txt != "-" else None
    await state.update_data(lab_date=lab_date)
    await state.set_state(LabManual.waiting_lab_name)
    await message.answer("Лаборатория (можно пропустить '-'):")


@router.message(LabManual.waiting_lab_name)
async def labs_lab_name(message: Message, state: FSMContext) -> None:
    lab_name = (message.text or "").strip()
    await state.update_data(lab_name=None if lab_name == "-" else lab_name)
    await state.set_state(LabManual.waiting_items)
    await message.answer(
        "Перечень показателей (каждый с новой строки в формате 'Название: значение единицы (референс) [флаг]')."
    )


def _parse_lab_lines(text: str) -> list[dict[str, Any]]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items: list[dict[str, Any]] = []
    for line in lines:
        name_part, _, rest = line.partition(":")
        if not rest:
            continue
        name = name_part.strip()
        value_part = rest.strip()
        flag = None
        if value_part.endswith("]") and "[" in value_part:
            flag = value_part[value_part.rfind("[") + 1 : -1]
            value_part = value_part[: value_part.rfind("[")].strip()
        unit = None
        reference_range = None
        if "(" in value_part and value_part.endswith(")"):
            main_value, ref = value_part.split("(", 1)
            value_part = main_value.strip()
            reference_range = ref[:-1].strip()
        parts = value_part.split()
        value = parts[0] if parts else value_part
        if len(parts) > 1:
            unit = parts[1]
        items.append(
            {
                "analyte_name": name,
                "value": value,
                "unit": unit,
                "reference_range": reference_range,
                "flag": flag,
            }
        )
    return items


@router.message(LabManual.waiting_items)
async def labs_items(message: Message, state: FSMContext) -> None:
    items_text = (message.text or "").strip()
    data = await state.get_data()
    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        await state.clear()
        return

    items = _parse_lab_lines(items_text)
    async with db.async_session_maker() as session:
        lab_set = LabResultSet(
            user_id=user.id,
            date=data.get("lab_date"),
            lab_name=data.get("lab_name"),
            raw_text=items_text,
        )
        session.add(lab_set)
        await session.flush()
        for item in items:
            session.add(
                LabResultItem(
                    set_id=lab_set.id,
                    analyte_name=item.get("analyte_name"),
                    value=item.get("value", ""),
                    unit=item.get("unit"),
                    reference_range=item.get("reference_range"),
                    flag=item.get("flag"),
                )
            )
        await session.commit()

    await message.answer("Анализы сохранены.", reply_markup=main_menu(user.language))
    await state.clear()


@router.callback_query(F.data == "labs_upload")
async def labs_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DocumentUpload.waiting_file)
    await state.update_data(mode="labs")
    await callback.message.answer("Отправьте фото или файл с анализами.")
    await callback.answer()


@router.message(DocumentUpload.waiting_file, F.photo | F.document)
async def handle_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode")
    file_bytes, file_id = await _download_bytes(message)
    parser = getattr(message.bot, "document_parser", None)

    text = ""
    if parser and file_bytes:
        text = await parser.extract_text_from_image(file_bytes)
    if not text and message.caption:
        text = message.caption

    classification = await parser.classify_document(text) if parser and text else mode

    if mode == "labs" or classification == "lab_report":
        parsed_items = await parser.parse_lab_report(text) if parser else []
        summary_lines = [f"- {i.get('analyte_name')}: {i.get('value')} {i.get('unit') or ''}".strip() for i in parsed_items]
        summary = "Распознаны анализы:\n" + ("\n".join(summary_lines) if summary_lines else "нет данных")
        await state.update_data(parsed_items=parsed_items, raw_text=text, file_id=file_id, mode="labs")
        await message.answer(summary, reply_markup=yes_no_keyboard("doc_confirm_labs"))
    else:
        parsed_exam = await parser.parse_examination_report(text) if parser else {}
        summary = "Обследование:\n" + "\n".join(
            [
                f"Тип: {parsed_exam.get('type')}",
                f"Регион: {parsed_exam.get('body_region')}",
                f"Дата: {parsed_exam.get('date')}",
                f"Заключение: {parsed_exam.get('summary')}",
            ]
        )
        await state.update_data(parsed_exam=parsed_exam, raw_text=text, file_id=file_id, mode="exams")
        await message.answer(summary, reply_markup=yes_no_keyboard("doc_confirm_exams"))


@router.callback_query(F.data.startswith("doc_confirm_labs"))
async def confirm_labs(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice = callback.data.split(":", 1)
    data = await state.get_data()
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    if choice == "yes":
        items = data.get("parsed_items") or []
        raw_text = data.get("raw_text")
        async with db.async_session_maker() as session:
            lab_set = LabResultSet(user_id=user.id, raw_text=raw_text)
            session.add(lab_set)
            await session.flush()
            for item in items:
                session.add(
                    LabResultItem(
                        set_id=lab_set.id,
                        analyte_name=item.get("analyte_name", ""),
                        value=str(item.get("value", "")),
                        unit=item.get("unit"),
                        reference_range=item.get("reference_range"),
                        flag=item.get("flag"),
                    )
                )
            await session.commit()
        await callback.message.answer("Анализы сохранены.", reply_markup=main_menu(user.language))
    else:
        await callback.message.answer("Сохранение отменено.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("doc_confirm_exams"))
async def confirm_exams(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice = callback.data.split(":", 1)
    data = await state.get_data()
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    if choice == "yes":
        exam = data.get("parsed_exam") or {}
        async with db.async_session_maker() as session:
            session.add(
                HealthExamination(
                    user_id=user.id,
                    type=exam.get("type") or "Обследование",
                    body_region=exam.get("body_region"),
                    date=_parse_date(exam.get("date")) if isinstance(exam.get("date"), str) else None,
                    summary=exam.get("summary") or (data.get("raw_text") or "")[:500],
                    raw_text=data.get("raw_text"),
                    file_id=data.get("file_id"),
                )
            )
            await session.commit()
        await callback.message.answer("Обследование сохранено.", reply_markup=main_menu(user.language))
    else:
        await callback.message.answer("Сохранение отменено.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "section_symptoms")
async def section_symptoms(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SymptomFlow.waiting_description)
    await callback.message.answer("Опишите жалобу/симптом.")
    await callback.answer()


@router.message(SymptomFlow.waiting_description)
async def symptom_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    if not desc:
        await message.answer("Опишите симптом.")
        return
    await state.update_data(symptom_description=desc)
    await state.set_state(SymptomFlow.waiting_severity)
    await message.answer("Оцените выраженность (0-10) или '-' если не хотите указывать.")


@router.message(SymptomFlow.waiting_severity)
async def symptom_severity(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    severity = _parse_int(txt) if txt and txt != "-" else None
    await state.update_data(symptom_severity=severity)
    await state.set_state(SymptomFlow.waiting_location)
    await message.answer("Локализация (например, эпигастрий) или '-' если не указано.")


@router.message(SymptomFlow.waiting_location)
async def symptom_location(message: Message, state: FSMContext) -> None:
    loc = (message.text or "").strip()
    await state.update_data(symptom_location=None if loc == "-" else loc)
    await state.set_state(SymptomFlow.waiting_triggers)
    await message.answer("Провоцирующие факторы (стресс, еда и т.п.) или '-' если нет.")


@router.message(SymptomFlow.waiting_triggers)
async def symptom_triggers(message: Message, state: FSMContext) -> None:
    triggers = (message.text or "").strip()
    await state.update_data(symptom_triggers=None if triggers == "-" else triggers)
    await state.set_state(SymptomFlow.waiting_meal_flag)
    await message.answer("Связано с приемом пищи?", reply_markup=symptom_meal_keyboard())


@router.callback_query(F.data.startswith("symptom_meal"))
async def symptom_meal(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice = callback.data.split(":", 1)
    with_meal = choice == "yes"
    data = await state.get_data()
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    async with db.async_session_maker() as session:
        session.add(
            SymptomEntry(
                user_id=user.id,
                date_time=datetime.now(timezone.utc),
                location=data.get("symptom_location"),
                description=data.get("symptom_description"),
                severity=data.get("symptom_severity"),
                triggers=data.get("symptom_triggers"),
                associated_with_meal=with_meal,
            )
        )
        await session.commit()
    await callback.message.answer("Жалоба сохранена.", reply_markup=main_menu(user.language))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "section_history")
async def section_history(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DiseaseFlow.waiting_name)
    await callback.message.answer("Название диагноза (например, GERD, IBS-D).")
    await callback.answer()


@router.message(DiseaseFlow.waiting_name)
async def history_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Введите название диагноза.")
        return
    await state.update_data(diagnosis_name=name)
    await state.set_state(DiseaseFlow.waiting_year)
    await message.answer("Год установки диагноза (или '-' если не указано).")


@router.message(DiseaseFlow.waiting_year)
async def history_year(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    year = _parse_int(txt) if txt and txt != "-" else None
    await state.update_data(diagnosis_year=year)
    await state.set_state(DiseaseFlow.waiting_notes)
    await message.answer("Дополнительные примечания (можно '-' ).")


@router.message(DiseaseFlow.waiting_notes)
async def history_notes(message: Message, state: FSMContext) -> None:
    notes = (message.text or "").strip()
    data = await state.get_data()
    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        await state.clear()
        return
    async with db.async_session_maker() as session:
        session.add(
            DiseaseHistory(
                user_id=user.id,
                diagnosis_name=data.get("diagnosis_name"),
                year_diagnosed=data.get("diagnosis_year"),
                notes=None if notes == "-" else notes,
            )
        )
        await session.commit()
    await message.answer("Диагноз сохранен.", reply_markup=main_menu(user.language))
    await state.clear()


@router.callback_query(F.data == "section_meds")
async def section_meds(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MedicationFlow.waiting_name)
    await callback.message.answer("Название лекарства.")
    await callback.answer()


@router.message(MedicationFlow.waiting_name)
async def meds_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Введите название.")
        return
    await state.update_data(med_name=name)
    await state.set_state(MedicationFlow.waiting_dosage)
    await message.answer("Дозировка (например, 20 мг) или '-'.")


@router.message(MedicationFlow.waiting_dosage)
async def meds_dosage(message: Message, state: FSMContext) -> None:
    dosage = (message.text or "").strip()
    await state.update_data(med_dosage=None if dosage == "-" else dosage)
    await state.set_state(MedicationFlow.waiting_schedule)
    await message.answer("Схема/кратность (например, 1-0-1) или '-'.")


@router.message(MedicationFlow.waiting_schedule)
async def meds_schedule(message: Message, state: FSMContext) -> None:
    schedule = (message.text or "").strip()
    await state.update_data(med_schedule=None if schedule == "-" else schedule)
    await state.set_state(MedicationFlow.waiting_indication)
    await message.answer("Показание/зачем (можно '-').")


@router.message(MedicationFlow.waiting_indication)
async def meds_indication(message: Message, state: FSMContext) -> None:
    indication = (message.text or "").strip()
    await state.update_data(med_indication=None if indication == "-" else indication)
    await state.set_state(MedicationFlow.waiting_start)
    await message.answer("Дата начала (ГГГГ-ММ-ДД) или '-'.")


@router.message(MedicationFlow.waiting_start)
async def meds_start(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    start_date = _parse_date(txt) if txt and txt != "-" else None
    await state.update_data(med_start=start_date)
    await state.set_state(MedicationFlow.waiting_end)
    await message.answer("Дата окончания (ГГГГ-ММ-ДД) или '-' если продолжается.")


@router.message(MedicationFlow.waiting_end)
async def meds_end(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    end_date = _parse_date(txt) if txt and txt != "-" else None
    await state.update_data(med_end=end_date)
    await state.set_state(MedicationFlow.waiting_current)
    await message.answer("Прием продолжается?", reply_markup=current_keyboard("med_current"))


@router.callback_query(F.data.startswith("med_current"))
async def meds_current(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice = callback.data.split(":", 1)
    is_current = choice == "yes"
    data = await state.get_data()
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    async with db.async_session_maker() as session:
        session.add(
            Medication(
                user_id=user.id,
                name=data.get("med_name"),
                dosage=data.get("med_dosage"),
                schedule=data.get("med_schedule"),
                indication=data.get("med_indication"),
                start_date=data.get("med_start"),
                end_date=data.get("med_end"),
                is_current=is_current,
            )
        )
        await session.commit()
    await callback.message.answer("Лекарство сохранено.", reply_markup=main_menu(user.language))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "section_supps")
async def section_supps(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupplementFlow.waiting_name)
    await callback.message.answer("Название БАДа.")
    await callback.answer()


@router.message(SupplementFlow.waiting_name)
async def supp_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Введите название.")
        return
    await state.update_data(supp_name=name)
    await state.set_state(SupplementFlow.waiting_dosage)
    await message.answer("Дозировка (можно '-').")


@router.message(SupplementFlow.waiting_dosage)
async def supp_dosage(message: Message, state: FSMContext) -> None:
    dosage = (message.text or "").strip()
    await state.update_data(supp_dosage=None if dosage == "-" else dosage)
    await state.set_state(SupplementFlow.waiting_schedule)
    await message.answer("Схема приема (можно '-').")


@router.message(SupplementFlow.waiting_schedule)
async def supp_schedule(message: Message, state: FSMContext) -> None:
    schedule = (message.text or "").strip()
    await state.update_data(supp_schedule=None if schedule == "-" else schedule)
    await state.set_state(SupplementFlow.waiting_purpose)
    await message.answer("Цель/показание (можно '-').")


@router.message(SupplementFlow.waiting_purpose)
async def supp_purpose(message: Message, state: FSMContext) -> None:
    purpose = (message.text or "").strip()
    await state.update_data(supp_purpose=None if purpose == "-" else purpose)
    await state.set_state(SupplementFlow.waiting_current)
    await message.answer("Прием продолжается?", reply_markup=current_keyboard("supp_current"))


@router.callback_query(F.data.startswith("supp_current"))
async def supp_current(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice = callback.data.split(":", 1)
    is_current = choice == "yes"
    data = await state.get_data()
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    async with db.async_session_maker() as session:
        session.add(
            Supplement(
                user_id=user.id,
                name=data.get("supp_name"),
                dosage=data.get("supp_dosage"),
                schedule=data.get("supp_schedule"),
                purpose=data.get("supp_purpose"),
                is_current=is_current,
            )
        )
        await session.commit()
    await callback.message.answer("БАД сохранен.", reply_markup=main_menu(user.language))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "section_diet")
async def section_diet(callback: CallbackQuery, state: FSMContext) -> None:
    user = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await callback.answer()
        return
    # show current prefs
    async with db.async_session_maker() as session:
        prefs = await session.scalar(select(DietPreferences).where(DietPreferences.user_id == user.id))
    text = "Текущие предпочтения:\n"
    if prefs:
        text += "\n".join(
            [
                f"Запрещено: {prefs.forbidden_foods or '-'}",
                f"Ограничено: {prefs.limited_foods or '-'}",
                f"Предпочтительно: {prefs.preferred_foods or '-'}",
                f"Заметки: {prefs.notes or '-'}",
            ]
        )
    else:
        text += "не заполнено."
    await state.set_state(DietFlow.forbidden)
    await callback.message.answer(text + "\n\nЗаполните новые значения. Оставьте '-' чтобы пропустить.",)
    await callback.message.answer("Продукты, которые нельзя:")
    await callback.answer()


@router.message(DietFlow.forbidden)
async def diet_forbidden(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(diet_forbidden=None if val == "-" else val)
    await state.set_state(DietFlow.limited)
    await message.answer("Продукты/группы, которые ограничены:")


@router.message(DietFlow.limited)
async def diet_limited(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(diet_limited=None if val == "-" else val)
    await state.set_state(DietFlow.preferred)
    await message.answer("Предпочтительные продукты:")


@router.message(DietFlow.preferred)
async def diet_preferred(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(diet_preferred=None if val == "-" else val)
    await state.set_state(DietFlow.notes)
    await message.answer("Заметки по диете (можно '-').")


@router.message(DietFlow.notes)
async def diet_notes(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    data = await state.get_data()
    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        await state.clear()
        return
    async with db.async_session_maker() as session:
        prefs = await session.scalar(select(DietPreferences).where(DietPreferences.user_id == user.id))
        if not prefs:
            prefs = DietPreferences(user_id=user.id)
            session.add(prefs)
            await session.flush()
        prefs.forbidden_foods = data.get("diet_forbidden")
        prefs.limited_foods = data.get("diet_limited")
        prefs.preferred_foods = data.get("diet_preferred")
        prefs.notes = None if val == "-" else val
        await session.commit()
    await message.answer("Диетические предпочтения сохранены.", reply_markup=main_menu(user.language))
    await state.clear()


@router.callback_query(F.data == "section_biometry")
async def section_biometry(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BiometryFlow.weight)
    await callback.message.answer("Вес (кг) или '-' если пропустить.")
    await callback.answer()


@router.message(BiometryFlow.weight)
async def biometry_weight(message: Message, state: FSMContext) -> None:
    weight = _parse_float((message.text or "").strip()) if message.text and message.text.strip() != "-" else None
    await state.update_data(bio_weight=weight)
    await state.set_state(BiometryFlow.waist)
    await message.answer("Талия (см) или '-'.")


@router.message(BiometryFlow.waist)
async def biometry_waist(message: Message, state: FSMContext) -> None:
    waist = _parse_float((message.text or "").strip()) if message.text and message.text.strip() != "-" else None
    await state.update_data(bio_waist=waist)
    await state.set_state(BiometryFlow.bp)
    await message.answer("Давление (формат 120/80) или '-'.")


@router.message(BiometryFlow.bp)
async def biometry_bp(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip() if message.text else ""
    if txt == "-":
        sys_bp, dia_bp = None, None
    else:
        sys_bp, dia_bp = _parse_bp(txt)
    await state.update_data(bio_sys=sys_bp, bio_dia=dia_bp)
    await state.set_state(BiometryFlow.hr)
    await message.answer("Пульс (уд/мин) или '-'.")


@router.message(BiometryFlow.hr)
async def biometry_hr(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip() if message.text else ""
    hr = _parse_int(txt) if txt and txt != "-" else None
    data = await state.get_data()
    user = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t("en", "profile_missing"))
        await state.clear()
        return

    async with db.async_session_maker() as session:
        session.add(
            BiometryEntry(
                user_id=user.id,
                date_time=datetime.now(timezone.utc),
                weight_kg=data.get("bio_weight"),
                waist_cm=data.get("bio_waist"),
                systolic_bp=data.get("bio_sys"),
                diastolic_bp=data.get("bio_dia"),
                heart_rate=hr,
            )
        )
        await session.commit()
    await message.answer("Биометрия сохранена.", reply_markup=main_menu(user.language))
    await state.clear()


# ---------- сохраняем совместимость старого редактирования ----------


@router.callback_query(F.data == "edit_weight")
async def edit_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await _set_edit_state(callback, state, EditProfile.waiting_weight)


@router.callback_query(F.data == "edit_height")
async def edit_height(callback: CallbackQuery, state: FSMContext) -> None:
    await _set_edit_state(callback, state, EditProfile.waiting_height)


@router.callback_query(F.data == "edit_activity")
async def edit_activity(callback: CallbackQuery, state: FSMContext) -> None:
    await _set_edit_state(callback, state, EditProfile.waiting_activity, keyboard=activity_keyboard)


@router.callback_query(F.data == "edit_goal")
async def edit_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await _set_edit_state(callback, state, EditProfile.waiting_goal, keyboard=nutrition_goal_keyboard)


async def _set_edit_state(
    callback: CallbackQuery,
    state: FSMContext,
    new_state: State,
    keyboard=None,
) -> None:
    session_maker = db.async_session_maker
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await callback.answer()
        return
    lang = user.language
    await state.set_state(new_state)
    await state.update_data(language=lang)
    reply_markup = keyboard(lang) if keyboard else None
    await callback.message.answer(t(lang, "profile_edit_prompt"), reply_markup=reply_markup)
    await callback.answer()


@router.message(EditProfile.waiting_weight)
async def update_weight(message: Message, state: FSMContext) -> None:
    await _update_numeric_field(message, state, "current_weight_kg")


@router.message(EditProfile.waiting_height)
async def update_height(message: Message, state: FSMContext) -> None:
    await _update_numeric_field(message, state, "height_cm")


@router.message(EditProfile.waiting_activity)
async def update_activity(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    mapping = {
        t(lang, "activity_low").lower(): "low",
        t(lang, "activity_medium").lower(): "medium",
        t(lang, "activity_high").lower(): "high",
    }
    value = mapping.get((message.text or "").strip().lower())
    if value is None:
        await message.answer(t(lang, "ask_activity_level"), reply_markup=activity_keyboard(lang))
        return
    await _save_field(message.bot, message.from_user.id, "activity_level", value)
    await _finish_edit(message, state, lang)


@router.message(EditProfile.waiting_goal)
async def update_goal(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    mapping = {
        t(lang, "goal_weight_loss").lower(): "weight_loss",
        t(lang, "goal_maintenance").lower(): "maintenance",
        t(lang, "goal_weight_gain").lower(): "weight_gain",
        t(lang, "goal_symptom_control").lower(): "symptom_control",
    }
    value = mapping.get((message.text or "").strip().lower())
    if value is None:
        await message.answer(t(lang, "ask_nutrition_goal"), reply_markup=nutrition_goal_keyboard(lang))
        return
    await _save_field(message.bot, message.from_user.id, "nutrition_goal", value)
    await _finish_edit(message, state, lang)


async def _update_numeric_field(message: Message, state: FSMContext, field_name: str) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    value = _parse_float(message.text) if message.text else None
    if value is None:
        await message.answer(t(lang, "invalid_number"))
        return
    await _save_field(message.bot, message.from_user.id, field_name, value)
    await _finish_edit(message, state, lang)


async def _save_field(bot: object, telegram_id: int, field_name: str, value) -> None:
    session_maker = db.async_session_maker
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return
        setattr(user, field_name, value)
        await session.commit()


async def _finish_edit(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "updated"), reply_markup=main_menu(lang))
