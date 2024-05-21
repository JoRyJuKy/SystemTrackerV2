import asyncio, time
from interactions import (
    Button, ButtonStyle, Extension, Attachment, 
    Embed, EmbedFooter, File,
    SlashContext, OptionType, Buckets, listen, 
    slash_command, slash_option, cooldown
)
from interactions.api.events import Startup
from misc.colors import ERROR_COLOR, KAVANI_COLOR
from misc.detector import initialize, detect as detect_from_url
from structures.systems import System

class Detect(Extension):

    @listen(Startup)
    async def startup(self):
        await initialize()
        print("Detector has been initialized.")

    @slash_command(
        name="detect",
        description="Detects system info from a screenshot. Please include the timer, system name, and system tier!"
    )
    @cooldown(Buckets.USER, 1, 30)
    @slash_option(
        name="screenshot",
        description="The screenshot to detect from.",
        required=True, opt_type=OptionType.ATTACHMENT
    )
    async def detect(self, ctx: SlashContext, screenshot: Attachment):
        #make sure the attachment is a valid image type
        if screenshot.content_type not in ["image/bmp", "image/jpeg", "image/jpg", "image/png"]:
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description=f"That screenshot's file type is not supported.\nPlease contact <@!{self.bot.owner.id}> if you think it should be.",
                footer=EmbedFooter(f"File type: {screenshot.content_type}")
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return
        
        await ctx.send(ephemeral=True, embeds=Embed(
            title="Detecting...", color=KAVANI_COLOR
        ))
        result = await detect_from_url(screenshot.url)

        #make sure a result was actually received 
        if not result:
            embed = Embed(
                title="Error", color=ERROR_COLOR,
                description="Image detection failed!\nThis could be because the internal detector failed, or because your screenshot does not have adequate information.",
                footer=EmbedFooter("This image has been sent to the developer, to hopefully improve future detection.") 
            )
            await ctx.edit(embeds=embed)

            owner = self.bot.owner
            await owner.send(f"Image detection failed for the following image: {screenshot.url}")
            return
        
        result, img_buffer = result
        
        system, tier = result.name, result.tier
        is_timer = bool(result.capturable)
        owner = "Foralkan" if system in self.bot.SYSTEMS["Foralkan"] else "Lycentian"

        current_timestamp = int(time.time())
        capturable_timestamp = result.capturable if is_timer else current_timestamp

        entry = System(system, owner, tier, capturable_timestamp, current_timestamp, ctx.user.id, None) #type:ignore

        #SECTION: Get confirmation that the image detection is correct
        
        #send a confirmation message
        conf_embed = Embed(
            title="Confirmation", color=KAVANI_COLOR,
            description="Are these detection results correct?",
            footer=EmbedFooter("Times are adjusted to your timezone\nAccepted after 30 seconds"),
        ).add_field("System", entry.get_system_data(), True)

        #make sure "Immediately" is set for capturable time if it willb e immedieately capturable
        capturable_value = entry.get_capture_data() if is_timer else "*Immediately*"
        conf_embed.add_field("Capturable", capturable_value, True)

        #create confirmation buttons
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
        #create cropped image file
        image_file = File(img_buffer, "image.png", "Cropped image", "image/png")

        await ctx.edit(embeds=conf_embed, components=conf_buttons, files=[image_file])
        ctx.message
        
        #this ensures that the user selected confirm. bit messy since we have to handle timeouts
        #if it timeouts after 30 seconds then this is seen as a confirmation of sending.
        try:
            result = await self.bot.wait_for_component(components=conf_buttons, timeout=30)
            if result.ctx.custom_id == "add_system_confirmation_deny":
                await result.ctx.edit_origin(embeds=Embed(title="Cancelled", color=KAVANI_COLOR), components=[])
                await ctx.command.cooldown.reset(ctx)
                return
        except asyncio.TimeoutError: pass

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
            await ctx.edit(embeds=embed, components=[])
            await ctx.command.cooldown.reset(ctx)
            return
        

        #if reached here, we know the detection is successful, so send a success message and add teh system to the managers
        success_embed = Embed(
            title="Success", color=KAVANI_COLOR,
            description=f"Successfully added {system}",
            footer=EmbedFooter("System will be added to list shortly")
        )
        await ctx.edit(embeds=success_embed, components=[])

        if not is_timer:
            entry.message_id = await self.bot.logging.log_capturable(entry)
        await (self.bot.timers if is_timer else self.bot.capturables).add(entry)