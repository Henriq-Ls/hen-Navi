"""Painel lateral do assistente e suas interações locais."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _CONFIGURA_ import LARGURA_DOCK_IA, TEXTO_UI
from _ULTILIDADES_.icones import ico_config, ico_ia


class AiAssistantDock(QDockWidget):
    requestRequested = Signal(str, bool, object)
    cancelRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(TEXTO_UI["ai_title"], parent)
        self.setObjectName("aiAssistantDock")
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(LARGURA_DOCK_IA)
        self._context_key = ""
        self._history_by_context: dict[str, list[dict[str, str]]] = {}
        self._truncated_by_context: dict[str, bool] = {}
        self._busy = False

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.provider_label = QLabel(TEXTO_UI["ai_no_provider"], content)
        self.provider_label.setObjectName("aiProviderLabel")
        self.provider_label.setWordWrap(True)
        header.addWidget(self.provider_label, 1)
        self.settings_button = QPushButton(
            ico_config(),
            TEXTO_UI["ai_settings"],
            content,
        )
        self.settings_button.setToolTip(TEXTO_UI["ai_settings"])
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        header.addWidget(self.settings_button)
        layout.addLayout(header)

        self.location_badge = QLabel("", content)
        self.location_badge.setObjectName("aiLocationBadge")
        layout.addWidget(self.location_badge)

        self.status_label = QLabel(TEXTO_UI["ai_ready"], content)
        self.status_label.setObjectName("aiStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.response_field = QPlainTextEdit(content)
        self.response_field.setObjectName("aiResponse")
        self.response_field.setReadOnly(True)
        self.response_field.setPlaceholderText(TEXTO_UI["ai_response_placeholder"])
        self.response_field.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.response_field, 1)

        self.question_field = QLineEdit(content)
        self.question_field.setObjectName("aiQuestion")
        self.question_field.setPlaceholderText(TEXTO_UI["ai_question_placeholder"])
        self.question_field.returnPressed.connect(self._ask)
        layout.addWidget(self.question_field)

        actions = QHBoxLayout()
        self.summarize_button = QPushButton(
            ico_ia(),
            TEXTO_UI["ai_summarize"],
            content,
        )
        self.summarize_button.clicked.connect(
            lambda: self._submit("", summarize=True)
        )
        actions.addWidget(self.summarize_button)
        self.send_button = QPushButton(TEXTO_UI["ai_send"], content)
        self.send_button.clicked.connect(self._ask)
        actions.addWidget(self.send_button)
        layout.addLayout(actions)

        secondary = QHBoxLayout()
        self.cancel_button = QPushButton(TEXTO_UI["ai_cancel"], content)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancelRequested.emit)
        secondary.addWidget(self.cancel_button)
        self.copy_button = QPushButton(TEXTO_UI["ai_copy"], content)
        self.copy_button.clicked.connect(self.copy_answer)
        secondary.addWidget(self.copy_button)
        self.clear_button = QPushButton(TEXTO_UI["ai_clear"], content)
        self.clear_button.clicked.connect(self.clear_conversation)
        secondary.addWidget(self.clear_button)
        layout.addLayout(secondary)

        self.setWidget(content)

    def set_provider(self, provider: dict | None) -> None:
        if provider is None:
            self.provider_label.setText(TEXTO_UI["ai_no_provider"])
            self.location_badge.setText("")
            return
        model = str(provider.get("model") or TEXTO_UI["ai_model_unselected"])
        self.provider_label.setText(f"{provider.get('name', '')} · {model}")
        is_local = provider.get("kind") == "ollama"
        self.location_badge.setText(
            TEXTO_UI["ai_local_badge"] if is_local else TEXTO_UI["ai_cloud_badge"]
        )

    def set_context_key(self, key: str) -> None:
        if key == self._context_key:
            return
        self._context_key = key
        history = self._history_by_context.get(key, [])
        latest = next(
            (
                item["content"]
                for item in reversed(history)
                if item["role"] == "assistant"
            ),
            "",
        )
        self.response_field.setPlainText(latest)
        self.status_label.setText(
            TEXTO_UI["ai_truncated"]
            if self._truncated_by_context.get(key, False)
            else TEXTO_UI["ai_ready"]
        )

    def release_context(self, key: str) -> None:
        self._history_by_context.pop(key, None)
        self._truncated_by_context.pop(key, None)
        if self._context_key == key:
            self.response_field.clear()

    def current_history(self) -> list[dict[str, str]]:
        return list(self._history_by_context.get(self._context_key, []))

    def set_busy(self, busy: bool, status: str = "") -> None:
        self._busy = bool(busy)
        self.summarize_button.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.question_field.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        if status:
            self.status_label.setText(status)
        elif not busy:
            self.status_label.setText(TEXTO_UI["ai_ready"])

    def show_answer(
        self,
        answer: str,
        *,
        question: str,
        summarize: bool,
        truncated: bool,
        context_key: str | None = None,
    ) -> None:
        context = context_key if context_key is not None else self._context_key
        history = self._history_by_context.setdefault(context, [])
        is_translation = question == TEXTO_UI["ai_translate_prompt"]
        user_message = (
            "Resuma a página."
            if summarize
            else (
                "Traduza a página para português."
                if is_translation
                else question.strip()
            )
        )
        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": answer},
            ]
        )
        self._history_by_context[context] = history[-8:]
        self._truncated_by_context[context] = bool(truncated)
        self.set_busy(False)
        if context == self._context_key:
            self.response_field.setPlainText(answer)
            self.question_field.clear()
            self.status_label.setText(
                TEXTO_UI["ai_truncated"]
                if truncated
                else (
                    TEXTO_UI["ai_translation_done"]
                    if is_translation
                    else TEXTO_UI["ai_ready"]
                )
            )

    def show_error(
        self,
        message: str,
        *,
        context_key: str | None = None,
    ) -> None:
        self.set_busy(False)
        if context_key is None or context_key == self._context_key:
            self.status_label.setText(message)
        else:
            self.status_label.setText(TEXTO_UI["ai_ready"])

    def show_local_notice(self, message: str | None = None) -> None:
        self.status_label.setText(message or TEXTO_UI["ai_local_notice"])

    def request_translation(self) -> None:
        if self._busy:
            self.status_label.setText(TEXTO_UI["ai_request_in_progress"])
            return
        self.requestRequested.emit(
            TEXTO_UI["ai_translate_prompt"],
            False,
            [],
        )

    def _ask(self) -> None:
        self._submit(self.question_field.text(), summarize=False)

    def _submit(self, question: str, *, summarize: bool) -> None:
        if self._busy:
            return
        if not summarize and not question.strip():
            self.status_label.setText(TEXTO_UI["ai_enter_question"])
            self.question_field.setFocus()
            return
        self.requestRequested.emit(
            question.strip(),
            summarize,
            self.current_history(),
        )

    def _cancel(self) -> None:
        self.cancelRequested.emit()

    def copy_answer(self) -> None:
        text = self.response_field.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.status_label.setText(TEXTO_UI["ai_copied"])

    def clear_conversation(self) -> None:
        if self._busy:
            return
        self._history_by_context.pop(self._context_key, None)
        self._truncated_by_context.pop(self._context_key, None)
        self.response_field.clear()
        self.status_label.setText(TEXTO_UI["ai_cleared"])
