import os
import yaml
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, ListItem, ListView, Static, Select
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.binding import Binding

class InjectionsTab(Vertical):
    CSS_PATH = 'gui.css'  # Path to the CSS file

    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self, global_config_path='config/config.yml'):
        super().__init__()
        # Config file path
        self.global_config_path = global_config_path
        self.config_path = self._get_path_from_config('injections')

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

    def compose(self) -> ComposeResult:
        """Compose the injections content."""
        injections_container = VerticalScroll(
            # Links section
            VerticalScroll(
                Static("Links", id='links-label', classes='inner-injections-label'),
                ListView(id='links-listview', classes='injections-listviews'),
                Select(id='replacement-type-select', options=[('all','all'),('domain','domain')], classes='injections-form-select'),
                Container(
                    Label("URL:", id='link-url-label', classes='injections-form-label'),
                    Input(placeholder="https://www.notaphish.com/login", id="link-url-input-all"),
                    classes='injections-link-all-input',
                    id='links-all-injection-form'
                ),
                Container(
                    Label("Domain:", id='link-domain-label', classes='injections-form-label'),
                    Input(placeholder="microsoftonline.com", id="link-domain-input"),
                    Label("URL:", id='link-url-label', classes='injections-form-label'),
                    Input(placeholder="https://www.notaphish.com/login", id="link-url-input-domain"),
                    classes='injections-link-domain-input',
                    id='links-domain-injection-form'
                ),
                Horizontal(
                    Button(label="+", variant='success', id='link-add-button', tooltip='Add a link to the list'),
                    Button(label="-", variant='error', id='link-remove-button', tooltip='Remove a link from the list'),
                    classes='injections-form-buttons',
                    id='links-injection-buttons'
                ),
                classes='injections-box injections-listsviews-box',
                id='links-box'
            ),

            # Headers section
            VerticalScroll(
                Static("Headers", id='headers-label', classes='inner-injections-label'),
                ListView(id='headers-listview', classes='injections-listviews'),
                Container(
                    Label("Header Key:", classes='injections-form-label'),
                    Input(placeholder="X-Header-Name", id="header-key-input"),
                    Label("Header Value:", classes='injections-form-label'),
                    Input(placeholder="Your header value", id="header-value-input"),
                    classes='injections-headers-input',
                    id='headers-injection-form'
                ),
                Horizontal(
                    Button(label="+", variant='success', id='header-add-button', tooltip='Add a header to inject'),
                    Button(label="-", variant='error', id='header-remove-button', tooltip='Remove a header from the injection list'),
                    classes='injections-form-buttons',
                    id='headers-injection-buttons'
                ),
                classes='injections-box injections-listsviews-box',
                id='headers-box'
            ),
            # Attachments section
            Container(
                Static("Attachments", id='attachments-label', classes='inner-injections-label'),
                Container(
                    Label("Attachment Path:", id='attachment-path-label'),
                    Input(placeholder="attachments/document.pdf.zip", id="attachment-path-input"),
                    Label("Attachment Message:", id='attachment-message-label'),
                    Input(placeholder="Use the password 'documentation' to access...", id="attachment-message-input"),
                    classes='injections-form-data-grid',
                    id='attachments-injection-form'
                ),
                classes='injections-box injections-box-attachments',
                id='attachments-box'
            ),

            # Tracking URL and UNC Path
            Container(
                Static("Other", id='other-label', classes='inner-injections-label'),
                Container(
                    Label("Tracking URL:", id='tracking-url-label'),
                    Input(placeholder="https://www.domain.com/login?param=1", id="tracking-url-input"),
                    Label("UNC Path:", id='unc-path-label'),
                    Input(placeholder="\\\\42.42.42.42\\file.png", id="unc-path-input"),
                    classes='injections-form-data-grid',
                    id='other-injection-form'
                ),
                classes='injections-box injections-box-other',
                id='other-box'
            ),

            # Save button
            Button("Save", variant="primary", id='button-save-injections'),
            id='outer-injections-grid',
            classes='vertical-scroll-containe'
        )
        yield injections_container

    def action_save_config(self):
        """Save the injections configuration to the file."""
        self.save_injections_information()

    async def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "link-add-button":
            self.add_link_to_list()
        if event.button.id == "link-remove-button":
            self.remove_link_to_list()
        if event.button.id == "header-add-button":
            self.add_header_to_list()
        if event.button.id == "header-remove-button":
            self.remove_header_to_list()
        elif event.button.id == "button-save-injections":
            self.save_injections_information()

    def add_link_to_list(self):
        """Add a link to the ListView."""
        replacement_type = self.query_one("#replacement-type-select", Select).value
        url_all = self.query_one("#link-url-input-all", Input).value
        url_domain = self.query_one("#link-url-input-domain", Input).value
        listview = self.query_one("#links-listview", ListView)

        if replacement_type and (url_all or url_domain):
            if replacement_type == 'all':
                updated = False
                for item in listview.children:
                    item_label = item.query_one(Label)
                    if item_label.renderable.plain.startswith("all --> "):
                        item_label.update(f"{replacement_type} --> {url_all}")
                        updated = True
                        break
                if (not updated):
                    listview.append(ListItem(Label(f"{replacement_type} --> {url_all}"), classes="injections-listitem"))
            elif replacement_type == 'domain':
                domain = self.query_one('#link-domain-input', Input).value
                updated = False
                for item in listview.children:
                    item_label = item.query_one(Label)
                    if item_label.renderable.plain.startswith(f"{domain} --> "):
                        item_label.update(f"{domain} --> {url_domain}")
                        updated = True
                        break
                # If it was not found in the previous loop
                if (not updated):
                    listview.append(ListItem(Label(f"{domain} --> {url_domain}"), classes="injections-listitem"))                
            else:
                if (url_domain != ''):
                    listview.append(ListItem(Label(f"{domain} --> {url_domain}"), classes="injections-listitem"))
                if (url_all != ''):
                    listview.append(ListItem(Label(f"{replacement_type} --> {url_all}"), classes="injections-listitem"))
        
        # Clear the input fields after adding to the list
        self.query_one("#replacement-type-select", Select).value = Select.BLANK
        self.query_one("#link-domain-input", Input).value = ""
        self.query_one("#link-url-input-all", Input).value = ""
        self.query_one("#link-url-input-domain", Input).value = ""
    
    def add_header_to_list(self):
        """Add a header injection to the ListView."""
        header = self.query_one("#header-key-input", Input).value
        hvalue = self.query_one("#header-value-input", Input).value
        listview = self.query_one("#headers-listview", ListView)

        if header and hvalue:
            listview.append(ListItem(Label(f"{header}: {hvalue}"), classes="injections-listitem"))
            # Clear the input fields after adding to the list
            self.query_one("#header-key-input", Input).value = ""
            self.query_one("#header-value-input", Input).value = ""

    def remove_link_to_list(self):
        """Remove a link to the ListView."""
        listview = self.query_one("#links-listview", ListView)
        listview.highlighted_child.remove()
    
    def remove_header_to_list(self):
        """Remove a header injection to the ListView."""
        listview = self.query_one("#headers-listview", ListView)
        listview.highlighted_child.remove()

    def on_key(self, event):
        """Handle key press events."""
        if event.key == "enter":
            # Check if the focus is on domain or address inputs and add to the corresponding list
            replacement_type = self.query_one("#replacement-type-select", Select)
            injection_link_all = self.query_one("#link-url-input-all", Input)
            injection_link_domain = self.query_one("#link-url-input-domain", Input)
            header_key = self.query_one("#header-key-input", Input)
            header_value = self.query_one("#header-value-input", Input)

            # If the focus is on any domain-related input
            if replacement_type.value != Select.BLANK and (injection_link_all.has_focus or injection_link_domain.has_focus):
                self.add_link_to_list()
            # If the focus is on any address-related input
            elif header_key.has_focus or header_value.has_focus:
                self.add_header_to_list()

    def on_select_changed(self, event: Select.Changed):
        """
        Handle select change events:
        Change the style of links-domain-injection-form and links-links-injection-form depending on the selected option.
        If the selected option is "all", show the links-links-injection-form container
        If the selected option is "domain", show the links-domain-injection-form container
        """
        replacement_type = self.query_one("#replacement-type-select", Select)
        if replacement_type.value == 'all':
            self.query_one("#links-all-injection-form").styles.display = 'block'
            self.query_one("#links-domain-injection-form").styles.display = 'none'
        elif replacement_type.value == 'domain':
            self.query_one("#links-all-injection-form").styles.display = 'none'
            self.query_one("#links-domain-injection-form").styles.display = 'block'
        else:
            self.query_one("#links-all-injection-form").styles.display = 'none'
            self.query_one("#links-domain-injection-form").styles.display = 'none'


    def save_injections_information(self):
        """Save injections information to a YAML file."""
        # pull the data from the form
        attachment = self.query_one('#attachment-path-input', Input)
        attachment_message = self.query_one('#attachment-message-input', Input)
        tracking_url = self.query_one('#tracking-url-input', Input)
        unc_path = self.query_one('#unc-path-input', Input)
        links_listview = self.query_one("#links-listview", ListView)
        headers_listview = self.query_one("#headers-listview", ListView)

        # Prepare the data structure
        injections_data = {}
        # Add the key value pair when they exists
        if (attachment_message is not None and attachment_message.value != "") or (attachment_message is not None and attachment_message.value != ""):
            injections_data["attachments"] = {}
            if (attachment is not None and attachment.value != ""):
                injections_data["attachments"]["path"] = attachment.value
            
            if (attachment_message is not None or attachment_message.value != ""):
                injections_data["attachments"]["attachment_message"] = attachment_message.value

        if (tracking_url is not None and tracking_url.value != ""):
            injections_data["tracking_url"] = tracking_url.value
        
        if (unc_path is not None and unc_path.value != ""):
            injections_data["unc_path"] = unc_path.value

        # If there are no headers, delete the dictionary entry
        if (len(headers_listview.children) >= 0):
            injections_data["links"] = {}
            # Collect links from the ListView
            for item in links_listview.children:
                # The link item will have a format like "(all) --> https://example.com"
                link_str = str(item.query_one(Label).renderable)
                replacement_type, url = link_str.split(" --> ", 1)
                injections_data["links"][replacement_type.strip()] = url.strip()
        
        # If there are no links, delete the dictionary entry
        if (len(links_listview.children) >= 0):
            injections_data["headers"] = {}
             # Collect headers from the ListView
            for item in headers_listview.children:
                # The header item will have a format like "X-Header-Name: Header Value"
                header_str = str(item.query_one(Label).renderable)
                header, value = header_str.split(": ", 1)
                injections_data["headers"][header.strip()] = value.strip()
            
        # Save to a YAML file
        with open(self.config_path, "w") as yaml_file:
            yaml.dump(injections_data, yaml_file, default_flow_style=False)

        print(f"Injections saved to {self.config_path}")


    def read_injections_information(self):
        """Load injections information from the YAML file (if exists) and populate the form."""
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r") as yaml_file:
            injections_data = yaml.safe_load(yaml_file)

        # Populate attachment fields
        self.query_one("#attachment-path-input", Input).value = injections_data.get("attachments", {}).get("path", "")
        self.query_one("#attachment-message-input", Input).value = injections_data.get("attachments", {}).get("attachment_message", "")

        # Populate links
        links_listview = self.query_one("#links-listview", ListView)
        for replacement_type, url in injections_data.get("links", {}).items():
            links_listview.append(ListItem(Label(f"{replacement_type} --> {url}"), classes="injections-listitem"))

        # Populate headers
        headers = injections_data.get("headers", {})
        header_listview = self.query_one("#headers-listview", ListView)
        for header, hvalue in injections_data.get("headers", {}).items():
            header_listview.append(ListItem(Label(f"{header}: {hvalue}"), classes="injections-listitem"))

        # Populate tracking URL and UNC path
        self.query_one("#tracking-url-input", Input).value = injections_data.get("tracking_url", "")
        self.query_one("#unc-path-input", Input).value = injections_data.get("unc_path", "")

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_injections_information()
