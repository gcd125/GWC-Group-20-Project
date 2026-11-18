"""Verified mapping between registration members and Discord accounts."""
import re
import sqlite3
import discord


def initialize_links(db):
    db.execute('''CREATE TABLE IF NOT EXISTS Member_Discord_Links (
        guild_id TEXT NOT NULL, discord_id TEXT NOT NULL, member_id INTEGER NOT NULL,
        PRIMARY KEY(guild_id, discord_id), UNIQUE(guild_id, member_id))''')
    db.commit()


def link_member(db, guild_id, discord_id, member_id):
    member = db.execute("SELECT member_id FROM Members WHERE member_id=? AND member_status='active'", (member_id,)).fetchone()
    if not member:
        raise ValueError('That registration ID is not an active member.')
    current = db.execute('SELECT member_id FROM Member_Discord_Links WHERE guild_id=? AND discord_id=?', (str(guild_id),str(discord_id))).fetchone()
    if current and current[0] == member_id:
        return
    try:
        with db:
            db.execute('INSERT INTO Member_Discord_Links VALUES (?,?,?)', (str(guild_id),str(discord_id),member_id))
    except sqlite3.IntegrityError:
        raise ValueError('That account or registration is already linked. No existing link was changed.') from None


async def handle_link_command(bot, message):
    async def reply(text):
        await message.channel.send(text, allowed_mentions=discord.AllowedMentions.none())
    if not message.author.guild_permissions.manage_guild:
        await reply('Only members with Manage Server permission can link registrations.')
        return
    parts = message.content.split()
    if len(parts) != 3 or not parts[1].isdigit() or not re.fullmatch(r'<@!?\d+>', parts[2]):
        await reply('Usage: !linkmember <registration ID> @member — for example !linkmember 9001 @yourself')
        return
    user_id = int(re.sub(r'\D', '', parts[2]))
    member = message.guild.get_member(user_id)
    if member is None:
        try:
            member = await message.guild.fetch_member(user_id)
        except discord.HTTPException:
            await reply('Could not verify that account in this server. Try again.')
            return
    if member.bot:
        await reply('Bot accounts cannot enter giveaways.')
        return
    try:
        link_member(bot.db, message.guild.id, user_id, int(parts[1]))
    except ValueError as error:
        await reply(str(error))
        return
    await reply('Registration linked. This member can now enter giveaways.')
