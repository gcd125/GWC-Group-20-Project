import time
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, timedelta

from database.database_helpers.events import (
    EASTERN, NewEvent, create_event, get_active_event, get_event, get_events,
    get_event_type, get_event_type_names, get_member, get_pending_reminders,
    mark_reminder_sent, setup_events_database, parse_eastern, event_start,
    format_time, send_event_message)
from database.database_helpers.attendance import (
    record_attendance, register_for_event, mark_present, get_attendance_counts)
from database.database_helpers.points import get_leaderboard, get_points


def is_officer(interaction):
    return (isinstance(interaction.user, discord.Member) and
            (interaction.user.guild_permissions.manage_guild or
             interaction.user.guild_permissions.administrator))


def register_commands(client: discord.Client) -> app_commands.CommandTree:
    tree = app_commands.CommandTree(client)
    setup_events_database()

    # ---------------- Check In command ------------------
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

        if is_new is None:
            await interaction.response.send_message(
                "Please complete your GWC member registration first.", ephemeral=True)
        elif is_new:
            await interaction.response.send_message(
                f"✅ Checked in to **{event_name}**. Attendance recorded!", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"You're already checked in to **{event_name}**.", ephemeral=True)

    # ------------------------- Create Event ---------------------------------
    @tree.command(name="event-create", description="Create an event with a check-in passcode")
    @app_commands.describe(
        name="Name of the event",
        event_type="Event type name",
        date="Date, YYYY-MM-DD",
        start_time="Start time, HH:MM (24-hour Eastern)",
        end_time="End time, HH:MM (24-hour Eastern)",
        location="Where the event is held",
        passcode="Passcode members will enter to check in",
        points="Points awarded for attending",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def event_create(interaction: discord.Interaction, name: str, event_type: str,
                           date: str, start_time: str, end_time: str, location: str,
                           passcode: str, points: app_commands.Range[int, 0, 1000] = 0):
        if not is_officer(interaction):
            await interaction.response.send_message(
                "Only officers can create events.", ephemeral=True)
            return

        try:
            start = parse_eastern(date, start_time)
            end = parse_eastern(date, end_time)
        except ValueError:
            await interaction.response.send_message(
                "Use date YYYY-MM-DD and times HH:MM (24-hour Eastern time).",
                ephemeral=True)
            return

        if start <= datetime.now(EASTERN):
            await interaction.response.send_message(
                "The event must be in the future.", ephemeral=True)
            return

        event_type_row = get_event_type(event_type.strip())
        if event_type_row is None:
            types = get_event_type_names()
            await interaction.response.send_message(
                "Unknown event type. Choose: " + ", ".join(types), ephemeral=True)
            return

        organizer = get_member(interaction.user.id)

        try:
            event_id = create_event(NewEvent(
                name=name.strip(),
                type_id=event_type_row[0],
                organizer_id=organizer[0] if organizer else None,
                points=points,
                date=date,
                start_time=int(start.timestamp()),
                end_time=int(end.timestamp()),
                passcode=passcode,
                opens_at=int(start.timestamp()),
                closes_at=int(end.timestamp()),
                location=location.strip(),
                reminder_channel_id=str(interaction.channel_id),
            ))
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"✅ Event **{name}** created (ID {event_id}).", ephemeral=True)
        if interaction.channel is not None:
            await send_event_message(interaction.channel, event_id)

    # ------------------------- List Events ---------------------------------
    @tree.command(name="event-list", description="See upcoming events")
    async def event_list(interaction: discord.Interaction):
        now = datetime.now(EASTERN)
        upcoming = []
        for event in get_events():
            start = event_start(event)
            if start is not None and start > now:
                upcoming.append(event)

        if not upcoming:
            await interaction.response.send_message("No upcoming events yet.", ephemeral=True)
            return

        embed = discord.Embed(title="💻 Upcoming GWC Events", color=discord.Color.blue())
        for event in upcoming[:25]:
            event_id, name, date, start_time, location = event
            embed.add_field(
                name=f"#{event_id} — {name}",
                value=f"📅 {date} at {format_time(event_start(event))} Eastern\n📍 {location or 'Not set'}",
                inline=False)
        await interaction.response.send_message(embed=embed)

    # ------------------------- Register ---------------------------------
    @tree.command(name="event-register", description="Register for an event")
    async def event_register(interaction: discord.Interaction, event_id: int):
        event = get_event(event_id)
        if event is None:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return

        start = event_start(event)
        if start is None or start <= datetime.now(EASTERN):
            await interaction.response.send_message(
                "Registration is unavailable for this event.", ephemeral=True)
            return

        member = get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message(
                "Please complete your GWC member registration first.", ephemeral=True)
            return

        registered = register_for_event(member[0], event_id)
        await interaction.response.send_message(
            "✅ You're registered!" if registered else "You're already registered for this event!",
            ephemeral=True)

    # ------------------------- Officer Mark Present ---------------------------------
    @tree.command(name="event-mark-present", description="Mark a member present")
    async def event_mark_present(interaction: discord.Interaction, event_id: int,
                                 member: discord.Member):
        if not is_officer(interaction):
            await interaction.response.send_message(
                "Only officers can check in members.", ephemeral=True)
            return
        if get_event(event_id) is None:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
        member_row = get_member(member.id)
        if member_row is None:
            await interaction.response.send_message(
                "Member not registered with GWC.", ephemeral=True)
            return

        updated = mark_present(member_row[0], event_id)
        await interaction.response.send_message(
            f"✅ {member.display_name} marked present." if updated
            else "Member has not registered for this event.",
            ephemeral=True)

    # ------------------------- Attendance ---------------------------------
    @tree.command(name="event-attendance", description="View event attendance")
    async def event_attendance(interaction: discord.Interaction, event_id: int):
        if not is_officer(interaction):
            await interaction.response.send_message(
                "Only officers can view attendance.", ephemeral=True)
            return
        event = get_event(event_id)
        if event is None:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return

        total, present = get_attendance_counts(event_id)
        await interaction.response.send_message(
            f"📋 **{event[1]}**\nRegistered: {total}\nPresent: {present}\n"
            f"Not checked in: {total - present}",
            ephemeral=True)

    # ------------------------- Ping ---------------------------------
    @tree.command(name="event-ping", description="Post an event announcement")
    async def event_ping(interaction: discord.Interaction, event_id: int):
        if not is_officer(interaction):
            await interaction.response.send_message(
                "Only officers can announce events.", ephemeral=True)
            return
        if get_event(event_id) is None:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
        await interaction.response.send_message("✅ Announcement posted!", ephemeral=True)
        await send_event_message(interaction.channel, event_id)

    # --------------Points Command---------------------
    @tree.command(
        name="points",
        description="View your points",
    )
    async def points(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_points = get_points(interaction.user.id)

        if user_points is None:
            await interaction.edit_original_response(
                content="You are not registered yet.",
            )
            return
        await interaction.edit_original_response(
            content=f"You have {user_points} points.",
        )

    # --------------Leaderboard Command---------------------
    @tree.command(
        name="leaderboard",
        description="View the points leaderboard",
    )
    async def leaderboard(interaction: discord.Interaction):
        members = get_leaderboard()

        if not members:
            await interaction.response.send_message(
                "No registered members yet.",
                ephemeral=True
            )
            return
        lines = [
            f"**{place}. {name}** {points} points"
            for place, (name, points) in enumerate(members, start=1)
        ]
        await interaction.response.send_message(
            "Points Leaderboard:\n" + "\n".join(lines),
            ephemeral=True
        )

    # --------------Automatic Reminders---------------------
    @tasks.loop(minutes=5)
    async def send_reminders():
        now = datetime.now(EASTERN)
        for event_id, name, date, start_time, channel_id in get_pending_reminders():
            start = datetime.fromtimestamp(start_time, EASTERN)
            if not channel_id or not (start - timedelta(hours=24) <= now < start):
                continue

            try:
                channel = client.get_channel(int(channel_id))
                if channel is None:
                    channel = await client.fetch_channel(int(channel_id))
                await channel.send(
                    f"⏰ **Event Reminder!**\n💻 **{name}**\n"
                    f"📅 {date} at {format_time(start)} Eastern\nDon't forget to attend!"
                )
            except (discord.DiscordException, ValueError) as error:
                print(f"Could not send reminder for event {event_id}: {error}")
                continue

            mark_reminder_sent(event_id)

    @send_reminders.before_loop
    async def before_reminders():
        await client.wait_until_ready()

    # -------------------------- Error ---------------------
    @tree.error
    async def on_command_error(interaction: discord.Interaction,
                               error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f} seconds.", ephemeral=True)
        else:
            raise error

    # Sync commands and start reminders once, when the bot starts up
    async def setup_hook():
        send_reminders.start()
        await tree.sync()

    client.setup_hook = setup_hook

    return tree