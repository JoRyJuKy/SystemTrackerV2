import re
from typing import Union
from interactions import (
    Extension,
    SlashContext, AutocompleteContext, ComponentContext,
    Embed, OptionType, Buckets,
    component_callback, cooldown, slash_command, slash_option
)

from misc.system_autocomplete import get_system_autocomplete
from misc.colors import ERROR_COLOR, KAVANI_COLOR

system_name_pattern = re.compile(r": ([a-zA-Z0-9'\- ]+) \[")

class Capture(Extension):
    async def capture(self, ctx: Union[SlashContext, ComponentContext], system: str, handle_deletion: bool):
        #make sure system is marked as capturable
        if not self.bot.capturables.has(system):
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"`{system}` is not currently marked as capturable!"
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return

        entry = self.bot.capturables.get(system)
        await self.bot.capturables.remove(system)

        if handle_deletion:
            #delete the alert message
            channel = await self.bot.fetch_channel(self.bot.config["main_channel"])
            thread = [
                t for t in (await channel.fetch_all_threads()).threads 
                if t.id == self.bot.config["alerts_thread"]
            ][0]
            msg = await thread.fetch_message(entry.message_id)
            if msg: await msg.delete()
        
        #send the success message
        embed = Embed(
            title="Success", color=KAVANI_COLOR,
            description=f"{entry.get_system_data()} was marked as captured!"
        )
        await ctx.send(embeds=embed, ephemeral=True)
        await self.bot.logging.log_capture(entry, ctx.user.id)

    @component_callback("button_capture_system")
    async def capture_button_pressed(self, ctx: ComponentContext):
        msg = ctx.message
        if not msg: 
            print("capture.py: Could not find message on button press")
            return

        #get the system from the id with some regex
        embed_desc = msg.embeds[0].description
        if not embed_desc:
            print("capture.py: Could not get description from first embed:")
            print(msg.embeds[0])
            return

        match = system_name_pattern.search(embed_desc)
        if not match:
            print("capture.py: Regex did not produce any matches for system name")
            return
        system = match.group(1)

        await msg.delete()
        await self.capture(ctx, system, False)

    @slash_command(
        name="capture",
        description="Marks a system as captured."
    )
    @cooldown(Buckets.USER, 1, 30)
    @slash_option(
        name="system",
        description="Name of the system. Must be one of the supplied options:",
        autocomplete=True, required=True,
        opt_type=OptionType.STRING
    )
    async def capture_command(self, ctx: SlashContext, system: str):
        #make sure system is valid, if not send an error emssage to user
        if system not in self.bot.SYSTEMS["All"]:
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"The system `{system}` could not be found!\nPlease make sure you're using the autocomplete.",
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return
        await self.capture(ctx, system, True)
    
    @capture_command.autocomplete("system")
    async def system_autocomplete(self, ctx: AutocompleteContext):
        capturable_systems = [s.name for s in self.bot.capturables._systems.values()]
        choices = get_system_autocomplete(ctx.input_text, capturable_systems)
        await ctx.send(choices=choices)