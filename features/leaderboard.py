"""Read-only points leaderboard commands and embed rendering."""
import math
import discord

PAGE_SIZE = 10


def leaderboard_page(db, page=1):
    if page < 1:
        raise ValueError('Page must be at least 1.')
    total = db.execute("SELECT COUNT(*) FROM Members WHERE member_status='active'").fetchone()[0]
    pages = max(1, math.ceil(total / PAGE_SIZE))
    if page > pages:
        raise ValueError(f'Choose a page from 1 to {pages}.')
    rows = db.execute('''
        SELECT member_id, first_name, last_name, points_balance,
               RANK() OVER (ORDER BY points_balance DESC) AS rank
        FROM Members WHERE member_status='active'
        ORDER BY points_balance DESC, first_name COLLATE NOCASE,
                 last_name COLLATE NOCASE, member_id
        LIMIT ? OFFSET ?
    ''', (PAGE_SIZE, (page - 1) * PAGE_SIZE)).fetchall()
    return rows, total, pages


def leaderboard_embed(rows, total, pages, page=1, thumbnail_url=None):
    lines = []
    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    for row in rows:
        # Keep even unusually long or formatted names within Discord's embed limit.
        raw_name = ' '.join(f"{row['first_name']} {row['last_name']}".split())[:60]
        name = discord.utils.escape_mentions(discord.utils.escape_markdown(raw_name))
        badge = medals.get(row['rank'], '🏅')
        lines.append(f"{badge} **#{row['rank']} · {name}** — {row['points_balance']:,} points")
    description = '\n\n'.join(lines) if lines else 'No active members yet. Join the club to get started! 💙'
    if pages > 1:
        description += '\n\nUse `!leaderboard <page>` to see more members.'
    embed = discord.Embed(title='🏆 Girls Who Code Points Leaderboard', description=description, colour=0x82A7DB)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text=f'Girls Who Code @ UCF 🤍 Code • Connect • Create | Page {page}/{pages} • {total} members')
    return embed


class LeaderboardFeature:
    def __init__(self, bot):
        self.bot = bot

    async def handle_message(self, message):
        parts = message.content.split()
        async def reply(text):
            await message.channel.send(text, allowed_mentions=discord.AllowedMentions.none())
        if parts[0].lower() == '!testleaderboard' and not self.bot.test_mode:
            await reply('Use !leaderboard, or restart with --test-mode for fictional member tests.')
            return
        try:
            if len(parts) > 2:
                raise ValueError
            page = int(parts[1]) if len(parts) == 2 else 1
            if page < 1:
                raise ValueError
        except ValueError:
            await reply('Usage: !leaderboard [page], for example !leaderboard 2')
            return
        try:
            rows, total, pages = leaderboard_page(self.bot.db, page)
        except ValueError as error:
            await reply(str(error))
            return
        thumbnail = str(self.bot.user.display_avatar.url) if self.bot.user else None
        await message.channel.send(
            embed=leaderboard_embed(rows, total, pages, page, thumbnail),
            allowed_mentions=discord.AllowedMentions.none(),
        )
