import asyncio, re, time
from interactions import (
    Extension,
    SlashContext, SlashCommandChoice, AutocompleteContext, 
    slash_command, slash_option, cooldown, 
    OptionType, Buckets,
    Button, ButtonStyle,
    Embed, EmbedFooter
)
from misc.system_autocomplete import get_system_autocomplete
from structures.systems import System
from misc.colors import KAVANI_COLOR, ERROR_COLOR

timer_pattern = re.compile(r"\d:\d{1,2}")

class TimerAndCapturable(Extension):
    @slash_command(
        name="timer",
        description="Adds a timer to the database"
    )
    @cooldown(Buckets.USER, 1, 30)
    @slash_option(
        name="system",
        description="Name of the system. Must be one of the supplied options:",
        autocomplete=True, required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="tier",
        description="Tier of the system's defenses.",
        required=True, opt_type=OptionType.INTEGER,
        choices=[SlashCommandChoice(name, i) for i, name in enumerate([
            "New Claim",
            "Outpost",
            "Garrison",
            "Stronghold"
        ])]
    )
    @slash_option(
        name="timer",
        description="Time until system is capturable. Can be from 0:01 to 6:59. Format: `h:mm`.",
        required=True, opt_type=OptionType.STRING
    )
    async def timer(self, 
            ctx: SlashContext, 
            system: str,
            tier: int,
            timer: str,
            bypass_timer_checks: bool = False
        ):
        #make sure system is valid, if not send an error emssage to user
        if system not in self.bot.SYSTEMS["All"]:
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"The system `{system}` could not be found!\nPlease make sure you're using the autocomplete.",
            )
            await ctx.send(embeds=embed, ephemeral=True)
            await ctx.command.cooldown.reset(ctx)
            return
        
        #get the owner
        owner = "Foralkan" if system in self.bot.SYSTEMS["Foralkan"] else "Lycentian"
        
        #get mins/hours from the timer, ensuring the timer is valid
        match = timer_pattern.search(timer)
        if not match:
            command_str = f"</{self.timer.name}:{self.timer.get_cmd_id(0)}>" #type:ignore
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"Could not read the timer!\nPlease make sure it's in the format `h:mm`\nExample: {command_str} `Arab Lycentian 4:25`"
            )
            await ctx.send(embeds=embed, ephemeral=True)
            await ctx.command.cooldown.reset(ctx)
            return
        
        hours_until, mins_until = map(int, match.group().split(":"))
        if (
            (not bypass_timer_checks) and
            (hours_until > 6 or mins_until > 59 or mins_until < 1)
        ):
            command_str = f"</{self.capturable.name}:{self.capturable.get_cmd_id(0)}>" #type:ignore
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"Timer provided was too short or long! Timers must be between 0:01 and 6:59.\nTo report a capturable system, use {command_str}"
            )
            await ctx.send(embeds=embed, ephemeral=True)
            await ctx.command.cooldown.reset(ctx)
            return

        #determine the number of seconds until capturable, for timestamp purposes
        secs_until = (mins_until + (hours_until * 60)) * 60
        is_timer = secs_until > 0
        
        #make sure system isn't already reported
        in_timers = self.bot.timers.has(system)
        in_capturable = self.bot.capturables.has(system)
        if in_timers or in_capturable:
            ex_data: System = (self.bot.timers if in_timers else self.bot.capturables).get(system)
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"The system `{system}` is already listed!\nPlease contact a moderator if you think the current listing is incorrect:"
            )
            embed.add_field("System", ex_data.get_system_data(), True)
            if is_timer: 
                embed.add_field("Capturable", ex_data.get_capture_data(), True)
            embed.add_field("Added By", ex_data.get_added_data())
            await ctx.send(embeds=embed, ephemeral=True)
            await ctx.command.cooldown.reset(ctx)
            return
        
        currrent_timestamp = int(time.time())
        capturable_timestamp = currrent_timestamp + secs_until

        entry = System(system, owner, tier, capturable_timestamp, currrent_timestamp, ctx.user.id, None)

        #send a confirmation message
        conf_embed = Embed(
            title="Confirmation", color=KAVANI_COLOR,
            description="Adding the following system. Is this okay?",
            footer=EmbedFooter("Times are adjusted to your timezone\nAccepted after 30 seconds")
        ).add_field("System", entry.get_system_data(), True)

        #make sure "Immediately" is set for capturable time if it willb e immedieately capturable
        capturable_value = entry.get_capture_data() if is_timer else "*Immediately*"
        conf_embed.add_field("Capturable", capturable_value, True)

        conf_buttons = [
            Button( #confirmation button
                custom_id="add_system_confirmation_confirm",
                label="Yes", style=ButtonStyle.SUCCESS
            ),
            Button( #deny button
                custom_id="add_system_confirmation_deny",
                label="No", style=ButtonStyle.DANGER
            )
        ]
        await ctx.send(embeds=conf_embed, components=conf_buttons, ephemeral=True)
        
        #this ensures that the user selected confirm. bit messy since we have to handle timeouts
        #if it timeouts after 30 seconds then this is seen as a confirmation of sending.
        try:
            result = await self.bot.wait_for_component(components=conf_buttons, timeout=30)
            if result.ctx.custom_id == "add_system_confirmation_deny":
                await result.ctx.edit_origin(embeds=Embed(title="Cancelled", color=KAVANI_COLOR), components=[])
                await ctx.command.cooldown.reset(ctx)
                return
        except asyncio.TimeoutError: pass

        success_embed = Embed(
            title="Success", color=KAVANI_COLOR,
            description=f"Successfully added {system}",
            footer=EmbedFooter("System will be added to list shortly")
        )
        await ctx.edit(embeds=success_embed, components=[])

        if not is_timer:
            entry.message_id = await self.bot.logging.log_capturable(entry)
        await (self.bot.timers if is_timer else self.bot.capturables).add(entry)
        

    @timer.autocomplete("system")
    async def timer_autocomplete_system(self, ctx: AutocompleteContext):
        choices = get_system_autocomplete(ctx.input_text, self.bot.SYSTEMS["All"])
        await ctx.send(choices=choices)
        

    @slash_command(
        name="capturable",
        description="Adds a capturable system to the database"
    )
    @cooldown(Buckets.USER, 1, 30)
    @slash_option(
        name="system",
        description="Name of the system. Must be one of the supplied options:",
        autocomplete=True, required=True,
        opt_type=OptionType.STRING
    )
    @slash_option(
        name="tier",
        description="Tier of the system's defenses.",
        required=True, opt_type=OptionType.INTEGER,
        choices=[SlashCommandChoice(name, i) for i, name in enumerate([
            "New Claim",
            "Outpost",
            "Garrison",
            "Stronghold"
        ])]
    )
    async def capturable(self, ctx: SlashContext, system: str, tier: int, force: bool=False):
        await self.timer.callback( #type:ignore
            ctx=ctx, 
            system=system,
            tier=tier,
            timer="0:0",
            bypass_timer_checks=True
        )
    
    @capturable.autocomplete("system")
    async def capturable_autocomplete_system(self, ctx: AutocompleteContext):
        choices = get_system_autocomplete(ctx.input_text, self.bot.SYSTEMS["All"])
        await ctx.send(choices=choices)