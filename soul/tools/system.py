import psutil


def get_system_stats() -> str:
    """
    Returns a snapshot of the computer's current state: battery, CPU, RAM,
    and disk usage. Use this when the user asks how the PC is doing, how
    much battery is left, or whether the machine is running hot/full.
    """
    lines = []

    # --- Battery (laptops only) ---
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            state = "charging" if battery.power_plugged else "on battery"
            lines.append(f"Battery: {battery.percent:.0f}% ({state})")
    except Exception:
        pass  # Desktops / no battery sensor

    # --- CPU ---
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        core_count = psutil.cpu_count(logical=True) or 0
        lines.append(f"CPU: {cpu_percent:.0f}% used across {core_count} cores")
    except Exception as e:
        lines.append(f"CPU: unavailable ({e})")

    # --- Memory ---
    try:
        mem = psutil.virtual_memory()
        lines.append(
            f"RAM: {mem.percent:.0f}% used "
            f"({mem.used / (1024 ** 3):.1f} / {mem.total / (1024 ** 3):.1f} GB)"
        )
    except Exception as e:
        lines.append(f"RAM: unavailable ({e})")

    # --- Disk (root partition) ---
    try:
        disk = psutil.disk_usage("/")
        lines.append(
            f"Disk (/): {disk.percent:.0f}% used "
            f"({disk.used / (1024 ** 3):.0f} / {disk.total / (1024 ** 3):.0f} GB)"
        )
    except Exception as e:
        lines.append(f"Disk: unavailable ({e})")

    if not lines:
        return "Error: Could not read any system statistics."

    return "\n".join(lines)


# =====================================================================
# Tool Definition Metadata
# =====================================================================
system_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'get_system_stats',
            'description': (
                "Gets a snapshot of the computer's current state: battery "
                "level, CPU usage, RAM usage, and disk space. Use this when "
                "the user asks how the PC is doing, how much battery is left, "
                "or whether the machine is running low on resources."
            ),
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': [],
            },
        },
    },
]
