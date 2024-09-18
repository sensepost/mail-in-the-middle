import os
import yaml
import re
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, ListItem, ListView, Static, Switch, Rule
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from datetime import datetime
from textual.binding import Binding

class FilterTab(Vertical):
    CSS_PATH = 'gui.css'  # Path to the CSS file
    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self, global_config_path='config/config.yml'):
        super().__init__()
        self.global_config_path = global_config_path
        self.config_path = self._get_path_from_config('filter')

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
        self.save_filter_information()

    def compose(self) -> ComposeResult:
        """Compose the filter tab layout."""

        # Monitoring Section (Left of second row)
        monitoring_container = VerticalScroll(
            Static("👁️  Monitoring", id='monitoring-label', classes='filter-form-label'),
            Container(
                Label("Subjects:", id='monitor-subjects-label', classes='inner-filter-label'),
                ListView(id='monitor-subjects-listview'),
                Input(placeholder="Add a subject to monitor", id="monitor-subject-input"),
                Horizontal(
                    Button(label="+", variant='success', id='monitor-subject-add-button'),
                    Button(label="-", variant='error', id='monitor-subject-remove-button')
                ),
                classes='filter-box'
            ),
            Container(
                Label("From Domains:", id='monitor-from-domains-label', classes='inner-filter-label'),
                ListView(id='monitor-from-domains-listview'),
                Input(placeholder="Add a 'from' domain to monitor", id="monitor-from-domain-input"),
                Horizontal(
                    Button(label="+", variant='success', id='monitor-from-domain-add-button'),
                    Button(label="-", variant='error', id='monitor-from-domain-remove-button')
                ),
                classes='filter-box'
            ),
            Container(
                Label("To Domains:", id='monitor-to-domains-label', classes='inner-filter-label'),
                ListView(id='monitor-to-domains-listview'),
                Input(placeholder="Add a 'to' domain to monitor", id="monitor-to-domain-input"),
                Horizontal(
                    Button(label="+", variant='success', id='monitor-to-domain-add-button'),
                    Button(label="-", variant='error', id='monitor-to-domain-remove-button')
                ),
                classes='filter-box'
            ),
        )

        # Ignore Section (Right of second row)
        ignore_container = VerticalScroll(
            Static("🙅🏼 Ignore", id='ignore-label', classes='filter-form-label'),
            Container(
                Label("Subjects:", id='ignore-subjects-label', classes='inner-filter-label'),
                ListView(id='ignore-subjects-listview'),
                Input(placeholder="Add a subject to ignore", id="ignore-subject-input"),
                Horizontal(
                    Button(label="+", variant='success', id='ignore-subject-add-button'),
                    Button(label="-", variant='error', id='ignore-subject-remove-button')
                ),
                classes='filter-box'
            ),
            Container(
                Label("From Domains:", id='ignore-from-domains-label', classes='inner-filter-label'),
                ListView(id='ignore-from-domains-listview'),
                Input(placeholder="Add a 'from' domain to ignore", id="ignore-from-domain-input"),
                Horizontal(
                    Button(label="+", variant='success', id='ignore-from-domain-add-button'),
                    Button(label="-", variant='error', id='ignore-from-domain-remove-button')
                ),
                classes='filter-box'
            ),
            Container(
                Label("To Domains:", id='ignore-to-domains-label', classes='inner-filter-label'),
                ListView(id='ignore-to-domains-listview'),
                Input(placeholder="Add a 'to' domain to ignore", id="ignore-to-domain-input"),
                Horizontal(
                    Button(label="+", variant='success', id='ignore-to-domain-add-button'),
                    Button(label="-", variant='error', id='ignore-to-domain-remove-button')
                ),
                classes='filter-box'
            )
        )

        # Save Button (Third row)
        save_button = Button(label="Save", variant="primary", id="button-save-filters")

        # Root Layout: Date Filter, Monitoring (Left), Ignore (Right), and Save Button
        yield VerticalScroll(
            Container(
                Label("Ignore Seen Emails:", id='ignore-seen-emails-label'),
                Switch(value=True, id="ignore-seen-emails-switch"),
                Label("Date Limit (e.g., 2024-03-14 12:00:40+00):", id='date-filter-label'),
                Input(placeholder="2024-03-14 12:00:40+00", id="date-limit-input"),
                classes='filter-first-row'
            ),
            Horizontal(
                monitoring_container,
                Rule(orientation='vertical'),
                ignore_container,
                id="monitor-ignore-split"
            ),
            save_button,
            classes='root-filter-grid',
            id="root-filter-grid"
        )

    async def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "monitor-subject-add-button":
            self.add_item_to_list("monitor-subject")
        elif event.button.id == "monitor-subject-remove-button":
            self.remove_item_from_list("monitor-subject")
        elif event.button.id == "monitor-from-domain-add-button":
            self.add_item_to_list("monitor-from-domain")
        elif event.button.id == "monitor-from-domain-remove-button":
            self.remove_item_from_list("monitor-from-domain")
        elif event.button.id == "monitor-to-domain-add-button":
            self.add_item_to_list("monitor-to-domain")
        elif event.button.id == "monitor-to-domain-remove-button":
            self.remove_item_from_list("monitor-to-domain")
        elif event.button.id == "ignore-subject-add-button":
            self.add_item_to_list("ignore-subject")
        elif event.button.id == "ignore-subject-remove-button":
            self.remove_item_from_list("ignore-subject")
        elif event.button.id == "ignore-from-domain-add-button":
            self.add_item_to_list("ignore-from-domain")
        elif event.button.id == "ignore-from-domain-remove-button":
            self.remove_item_from_list("ignore-from-domain")
        elif event.button.id == "ignore-to-domain-add-button":
            self.add_item_to_list("ignore-to-domain")
        elif event.button.id == "ignore-to-domain-remove-button":
            self.remove_item_from_list("ignore-to-domain")
        elif event.button.id == "button-save-filters":
            self.save_filter_information()

    
    def on_key(self, event):
        """Handle key press events."""
        if event.key == "enter":
            # Check if the focus is on domain or address inputs and add to the corresponding list
            monitor_subject = self.query_one("#monitor-subject-input", Input)
            monitor_from_domain = self.query_one("#monitor-from-domain-input", Input)
            monitor_to_domain = self.query_one("#monitor-to-domain-input", Input)
            ignore_subject = self.query_one("#ignore-subject-input", Input)
            ignore_from_domain = self.query_one("#ignore-from-domain-input", Input)
            ignore_to_domain = self.query_one("#ignore-to-domain-input", Input)

            if (monitor_subject.has_focus):
                self.add_item_to_list("monitor-subject")
            elif (monitor_from_domain.has_focus):
                self.add_item_to_list("monitor-from-domain")
            elif (monitor_to_domain.has_focus):
                self.add_item_to_list("monitor-to-domain")
            elif (ignore_subject.has_focus):
                self.add_item_to_list("ignore-subject")
            elif (ignore_from_domain.has_focus):
                self.add_item_to_list("ignore-from-domain")
            elif (ignore_to_domain.has_focus):
                self.add_item_to_list("ignore-to-domain")

    def add_item_to_list(self, item_type: str):
        """Add an item to the appropriate ListView."""
        if item_type == "monitor-subject":
            # Add quotes to show the spaces
            input_value = "'"+self.query_one("#monitor-subject-input", Input).value+"'"
            listview = self.query_one("#monitor-subjects-listview", ListView)
        elif item_type == "monitor-from-domain":
            input_value = self.query_one("#monitor-from-domain-input", Input).value
            listview = self.query_one("#monitor-from-domains-listview", ListView)
        elif item_type == "monitor-to-domain":
            input_value = self.query_one("#monitor-to-domain-input", Input).value
            listview = self.query_one("#monitor-to-domains-listview", ListView)
        elif item_type == "ignore-subject":
            # Add quotes to show the spaces
            input_value = "'"+self.query_one("#ignore-subject-input", Input).value+"'"
            listview = self.query_one("#ignore-subjects-listview", ListView)
        elif item_type == "ignore-from-domain":
            input_value = self.query_one("#ignore-from-domain-input", Input).value
            listview = self.query_one("#ignore-from-domains-listview", ListView)
        elif item_type == "ignore-to-domain":
            input_value = self.query_one("#ignore-to-domain-input", Input).value
            listview = self.query_one("#ignore-to-domains-listview", ListView)

        if input_value:
            listview.append(ListItem(Label(input_value),classes='filter-listitem'))
            self.query_one(f"#{item_type}-input", Input).value = ""  # Clear the input field

    def remove_item_from_list(self, item_type: str):
        """Remove the selected item from the ListView."""
        if item_type == "monitor-subject":
            listview = self.query_one("#monitor-subjects-listview", ListView)
        elif item_type == "monitor-from-domain":
            listview = self.query_one("#monitor-from-domains-listview", ListView)
        elif item_type == "monitor-to-domain":
            listview = self.query_one("#monitor-to-domains-listview", ListView)
        elif item_type == "ignore-subject":
            listview = self.query_one("#ignore-subjects-listview", ListView)
        elif item_type == "ignore-from-domain":
            listview = self.query_one("#ignore-from-domains-listview", ListView)
        elif item_type == "ignore-to-domain":
            listview = self.query_one("#ignore-to-domains-listview", ListView)

        listview.highlighted_child.remove()  # Remove the highlighted item

    def save_filter_information(self):
        """Save the filter information to a YAML file."""
        remove_quotes = lambda x: re.sub("'$", "", re.sub("^'", "", x))
        # Monitor section
        monitor_subjects = [x for x in [str(item.query_one(Label).renderable) for item in self.query_one("#monitor-subjects-listview", ListView).children]]
        monitor_subjects = list(map(remove_quotes,monitor_subjects))
        monitor_from_domains = [str(item.query_one(Label).renderable) for item in self.query_one("#monitor-from-domains-listview", ListView).children]
        monitor_to_domains = [str(item.query_one(Label).renderable) for item in self.query_one("#monitor-to-domains-listview", ListView).children]
        # Ignore section
        ignore_subjects = [x for x in [str(item.query_one(Label).renderable) for item in self.query_one("#ignore-subjects-listview", ListView).children]]
        ignore_subjects = list(map(remove_quotes,ignore_subjects))
        ignore_from_domains = [str(item.query_one(Label).renderable) for item in self.query_one("#ignore-from-domains-listview", ListView).children]
        ignore_to_domains = [str(item.query_one(Label).renderable) for item in self.query_one("#ignore-to-domains-listview", ListView).children]
        ignore_seen_email = self.query_one("#ignore-seen-emails-switch", Switch).value
        # Save the date limit as datetime
        date_limit = datetime.strptime(self.query_one("#date-limit-input", Input).value, "%Y-%m-%d %H:%M:%S%z")

        filters_data = {
            "monitor": {
                "subject": monitor_subjects,
                "from_domains": monitor_from_domains,
                "to_domains": monitor_to_domains,
            },
            "ignore": {
                "seen_email": ignore_seen_email,
                "subjects": ignore_subjects,
                "from_domains": ignore_from_domains,
                "to_domains": ignore_to_domains,
            },
            "date_limit": date_limit
        }

        # Save the information to a YAML file
        with open(self.config_path, "w") as yaml_file:
            yaml.dump(filters_data, yaml_file, default_flow_style=False)

        print(f"Filters saved to {self.config_path}")

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_filter_information()

    def read_filter_information(self):
        """Load the filter information from the YAML file (if exists) and populate the form."""
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r") as yaml_file:
            filters_data = yaml.safe_load(yaml_file)

        # Populate the date limit field
        self.query_one("#date-limit-input", Input).value = str(filters_data.get("date_limit", ""))

        # Populate the monitoring section
        monitor_subjects = ["'"+x+"'" for x in filters_data.get("monitor", {}).get("subject", [])]
        monitor_from_domains = filters_data.get("monitor", {}).get("from_domains", [])
        monitor_to_domains = filters_data.get("monitor", {}).get("to_domains", [])

        # Populate ignore section
        ignore_subjects = ["'"+x+"'" for x in filters_data.get("ignore", {}).get("subjects", [])]
        ignore_from_domains = filters_data.get("ignore", {}).get("from_domains", [])
        ignore_to_domains = filters_data.get("ignore", {}).get("to_domains", [])
        ignore_seen_email = filters_data.get("ignore", {}).get("seen_email", False)

        # Update the monitoring lists
        self.populate_list("#monitor-subjects-listview", monitor_subjects)
        self.populate_list("#monitor-from-domains-listview", monitor_from_domains)
        self.populate_list("#monitor-to-domains-listview", monitor_to_domains)

        # Update the ignore lists
        self.populate_list("#ignore-subjects-listview", ignore_subjects)
        self.populate_list("#ignore-from-domains-listview", ignore_from_domains)
        self.populate_list("#ignore-to-domains-listview", ignore_to_domains)

        # Update ignore seen email switch
        self.query_one("#ignore-seen-emails-switch", Switch).value = ignore_seen_email

    def populate_list(self, listview_id: str, items: list):
        """Populate a ListView with a list of items."""
        listview = self.query_one(listview_id, ListView)
        for item in items:
            listview.append(ListItem(Label(item),classes='filter-listitem'))
