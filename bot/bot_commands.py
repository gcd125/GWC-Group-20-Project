import time
import discord
from discord import app_commands

# adjust this import to match your database file's name and functions
from database.database_helpers.events import NewEvent, create_event, get_active_event
from database.database_helpers.attendance import record_attendance


def register_commands(client: discord.Client) -> app_commands.CommandTree:
    tree = app_commands.CommandTree(client)
    print("hello")

    @tree.command(name="check-in", description="Check in to an event with a passcode")
    @app_commands.describe(passcode="The passcode for the event")
    @app_commands.checks.cooldown(3, 60.0)  # 3 attempts per minute per user
    async def check_in(interaction: discord.Interaction, passcode: str):
        now = int(time.time())
        event = get_active_event(passcode.strip().lower(), now)

        if event is None:
            await interaction.response.send_message(
                "Invalid or expired passcode.", ephemeral=True)
            return

        event_id, event_name = event
        is_new = record_attendance(event_id, interaction.user.id)

        if is_new:
            await interaction.response.send_message(
                f"✅ Checked in to **{event_name}**. Attendance recorded!", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"You're already checked in to **{event_name}**.", ephemeral=True)

    @tree.command(name="event-create", description="Create an event with a check-in passcode")
    @app_commands.describe(
        name="Name of the event",
        event_type_id="Event type ID",
        points="Points awarded for attending",
        passcode="Passcode members will enter to check in",
        minutes_open="How long check-in stays open (default 60)",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def event_create(interaction: discord.Interaction, name: str, event_type_id: int, date: int, start_time: int,
                           end_time: int, points: int, passcode: str, minutes_open: int):
        now = int(time.time())
        try:
            event_id = create_event(NewEvent(
                name=name,
                type_id=event_type_id,
                organizer_id=interaction.user.id,   # or look up the member's row ID
                points=points,
                date = date,
                start_time= start_time,
                end_time= end_time,
                passcode=passcode,
                opens_at = now,
                closes_at = now + 60
            ))
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Event **{name}** created (ID {event_id}), open for {minutes_open} minutes.",
            ephemeral=True)

    @tree.error
    async def on_command_error(interaction: discord.Interaction,
                               error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f} seconds.", ephemeral=True)
        else:
            raise error

    # Sync commands with Discord once, when the bot starts up
    async def setup_hook():
        await tree.sync()

    client.setup_hook = setup_hook

    return tree