import os, sys
from textual.app import App, Screen, ComposeResult
from textual.widgets import Label, Button, Log, Footer, Header, TabbedContent, TabPane, Checkbox, Rule, Collapsible, Select
from textual.containers import Vertical, Horizontal, Container
from textual.binding import Binding
from datetime import datetime
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from tabs import AuthenticationTab, NotificationsTab, TyposTab, InjectionsTab, FilterTab, MiscTab
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Maitm import Maitm

def firstrun() -> bool:
    """Check if the app is running for the first time."""
    return 

class RunScreen(Screen):
    """A screen for running the tool."""
    CSS_PATH = 'gui.css'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_path = None
        self.executor = ThreadPoolExecutor(max_workers=1) 
        self._log_watcher_task = None  
        self.stop_event = None  
        self.thread = None  

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Button(label="Run MaitM", id="run-button", variant="success", classes='run'),
                Rule(orientation="horizontal"),
                Collapsible(
                    Label("Configuration file path:"),
                    Select(id="config-file-select", prompt="Select your configuration file", options=[]),
                    Checkbox(value=True, id="testing-onlynewmails-checkbox", label="Skip already forwarded emails"),
                    Checkbox(value=False, id="testing-forwardemail-checkbox", label="Do not Forward (Testing Mode)"),
                    title='Run Settings',
                    collapsed=False,
                    id='collapsible-testing-settings'
                ),
                Rule(orientation="horizontal"),
                Container(
                    Button("Configuration", id="button-configuration",variant="primary"),
                    id='configuration-container'
                ),
                id="left-panel"
            ),
            Log(highlight=True, id="log-viewer", name="terminal_output"),
            id="main_container"
        )
        yield Footer()

    async def on_button_pressed(self, event) -> None:
        """Handle button press to navigate to configuration screen."""
        if event.button.id == "button-configuration":
            await self.app.push_screen(ConfigureScreen())
        if event.button.id == "run-button":
            if firstrun():
                await self.app.push_screen(ConfigureScreen())
            else:
                run_button = self.query_one("#run-button", Button)
                if (str(run_button.label) == "Stop"):
                    # Change the tool class and text
                    run_button.label = "Run MaitM"
                    run_button.variant="success"
                    # Stop the tool and monitor
                    await self.stop_tool()
                elif (str(run_button.label) == "Run MaitM"):
                    # Change the tool class and text
                    run_button.label = "Stop"
                    run_button.variant="error"
                    # Run the tool in the background
                    await self.run_tool_in_background()
            
        if event.button.id == "button-save-testing-config":
            self.save_testing_config()

    async def stop_tool(self):
        """Stop the tool and monitor."""
        # Signal the background thread to stop
        if self.stop_event:
            self.stop_event.set()  # This will stop the thread's execution

        # Cancel the log watcher task
        if self._log_watcher_task:
            self._log_watcher_task.cancel()

    async def run_tool_in_background(self):
        """Run the tool in the background and monitor the logs."""
        # Get configuration file and options from the UI
        config_file = self.query_one("#config-file-select").value
        testing_onlynewmails = self.query_one("#testing-onlynewmails-checkbox").value
        testing_forwardemail = not bool(self.query_one("#testing-forwardemail-checkbox").value)

        # Create the log file path
        self.log_path = "logs/" + datetime.now().strftime('%Y%m%d_%H%M%S') + '_mailinthemiddle.log'

        # Create a stop event for the thread to monitor
        self.stop_event = threading.Event()

        # Run the tool in the background
        self.thread = threading.Thread(
            target=self._run_maitm,
            args=(config_file, testing_onlynewmails, testing_forwardemail, self.stop_event)
        )
        self.thread.start()

        # Start watching the log file asynchronously
        self._log_watcher_task = asyncio.create_task(self.watch_log_file())

    def _run_maitm(self, config_file, testing_onlynewmails, testing_forwardemail, stop_event) -> None:
        """Run the Maitm tool with the selected configuration."""
        maitm = Maitm(config_file=config_file,
                      logfile=self.log_path,
                      only_new=testing_onlynewmails,
                      forward_emails=testing_forwardemail,
                      stop_event=stop_event)

        maitm.mailmanager.login_read()
        maitm.mailmanager.login_send()
        maitm.monitor_inbox()  # This function should check stop_event periodically


    async def watch_log_file(self):
        """Watch the log file for updates and display them in a TextLog widget."""
        text_log = self.query_one("#log-viewer", Log)

        # Continuously watch for changes in the log file
        last_size = 0
        while True:
            try:
                if os.path.exists(self.log_path):
                    # Get the current file size and read only the new data
                    current_size = os.path.getsize(self.log_path)
                    if current_size > last_size:
                        with open(self.log_path, 'r') as log_file:
                            log_file.seek(last_size)  # Read only the new portion of the file
                            new_data = log_file.read()
                            text_log.write(new_data)  # Write new data to the TextLog widget
                        last_size = current_size
            except Exception as e:
                text_log.write(f"Error reading log file: {e}")
            await asyncio.sleep(1)  # Poll every second for changes

    def on_mount(self) -> None:
        """Load the configuration files in the dropdown."""
        config_folder = 'config/'
        config_files = [(f, config_folder + f) for f in os.listdir(config_folder) if (f.endswith('.yml') and f.startswith('config'))]
        select: Select = self.query_one("#config-file-select")
        select.set_options(config_files)
        # Select by default the config/config.yml file
        select.value = self.app.config_path

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle the selection change event."""
        self.app.config_path = event.value


class ConfigureScreen(Screen):
    """A screen for configuring the tool with 5 tabs."""
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),  # Key binding to quit the application
        Binding(key="a", action="show_tab('auth')", description="Authentication"),
        Binding(key="i", action="show_tab('injection')", description="Injections"),
        Binding(key="t", action="show_tab('typos')", description="Typos"),
        Binding(key="f", action="show_tab('filter')", description="Filters"),
        Binding(key="n", action="show_tab('notifications')",description="Notifications"),
        Binding(key="m", action="show_tab('miscelanea')",description="Misc.")
    ]
    CSS_PATH='gui.css'

    def compose(self) -> ComposeResult:
        yield Header()
        # Creating the tabbed content with 5 tabs
        self.tabbed_content = TabbedContent(initial="auth")  # Assign the tabbed content to a class variable
        with self.tabbed_content:
            with TabPane("🪪 Authentication [a]", id="auth"):
                yield AuthenticationTab(global_config_path=self.app.config_path)
            with TabPane("🎛️  Filter [f]", id="filter"):
                yield FilterTab(global_config_path=self.app.config_path)
            with TabPane("💉 Injection [i]", id="injection"):
                yield InjectionsTab(global_config_path=self.app.config_path)
            with TabPane("✏️  Typos [t]", id="typos"):
                yield TyposTab(global_config_path=self.app.config_path)
            with TabPane("💬 Notifications [n]", id="notifications"):
                yield NotificationsTab(global_config_path=self.app.config_path)
            with TabPane("🗑️  Miscellaneous [m]", id="miscelanea"):
                yield MiscTab(global_config_path=self.app.config_path)

        yield self.tabbed_content
        yield Footer()

    async def action_show_tab(self, tab_id: str) -> None:
        """Show the requested tab based on key bindings."""
        # Switch to the tab based on the provided ID
        self.tabbed_content.active = tab_id

    async def on_button_pressed(self, event) -> None:
        """Handle configuration submission."""
        if event.button.id == "submit_button":
            # Configuration is done, remove the ".firstrun" file
            if os.path.exists(".firstrun"):
                os.remove(".firstrun")
            await self.app.pop_screen()  # Go back to the run screen after configuration
                

class MaitmTUI(App):
    """Main application that switches between Run and Configuration screens."""

    BINDINGS = [Binding(key="q", action="quit", description="Quit the app"),
                Binding(key="r", action="show_run_screen()",description="Run"),
                Binding(key="c", action="show_configuration_screen()",description="Configuration")]
    
    def __init__(self):
        super().__init__()
        self.config_path = 'config/config.yml'

    def check_first_run(self) -> bool:
        """Check if the '.firstrun' flag exists."""
        return os.path.exists(".firstrun")

    async def on_mount(self) -> None:
        """Check if it's the first run and push the appropriate screen."""

        self.title = "Mail-in-the-Middle"
        self.sub_title = "Plenty of fishes out there"

        if self.check_first_run():
            # If the tool is running for the first time, show the configuration screen
            await self.push_screen(ConfigureScreen())
        else:
            # Otherwise, go directly to the run screen
            await self.push_screen(RunScreen())

    def compose(self) -> ComposeResult:
        """This method ensures that we load the first screen as needed."""
        # Add Header, Footer, and placeholder for the first screen
        yield Header()  # Persistent header across the app
        yield Label("Loading...")  # Temporary screen while deciding what to load
        yield Footer()  # Persistent footer across the app

    async def action_show_run_screen(self) -> None:
        """Show the run screen."""
        await self.push_screen(RunScreen(name='RunScreen'))

    async def action_show_configuration_screen(self) -> None:
        """Show the run screen."""
        await self.push_screen(ConfigureScreen(name='ConfigureScreen'))

    # async def on_startup(self) -> None:
    #     """Called when the application starts. Set up the '.firstrun' flag if needed."""
    #     # Create the '.firstrun' flag if it doesn't exist (indicating first run)
    #     if not os.path.exists(".firstrun"):
    #         with open(".firstrun", "w") as f:
    #             f.write("This is the first run configuration flag.\n")


if __name__ == "__main__":
    app = MaitmTUI()
    app.run()
