import os
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, ListItem, ListView
from textual.containers import Vertical, Horizontal, Container
from textual.binding import Binding
import yaml

# Define the Authentication tab as its own class
class TyposTab(Vertical):
    # CSS
    CSS_PATH='gui.css'
    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self,global_config_path='config/config.yml'):
        super().__init__()
        # Config file path
        self.global_config_path = global_config_path
        self.config_path = self._get_path_from_config('typos')
        self.selected_address = None
        self.selected_domain = None

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
        self.save_typos_information()

    def compose(self) -> ComposeResult:
        """Typos content."""
        typos_container = Container(
            Container(
                Label("Domains", id='domain-typos-label', classes='inner-typos-label'),                
                ListView(
                    id='domain-typos-listview',
                    classes='typos-listview'
                ),
                Container(  
                    Label("Mistyped: ", id='mistyped-domain-label'),
                    Input(placeholder="domani.com", id="typoed-domain-input"),
                    Label("Corrected: ", id='fixed-domain-label'),
                    Input(placeholder="domain.com", id="fixed-domain-input"),
                    classes='typos-form-data-grid',
                    id='domains-typos-form-data'
                ),
                Horizontal(
                    Button(label="+", variant='success',id='domain-add-button', tooltip='Add a domain typo to fix to the list'),
                    Button(label="-", variant='error', id='domain-remove-button',tooltip='Remove a domain typo to fix from the list'),
                ),
                classes='inner-typos-grid',
                id='domain-typos-box'
            ),
            Container(
                Label("Addresses", id='addresses-typos-label', classes='inner-typos-label'),
                ListView(
                    id='addresses-typos-listview',
                    classes='typos-listview'
                ),
                Container(  
                    Label("Mistyped: ", id='mistyped-address-label'),
                    Input(placeholder="felmoltor@domani.com", id="typoed-address-input"),
                    Label("Corrected: ", id='fixed-address-label'),
                    Input(placeholder="felmoltor@domain.com", id="fixed-address-input"),
                    classes='typos-form-data-grid',
                    id='addresses-typos-form-data'
                ),
                Horizontal(
                    Button(label="+", variant='success', id='address-add-button', tooltip='Add an address typo to fix to the list'),
                    Button(label="-", variant='error', id='address-remove-button', tooltip='Remove an address typo to fix from the list'),
                ),
                classes='inner-typos-grid',
                id='addresses-typos-box'
            ),
            Button("Save", variant="primary", id='button-save-auth'),
            id='outer-typos-grid',
            classes='outer-typos-grid'
        )
        yield typos_container

    
    def save_typos_information(self):
        """Save typos to a YAML file."""
        domain_typos = {}
        address_typos = {}

        # Collect domain typos from the ListView
        domain_listview = self.query_one("#domain-typos-listview", ListView)
        for item in domain_listview.children:
            typo_str = str(item.query_one(Label).renderable)
            mistyped, corrected = typo_str.split(" --> ")
            domain_typos[mistyped] = corrected

        # Collect address typos from the ListView
        address_listview = self.query_one("#addresses-typos-listview", ListView)
        for item in address_listview.children:
            typo_str = str(item.query_one(Label).renderable)
            mistyped, corrected = typo_str.split(" --> ")
            address_typos[mistyped] = corrected

        # Create the YAML structure
        typos_data = {
            "address": address_typos,
            "domain": domain_typos
        }

        # Save to a YAML file
        with open(self.config_path, "w") as yaml_file:
            yaml.dump(typos_data, yaml_file, default_flow_style=False)

        print(f"Typos saved to {self.config_path}")

    def read_typos_information(self):
        """Load the typos from the YAML file (if exists) and populate the ListView."""
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r") as yaml_file:
            typos_data = yaml.safe_load(yaml_file)

        # Load domains into the domain ListView
        domain_listview = self.query_one("#domain-typos-listview", ListView)
        for mistyped, corrected in typos_data.get("domain", {}).items():
            domain_listview.append(ListItem(Label(f"{mistyped} --> {corrected}"), classes="typos-listitem"))

        # Load addresses into the address ListView
        address_listview = self.query_one("#addresses-typos-listview", ListView)
        for mistyped, corrected in typos_data.get("address", {}).items():
            address_listview.append(ListItem(Label(f"{mistyped} --> {corrected}"), classes="typos-listitem"))

    def add_typo_to_list(self, typo_type: str):
        """Add mistyped and corrected input values to the ListView."""
        if typo_type == "domain":
            mistyped = self.query_one("#typoed-domain-input", Input).value
            corrected = self.query_one("#fixed-domain-input", Input).value
            listview = self.query_one("#domain-typos-listview", ListView)
        elif typo_type == "address":
            mistyped = self.query_one("#typoed-address-input", Input).value
            corrected = self.query_one("#fixed-address-input", Input).value
            listview = self.query_one("#addresses-typos-listview", ListView)

        if mistyped and corrected:
            listview.append(ListItem(Label(f"{mistyped} --> {corrected}"), classes="typos-listitem"))
            # Clear the input fields after adding to the list
            self.query_one(f"#typoed-{typo_type}-input", Input).value = ""
            self.query_one(f"#fixed-{typo_type}-input", Input).value = ""

    def remove_typo_to_list(self, typo_type: str):
        """Add mistyped and corrected input values to the ListView."""
        if typo_type == "domain":
            listview = self.query_one("#domain-typos-listview", ListView)
        elif typo_type == "address":
            listview = self.query_one("#addresses-typos-listview", ListView)

        listview.highlighted_child.remove()

    def on_key(self, event):
        """Handle key press events."""
        if event.key == "enter":
            # Check if the focus is on domain or address inputs and add to the corresponding list
            domain_mistyped_input = self.query_one("#typoed-domain-input", Input)
            domain_corrected_input = self.query_one("#fixed-domain-input", Input)
            address_mistyped_input = self.query_one("#typoed-address-input", Input)
            address_corrected_input = self.query_one("#fixed-address-input", Input)

            # If the focus is on any domain-related input
            if domain_mistyped_input.has_focus or domain_corrected_input.has_focus:
                self.add_typo_to_list("domain")
            # If the focus is on any address-related input
            elif address_mistyped_input.has_focus or address_corrected_input.has_focus:
                self.add_typo_to_list("address")
        

    async def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "address-add-button":
            self.add_typo_to_list("address")
        elif event.button.id == "domain-add-button":
            self.add_typo_to_list("domain")
        elif event.button.id == "address-remove-button":
            self.remove_typo_to_list("address")
        elif event.button.id == "domain-remove-button":
            self.remove_typo_to_list("domain")
        elif event.button.id == "button-save-auth":
            self.save_typos_information()

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_typos_information() 
    