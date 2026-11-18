"""Register this branch's slash commands on the shared command tree."""
import os
import discord
from discord import app_commands


def register_commands(client: discord.Client) -> app_commands.CommandTree:
    tree = getattr(client, 'tree', None)
    if tree is None:
        tree = app_commands.CommandTree(client)
        client.tree = tree

    if getattr(client, '_gwc_commands_registered', False):
        return tree

    @tree.command(name='registration', description='Receive your private member registration DM')
    @app_commands.guild_only()
    async def registration(interaction: discord.Interaction):
        if interaction.guild is None or interaction.user.bot:
            await interaction.response.send_message('Use this command in the club server.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        sent = await client.welcome.send_registration_dm(
            f'slash:{interaction.id}', interaction.user, interaction.guild)
        await interaction.followup.send(
            'Your registration card is waiting in your DMs! 💙✨' if sent else
            'Please enable DMs from server members and try /registration again. 💙', ephemeral=True)

    @tree.command(name='giveaway', description='Create a club giveaway')
    @app_commands.guild_only()
    async def giveaway(interaction: discord.Interaction):
        await client.giveaways.handle_interaction(interaction)

    client._gwc_commands_registered = True
    return tree


async def sync_commands(client, tree):
    guild_id = os.environ.get('GUILD_ID', '').strip()
    if guild_id and (not guild_id.isdigit() or int(guild_id) <= 0):
        raise ValueError('GUILD_ID must be a positive numeric server ID')
    # Upsert this branch's commands without deleting other developers' commands.
    for command in tree.get_commands():
        payload = command.to_dict(tree)
        if guild_id:
            await client.http.upsert_guild_command(client.application_id, int(guild_id), payload=payload)
        else:
            await client.http.upsert_global_command(client.application_id, payload=payload)
