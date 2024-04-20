import enum
import time
from typing import Optional
from interactions import BaseComponent, Button, ButtonStyle, Client, Embed, GuildText, Message, ThreadChannel

from misc.colors import KAVANI_COLOR
from structures.systems import MessageId, System, Timestamp, UserId

class WhichThread(enum.Enum):
    Logs = 1
    Alerts = 2

class Logger():
    """
    Used for logging to a logging thread.
    """
    bot: Client
    last_pinged: Timestamp
    _logs_thread: ThreadChannel
    _alerts_thread: ThreadChannel

    @classmethod
    async def new(cls, bot: Client):
        self = cls()
        self.bot = bot
        self.last_pinged = 0

        channel = await self.bot.fetch_channel(self.bot.config["main_channel"])
        if not isinstance(channel, GuildText): raise TypeError("Wrong channel type for logger!")

        all_threads = (await channel.fetch_all_threads()).threads
        def pick_thread(id):
            return [t for t in all_threads if t.id==id][0]
        
        self._logs_thread = pick_thread(self.bot.config["logging_thread"])
        self._alerts_thread = pick_thread(self.bot.config["alerts_thread"])
        
        return self

    async def log(self, 
        text      : Optional[str]                 = None, 
        embeds    : Optional[list[Embed]]         = None, 
        components: Optional[list[BaseComponent]] = None,
        thread    : WhichThread = WhichThread.Logs
    ) -> Message:
        send_thread = self._logs_thread if thread == WhichThread.Logs else self._alerts_thread
        return await send_thread.send(content=text, embeds=embeds, components=components)

    async def log_capturable(self, capturable: System) -> MessageId:
        embed = Embed(
            title="System capturable:", color=KAVANI_COLOR,
            description=f"**{capturable.get_system_data()}** can be captured!"
        )
        button = Button(
            label="Mark as Captured", style=ButtonStyle.SUCCESS,
            custom_id="button_capture_system"
        )
        
        #make sure pinging doesn't happen too often
        log_text = f"`{capturable.name}` is now capturable"
        current_time = round(time.time())
        if abs(current_time - self.last_pinged) >= 60:
            log_text = log_text + f" <@&{self.bot.config['notify_role']}>"
            self.last_pinged = current_time

        log_msg = await self.log(
            text=log_text, embeds=[embed],
            thread=WhichThread.Alerts, components=[button]
        )
        return log_msg.id

    async def log_capture(self, capture: System, by: UserId):
        embed = Embed(
            title="System captured:", color=KAVANI_COLOR,
            description=f"**{capture.get_system_data()}** was marked as captured!"
        ).add_field("Reported by", f"<@{by}>")
        await self.log(embeds=[embed])