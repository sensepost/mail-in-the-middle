import os
import yaml
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input
from textual.containers import Vertical, Container
from textual.binding import Binding

class NotificationsTab(Vertical):
    CSS_PATH = 'gui.tcss'  # Path to the TCSS file
    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self, global_config_path='config/config.yml'):
        super().__init__()
        # Config file path
        self.global_config_path = global_config_path
        self.config_path = self._get_path_from_config('notifications')

    def _get_path_from_config(self, section):
        """Get the path to the configuration section file."""
        # Load the main configuration file
        with open(self.global_config_path, 'r') as config_file:
            main_config = yaml.safe_load(config_file)
        
        # Get the path for the authentication configuration
        section_config_path = main_config.get(section)
        
        # If the auth_config_path is not absolute, make it relative to the directory of config_path
        if not os.path.isabs(section_config_path):
            global_config_dir = os.path.dirname(self.global_config_path)
            section_config_path = os.path.join(global_config_dir, section_config_path)
        
        return section_config_path
    
    def action_save_config(self):
        """Save the injections configuration to the file."""
        self.save_notifications_information()

    def compose(self) -> ComposeResult:
        """Compose the notifications content."""
        notifications_container = Vertical(
            Container(
                Label("Teams Webhook URL:", id="teams-label"),
                Input(placeholder="<Teams webhook URL>", id="teams-input"),
                classes="notifications-input-grid"
            ),
            Container(
                Label("Discord Webhook URL:", id="discord-label"),
                Input(placeholder="<Discord webhook URL>", id="discord-input"),
                classes="notifications-input-grid"
            ),
            # Container(id='blank-buffer-container'),
            Button(label="Save", variant="primary", id="button-save-notifications"),
            classes="notifications-container"
        )
        yield notifications_container

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_notifications_information()

    async def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "button-save-notifications":
            self.save_notifications_information()

    def read_notifications_information(self):
        """Read and populate the data from the notifications.yml config file."""
        if not os.path.exists(self.config_path):
            return  # No config file exists yet, nothing to load

        # Load the YAML configuration file
        with open(self.config_path, "r") as yaml_file:
            config_data = yaml.safe_load(yaml_file)

        # Populate Teams input field
        teams_webhook = ''
        discord_webhook = ''
        if (config_data is not None):
            if ("teams" in config_data.keys()):
                teams_webhook = config_data.get("teams", "").strip()
            if ("discord" in config_data.keys()):
                discord_webhook = config_data.get("discord", "").strip()

        self.query_one("#teams-input", Input).value = teams_webhook
        self.query_one("#discord-input", Input).value = discord_webhook

    def save_notifications_information(self):
        """Save the webhook URLs to the notifications.yml config file."""
        discord_webhook = self.query_one("#discord-input", Input).value
        teams_webhook = self.query_one("#teams-input", Input).value

        notifications_config = {}
        if (discord_webhook.strip() != ''):
            notifications_config["discord"]=discord_webhook
        if (teams_webhook.strip() != ''):
            notifications_config["teams"] = teams_webhook

        # Save to a YAML file
        with open(self.config_path, "w") as yaml_file:
            if (len(notifications_config)>0):
                yaml.dump(notifications_config, yaml_file, default_flow_style=False)
            else:
                yaml_file.write("")

        print(f"Notifications saved to {self.config_path}")
