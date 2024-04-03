from interactions import (
    Extension, Embed, OptionType,
    SlashContext, AutocompleteContext,
    slash_command, slash_option,
)
from misc.colors import ERROR_COLOR, KAVANI_COLOR
from misc.system_autocomplete import get_system_autocomplete

class Remove(Extension):
    @slash_command(
        name="remove",
        description="Moderator-only: Removes a logged system from the bot"
    )
    @slash_option(
        name="system",
        description="Name of the system. Must be one of the supplied options:",
        autocomplete=True, required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="reason",
        description="Reason for removal",
        opt_type=OptionType.STRING
    )
    async def remove(self, ctx: SlashContext, system: str, reason: str = "No reason specified"):
        #make sure system is valid, if not send an error emssage to user
        if system not in self.bot.SYSTEMS["All"]:
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"The system `{system}` could not be found!\nPlease make sure you're using the autocomplete.",
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return

        #make sure the system is in the bot somewhere
        in_capturables = self.bot.capturables.has(system)
        in_timers = self.bot.timers.has(system)
        if not (in_capturables or in_timers):
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"`{system}` is not currently reported as a timer or capturable."
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return
        
        #cache the entry for logging purposes
        entry = (self.bot.timers if in_timers else self.bot.capturables).get(system)

        #actually remove the thing
        if in_capturables:
            await self.bot.capturables.remove(system)
        else:
            await self.bot.timers.remove(system)

        from_section = f"from the {'Timers' if in_timers else 'Capturable'} section"

        #log the moderator action
        embed = Embed(
            title="System removed by moderator", color=KAVANI_COLOR,
            description=f"A system originally added by {entry.get_added_data()},\nwas removed by moderator {ctx.user.mention} {from_section}."
        )
        embed.add_field("Reason", reason)
        embed.add_field("System Data", f"System: {entry.get_system_data()}\nWas capturable {entry.get_capture_data()}")
        await self.bot.logging.log(embeds=[embed])
        
        embed = Embed(
            title="Success", color=KAVANI_COLOR,
            description=f"Successfully removed `{system}` {from_section}."
        )
        await ctx.send(embeds=embed, ephemeral=True)

    @remove.autocomplete("system")
    async def system_autocomplete(self, ctx: AutocompleteContext):
        #get a list of valid systems (capturable/timer systems)
        valid_systems = [s.name for s in [
            *self.bot.capturables._systems.values(),
            *self.bot.timers._systems.values()
        ]]
        
        #respond to autocomplete context
        choices = get_system_autocomplete(ctx.input_text, valid_systems)
        await ctx.send(choices=choices)