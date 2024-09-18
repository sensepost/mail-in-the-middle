from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Vertical
from textual.app import ComposeResult
from time import sleep

class FeedbackModal(ModalScreen):
    """A simple modal screen for feedback."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Compose the content of the modal."""
        yield Vertical(
            Static(self.message, id="modal-message"),
            Button("OK", id="modal-ok-button", variant="primary")
        )

    async def on_button_pressed(self, event) -> None:
        """Handle button press in the modal."""
        if event.button.id == "modal-ok-button":
            await self.app.pop_screen()  # Close the modal
