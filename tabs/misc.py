import os
import yaml
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, Switch, ListItem, ListView
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.binding import Binding

class MiscTab(Vertical):
    CSS_PATH = 'gui.css'  # Path to the CSS file
    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self, global_config_path='config/config.yml'):
        super().__init__()
        # Config file path
        self.global_config_path = global_config_path
        self.config_path = self._get_path_from_config('misc')

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
        self.save_miscelanea_information()

    def compose(self) -> ComposeResult:
        """Compose the miscelanea tab content."""
        misc_container = VerticalScroll(
            # Fixed Destinations
            Container(
                Label("Fixed Destinations:", id="fixed-destinations-label", classes='filter-form-label'),
                ListView(id="fixed-destinations-listview", classes="miscelanea-listview"),
                Input(placeholder="felipe@mycatchall.com", id="fixed-destination-input"),
                Horizontal(
                    Button("+", id="add-fixed-destination-button", variant="success", tooltip="Add fixed destination"),
                    Button("-", id="remove-fixed-destination-button", variant="error", tooltip="Remove fixed destination")
                ),
                classes="miscelanea-box",
                id="fixed-destinations-box"
            ),
            
            # Sender Details
            Container(
                Label("Other Settings:", id="sender-settings-label", classes='filter-form-label'),
                Horizontal(
                    Label("Spoof original sender:"),
                    Switch(value=False, id="sender-spoof-switch")
                ),
                Horizontal(
                    Label("Fixed Sender:"),
                    Input(placeholder="Microsoft Security <user@phishingdomain.com>", id="sender-fixed-input"),
                    id='fixed-sender-container',
                ),
                Horizontal(
                    Label("Poll Interval (seconds):", id="poll-interval-label"),
                    Input(placeholder="120", id="poll-interval-input", type="number"),
                ),
                Horizontal(
                    Label("Tracking Parameter:", id="tracking-param-label"),
                    Input(placeholder="customerid", id="tracking-param-input"),
                ),
                classes="miscelanea-box",
                id="other-settings-box"
            ),
            
            # Save Button
            Button("Save", variant="primary", id="button-save-miscelanea"),
            classes="miscelanea-container"
        )
        yield misc_container

    async def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "add-fixed-destination-button":
            self.add_fixed_destination_to_list()
        elif event.button.id == "remove-fixed-destination-button":
            self.remove_fixed_destination_from_list()
        elif event.button.id == "button-save-miscelanea":
            self.save_miscelanea_information()

    def add_fixed_destination_to_list(self):
        """Add fixed destination email to the list."""
        email = self.query_one("#fixed-destination-input", Input).value
        if email:
            listview = self.query_one("#fixed-destinations-listview", ListView)
            listview.append(ListItem(Label(email), classes="miscelanea-listitem"))
            self.query_one("#fixed-destination-input", Input).value = ""  # Clear input field

    def remove_fixed_destination_from_list(self):
        """Remove highlighted fixed destination from the list."""
        listview = self.query_one("#fixed-destinations-listview", ListView)
        if listview.highlighted_child:
            listview.highlighted_child.remove()

    def save_miscelanea_information(self):
        """Save miscelanea information to the YAML file."""
        fixed_destinations = [str(item.query_one(Label).renderable) for item in self.query_one("#fixed-destinations-listview", ListView).children]
        sender_spoof = self.query_one("#sender-spoof-switch", Switch).value
        sender_fixed = self.query_one("#sender-fixed-input", Input).value
        poll_interval = int(self.query_one("#poll-interval-input", Input).value)
        tracking_param = self.query_one("#tracking-param-input", Input).value

        misc_data = {
            "fixed_destinations": fixed_destinations,
            "sender": {
                "spoof": sender_spoof,
                "fixed": sender_fixed
            },
            "poll_interval": poll_interval,
            "tracking_param": tracking_param
        }

        # Remove the fixed sender container if spoof is False
        if sender_fixed is None or len(sender_fixed) == 0:
            misc_data["sender"].pop("fixed", None)

        # Save the information to a YAML file
        with open(self.config_path, "w") as yaml_file:
            yaml.dump(misc_data, yaml_file, default_flow_style=False)

        print(f"Miscellaneous information saved to {self.config_path}")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch change events."""
        if event.switch.id == "sender-spoof-switch":
            sfi_element = self.query_one("#fixed-sender-container")
            if event.value and 'hidden' not in sfi_element.classes:
                sfi_element.add_class("hidden")
            else:
                sfi_element.remove_class("hidden")

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_miscelanea_information()

    def read_miscelanea_information(self):
        """Load the miscelanea information from the YAML file (if exists) and populate the form."""
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r") as yaml_file:
            misc_data = yaml.safe_load(yaml_file)

        # Populate fixed destinations list
        fixed_destinations = misc_data.get("fixed_destinations", [])
        listview = self.query_one("#fixed-destinations-listview", ListView)
        for email in fixed_destinations:
            listview.append(ListItem(Label(email), classes="miscelanea-listitem"))

        # Populate sender information
        sender_data = misc_data.get("sender", {})
        self.query_one("#sender-spoof-switch", Switch).value = sender_data.get("spoof", False)
        self.query_one("#sender-fixed-input", Input).value = sender_data.get("fixed", "")

        # Populate poll interval
        self.query_one("#poll-interval-input", Input).value = str(misc_data.get("poll_interval", 120))

        # Populate tracking parameter
        self.query_one("#tracking-param-input", Input).value = misc_data.get("tracking_param", "customerid")
