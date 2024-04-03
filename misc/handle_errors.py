import time
from interactions import listen, Embed, Extension
from interactions.api.events import CommandError
from interactions.client.errors import CommandCheckFailure, CommandOnCooldown

from misc.colors import ERROR_COLOR

class CommandErrors(Extension):
    @listen(CommandError, disable_default_listeners=True)
    async def on_cmd_error(self, err):
        if isinstance(err.error, CommandCheckFailure):
            await err.ctx.send(ephemeral=True, embeds=Embed(
                title="Error", color=ERROR_COLOR,
                description="You do not have permissions to run that command!\nThis could be because you are denylisted from the bot."
            ))
        elif isinstance(err.error, CommandOnCooldown):
            ready_time = int(time.time() + err.error.cooldown.get_cooldown_time())
            await err.ctx.send(ephemeral=True, embeds=Embed(
                title="Error", color=ERROR_COLOR,
                description=f"That command is on cooldown!\nTry again in <t:{ready_time}:R>"
            ))
        else:
            await err.ctx.send(ephemeral=True, embeds=Embed(
                title="Error", color=ERROR_COLOR,
                description="An unknown/unhandled error occured running this command. Sorry!"
            ))