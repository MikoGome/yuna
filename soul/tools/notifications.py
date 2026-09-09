import sys
import shutil
import subprocess


def send_notification(title: str, message: str) -> str:
    """
    Shows a desktop notification to the user.

    Args:
        title (str): Short bold title for the notification (e.g., 'Yuna').
        message (str): The notification body text.
    """
    title = title.strip() or "Yuna"
    message = message.strip()

    if not message:
        return "Error: A notification message is required."

    # --- Linux: notify-send (libnotify) ---
    if sys.platform.startswith('linux'):
        if not shutil.which('notify-send'):
            return "Error: 'notify-send' is not installed. Install it via your package manager (libnotify2)."
        try:
            subprocess.run(
                ['notify-send', '-a', 'Yuna', title, message],
                capture_output=True, text=True, check=True
            )
            return f"Notification sent: '{title}' - {message}"
        except Exception as e:
            return f"Error sending notification: {str(e)}"

    # --- macOS: osascript display notification ---
    elif sys.platform == 'darwin':
        try:
            script = (
                f'display notification "{message.replace(chr(34), chr(92) + chr(34))}" '
                f'with title "{title.replace(chr(34), chr(92) + chr(34))}"'
            )
            subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
            return f"Notification sent: '{title}' - {message}"
        except Exception as e:
            return f"Error sending notification on macOS: {str(e)}"

    # --- Windows: PowerShell toast (WinRT) ---
    elif sys.platform == 'win32':
        try:
            def _xml_escape(s: str) -> str:
                return (s.replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;").replace('"', "&quot;"))
            # Escape single quotes for the PowerShell single-quoted string
            def _ps_quote(s: str) -> str:
                return s.replace("'", "''")
            toast_xml = (
                '<toast><visual><binding template="ToastText02">'
                f'<text id="1">{_xml_escape(title)}</text>'
                f'<text id="2">{_xml_escape(message)}</text>'
                '</binding></visual></toast>'
            )
            ps_script = (
                "$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]; "
                "$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime]; "
                "$doc = New-Object Windows.Data.Xml.Dom.XmlDocument; "
                f"$doc.LoadXml('{_ps_quote(toast_xml)}'); "
                "$toast = New-Object Windows.UI.Notifications.ToastNotification $doc; "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Yuna').Show($toast)"
            )
            subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, check=True
            )
            return f"Notification sent: '{title}' - {message}"
        except Exception as e:
            return f"Error sending notification on Windows: {str(e)}"

    return f"Error: Unsupported operating system for notifications: {sys.platform}"


# =====================================================================
# Tool Definition Metadata
# =====================================================================
notification_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'send_notification',
            'description': (
                "Shows a desktop notification popup to the user. Use this to "
                "get the user's attention, confirm a background task finished, "
                "or deliver a short message they can see even if they're not "
                "listening."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': "Short bold title for the notification (e.g., 'Yuna').",
                    },
                    'message': {
                        'type': 'string',
                        'description': "The notification body text to display.",
                    },
                },
                'required': ['title', 'message'],
            },
        },
    },
]
