import os
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, RadioSet, RadioButton, Switch
from textual.containers import Vertical, VerticalScroll, Horizontal, Container
from textual.validation import Number
from textual.binding import Binding
import yaml

# Define the Authentication tab as its own class
class AuthenticationTab(Vertical):
    # CSS
    CSS_PATH='gui.css'
    BINDINGS = [
        Binding(key="ctrl+s", action="save_config()",description="Save"),
    ]

    def __init__(self,global_config_path='config/config.yml'):
        super().__init__()
        # Config file path
        self.global_config_path=global_config_path
        self.config_path=self._get_path_from_config('auth')
        # Shared configuration variables
        self.authentication_protocol_send = "SMTP"
        self.authentication_protocol_read = "IMAP"

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
        self.save_auth_information()

    def compose(self) -> ComposeResult:
        """Authentication content."""
        auth_container = VerticalScroll(
            Container(
                Label("Inbound Protocol", id='reading-emails-label', classes='filter-form-label'),
                RadioSet(
                    RadioButton("IMAP", value=True, id='radio-button-read-imap'),
                    RadioButton("M365 Oauth2 (Legacy)", id='radio-button-read-oauth2l'),
                    id='radio-set-read'
                ),
                classes='auth-box',
                id='auth-read-box-left'
            ),
            # IMAP for reading emails container:
            Container(
                Horizontal(
                    Label('Username: ',  classes='label-auth-form'),
                    Input(placeholder="Username", id="read-username")
                ),
                Horizontal(
                    Label('Password: ', classes='label-auth-form'),
                    Input(placeholder="Password", id="read-password", password=True)
                ),
                Horizontal(
                    Label('Server: ', classes='label-auth-form'),
                    Input(placeholder="Server", id="read-server")
                ),
                Horizontal(
                    Label('Port Number: ', classes='label-auth-form'),
                    Input(placeholder="Port", id="read-port", type="integer", validators=[
                        Number(minimum=1,maximum=65535)
                    ])
                ),
                Horizontal(
                    Label('Use TLS: ', classes='label-auth-form'),
                    Switch(value=True, id="read-tls")
                ),
                classes='auth-box visible',
                id='imap-read-params-box'
            ),
            # Oauth2 for reading emails container:
            Container(
                Horizontal(
                    Label('Username: ', classes='label-auth-form'),
                    Input(placeholder="Username", id="read-o2-username")
                ),
                Horizontal(
                    Label('Password: ', classes='label-auth-form'),
                    Input(placeholder="Password", id="read-o2-password", password=True)
                ),
                Horizontal(
                    Label('Tenant ID: ', classes='label-auth-form'),
                    Input(placeholder="Tenant ID", id="read-o2-tenant-id")
                ),
                Horizontal(
                    Label('Client ID: ', classes='label-auth-form'),
                    Input(placeholder="Client ID", id="read-o2-client-id")
                ),
                Horizontal(
                    Label('Client Secret: ', classes='label-auth-form'),
                    Input(placeholder="Client Secret", id="read-o2-client-secret", password=True)
                ),
                classes='auth-box hidden',
                id='oauth2l-read-params-box'
            ),
            Container(
                Label("Outbound Protocol", id='sending-emails-label', classes='filter-form-label'),
                RadioSet(
                    RadioButton("SMTP", value=True, id='radio-button-send-smtp'),
                    RadioButton("M365 Oauth2 (Legacy)", id='radio-button-send-oauth2l'),
                    id='radio-set-send'
                ),
                classes='auth-box',
                id='auth-send-box-left'
            ),
            # SMTP for sending emails container:
            Container(
                Horizontal(
                    Label('Username: ', classes='label-auth-form'),
                    Input(placeholder="Username", id="send-username")
                ),
                Horizontal(
                    Label('Password: ', classes='label-auth-form'),
                    Input(placeholder="Password", id="send-password", password=True)
                ),
                Horizontal(
                    Label('Server: ', classes='label-auth-form'),
                    Input(placeholder="Server", id="send-server")
                ),
                Horizontal(
                    Label('Port Number: ', classes='label-auth-form'),
                    Input(placeholder="Port", id="send-port", type="integer", validators=[
                        Number(minimum=1,maximum=65535)
                    ])
                ),
                Horizontal(
                    Label('Use TLS: ', classes='label-auth-form'),
                    Switch(value=True, id="send-tls")
                ),
                classes='auth-box visible',
                id='smtp-send-params-box'
            ),
            # Oauth2 for sending emails container:
            Container(
                Horizontal(
                    Label('Username: ', classes='label-auth-form'),
                    Input(placeholder="Username", id="send-o2-username")
                ),
                Horizontal(
                    Label('Password: ', classes='label-auth-form'),
                    Input(placeholder="Password", id="send-o2-password", password=True)
                ),
                Horizontal(
                    Label('Tenant ID: ', classes='label-auth-form'),
                    Input(placeholder="Tenant ID", id="send-o2-tenant-id")
                ),
                Horizontal(
                    Label('Client ID: ', classes='label-auth-form'),
                    Input(placeholder="Client ID", id="send-o2-client-id")
                ),
                Horizontal(
                    Label('Client Secret: ', classes='label-auth-form'),
                    Input(placeholder="Client Secret", id="send-o2-client-secret", password=True)
                ),
                classes='auth-box hidden',
                id='oauth2l-send-params-box'
            ),
            Button("Save", variant="primary",id='button-save-auth'),
            id='grid-auth',
            classes='grid-auth'
        )
        yield auth_container

    async def on_mount(self) -> None:
        """Called after the widget is mounted in the DOM."""
        self.read_auth_information() 
    
    def read_auth_information(self):
        """Read and populate the data from the auth.yml config file."""
        # Check if the configuration file exists
        if not os.path.exists(self.config_path):
            print(f"Configuration file {self.config_path} does not exist.")
            return

        # Load the YAML configuration file
        with open(self.config_path, "r") as yaml_file:
            config_data = yaml.safe_load(yaml_file)

        # Populate the 'send' configuration
        send_config = config_data.get("send", {})
        if "smtp" in send_config:
            smtp_config = send_config["smtp"]
            self.query_one("#send-username", Input).value = smtp_config.get("username", "")
            self.query_one("#send-password", Input).value = smtp_config.get("password", "")
            self.query_one("#send-server", Input).value = smtp_config.get("server", "")
            self.query_one("#send-port", Input).value = str(smtp_config.get("port", ""))
            self.query_one("#send-tls", Switch).value = smtp_config.get("tls", False)
            self.authentication_protocol_send = "SMTP"
            self.query_one('#radio-button-send-smtp', RadioButton).value = True
        elif "oauth2legacy" in send_config:
            oauth2_send_config = send_config["oauth2legacy"]
            self.query_one("#send-o2-username", Input).value = oauth2_send_config.get("email", "")
            self.query_one("#send-o2-password", Input).value = oauth2_send_config.get("password", "")
            self.query_one("#send-o2-client-id", Input).value = oauth2_send_config.get("client_id", "")
            self.query_one("#send-o2-client-secret", Input).value = oauth2_send_config.get("client_secret", "")
            self.query_one("#send-o2-tenant-id", Input).value = oauth2_send_config.get("tenant_id", "")
            self.authentication_protocol_send = "M365 Oauth2 (Legacy)"
            self.query_one('#radio-button-send-oauth2l', RadioButton).value = True

        # Populate the 'read' configuration
        read_config = config_data.get("read", {})
        if "imap" in read_config:
            imap_config = read_config["imap"]
            self.query_one("#read-username", Input).value = imap_config.get("username", "")
            self.query_one("#read-password", Input).value = imap_config.get("password", "")
            self.query_one("#read-server", Input).value = imap_config.get("server", "")
            self.query_one("#read-port", Input).value = str(imap_config.get("port", ""))
            self.query_one("#read-tls", Switch).value = imap_config.get("ssl", False)
            self.authentication_protocol_read = "IMAP"
            self.query_one('#radio-button-read-imap', RadioButton).value = True
        elif "oauth2legacy" in read_config:
            oauth2_read_config = read_config["oauth2legacy"]
            self.query_one("#read-o2-username", Input).value = oauth2_read_config.get("email", "")
            self.query_one("#read-o2-password", Input).value = oauth2_read_config.get("password", "")
            self.query_one("#read-o2-client-id", Input).value = oauth2_read_config.get("client_id", "")
            self.query_one("#read-o2-client-secret", Input).value = oauth2_read_config.get("client_secret", "")
            self.query_one("#read-o2-tenant-id", Input).value = oauth2_read_config.get("tenant_id", "")
            self.authentication_protocol_read = "M365 Oauth2 (Legacy)"
            self.query_one('#radio-button-read-oauth2l', RadioButton).value = True

    def save_auth_information(self):
        # Collect values for sending configuration
        if self.authentication_protocol_send == "SMTP":
            send_config = {
                "smtp": {
                    "username": self.query_one("#send-username", Input).value,
                    "password": self.query_one("#send-password", Input).value,
                    "server": self.query_one("#send-server", Input).value,
                    "port": int(self.query_one("#send-port", Input).value),
                    "tls": self.query_one("#send-tls", Switch).value,
                }
            }
        else:  # Oauth2 (Legacy) for sending
            send_config = {
                "oauth2legacy": {
                    "email": self.query_one("#send-o2-username", Input).value,
                    "password": self.query_one("#send-o2-password", Input).value,
                    "client_id": self.query_one("#send-o2-client-id", Input).value,
                    "client_secret": self.query_one("#send-o2-client-secret", Input).value,
                    "tenant_id": self.query_one("#send-o2-tenant-id", Input).value,
                }
            }

        # Collect values for reading configuration
        if self.authentication_protocol_read == "IMAP":
            read_config = {
                "imap": {
                    "username": self.query_one("#read-username", Input).value,
                    "password": self.query_one("#read-password", Input).value,
                    "server": self.query_one("#read-server", Input).value,
                    "port": int(self.query_one("#read-port", Input).value),
                    "ssl": self.query_one("#read-tls", Switch).value,
                }
            }
        else:  # Oauth2 (Legacy) for reading
            read_config = {
                "oauth2legacy": {
                    "email": self.query_one("#read-o2-username", Input).value,
                    "password": self.query_one("#read-o2-password", Input).value,
                    "client_id": self.query_one("#read-o2-client-id", Input).value,
                    "client_secret": self.query_one("#read-o2-client-secret", Input).value,
                    "tenant_id": self.query_one("#read-o2-tenant-id", Input).value,
                }
            }

        # Create the data structure
        auth_config = {
            "send": send_config,
            "read": read_config
        }

        # Save the information to a YAML file
        with open(self.config_path, "w") as yaml_file:
            yaml.dump(auth_config, yaml_file, default_flow_style=False)


    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        # Outbound protocol
        if (event.pressed.id == 'radio-button-send-smtp'):
            self.query_one('#oauth2l-send-params-box').remove_class('visible')
            self.query_one('#oauth2l-send-params-box').add_class('hidden')
            self.query_one('#smtp-send-params-box').remove_class('hidden')
            self.query_one('#smtp-send-params-box').add_class('visible')
            self.authentication_protocol_send=str(event.pressed.label)
        if (event.pressed.id == 'radio-button-send-oauth2l'):
            self.query_one('#oauth2l-send-params-box').remove_class('hidden')
            self.query_one('#oauth2l-send-params-box').add_class('visible')
            self.query_one('#smtp-send-params-box').remove_class('visible')
            self.query_one('#smtp-send-params-box').add_class('hidden')
            self.authentication_protocol_send=str(event.pressed.label)

        # Inbound protocol
        if (event.pressed.id == 'radio-button-read-imap'):
            self.query_one('#oauth2l-read-params-box').remove_class('visible')
            self.query_one('#oauth2l-read-params-box').add_class('hidden')
            self.query_one('#imap-read-params-box').remove_class('hidden')
            self.query_one('#imap-read-params-box').add_class('visible')
            self.authentication_protocol_read=str(event.pressed.label)
        if (event.pressed.id == 'radio-button-read-oauth2l'):
            self.query_one('#oauth2l-read-params-box').remove_class('hidden')
            self.query_one('#oauth2l-read-params-box').add_class('visible')
            self.query_one('#imap-read-params-box').remove_class('visible')
            self.query_one('#imap-read-params-box').add_class('hidden')
            self.authentication_protocol_read=str(event.pressed.label)

    async def on_button_pressed(self, event) -> None:
        if event.button.id == 'button-save-auth':
            self.save_auth_information()