from typing import Optional
from dataclasses import dataclass
from motor.motor_asyncio import AsyncIOMotorCollection
from interactions import Embed, Guild, GuildText, Message, Client
from interactions.client.utils import bold

from misc.colors import KAVANI_COLOR


#for more clear type hinting
Timestamp = int
UserId    = int
MessageId = int

@dataclass
class System():
    """
    Represents a Contested system, and data about its addition to the DB
    """
    name: str
    owner: str
    tier: int
    capturable: Timestamp
    added: Timestamp
    added_by: UserId
    message_id: Optional[MessageId]

    def get_tier(self) -> str:
        """Gets the string version of this system's tier"""
        return [
            "New Claim",
            "Outpost",
            "Garrison",
            "Stronghold"
        ][self.tier]
    
    def get_system_data(self) -> str:
        """Gets string containing information about system"""
        emoji = '<:Foralkus:1227736614432936057>' if self.owner == 'Foralkan' else '<:Lycentia:1222626949457772695>'
        return f"{emoji} {self.name} [{self.get_tier()}]"
    
    def get_capture_data(self) -> str:
        """Gets string containing information about capturability"""
        return f"<t:{self.capturable}:R>, at <t:{self.capturable}:t>"
    
    def get_added_data(self) -> str:
        """Gets string containing information about this system's addition to the DB"""
        return f"<@{self.added_by}>, on <t:{self.added}:f>"
    

class BaseManager():
    """
    Base manager representing a collection of Systems and its associated functionality.
    Designed to be extended by children classes, do not use on its own.
    """
    bot: Client
    collection: AsyncIOMotorCollection
    _systems: dict[str, System]
    _channel: GuildText

    @classmethod
    async def new(cls, bot: Client, collection: AsyncIOMotorCollection):
        """Creates a new manager"""
        self = cls()

        #initialize the reference to the bot and an empty systems dict
        self.bot = bot
        self.collection = collection
        self._systems = {}

        #initialize the systems from the db
        async for document in self.collection.find(projection={"_id": False}):
            self._systems[document["name"]] = System(**document)

        #fetch the main guild
        guild = await self.bot.fetch_guild(self.bot.config["main_guild"])
        if not guild: raise RuntimeError("Could not fetch guild for manager!")

        #fetch the main channel with some typechecking shenanigans
        _channel = await guild.fetch_channel(self.bot.config["main_channel"])
        if not isinstance(_channel, GuildText): raise TypeError("Wrong channel type for manager!")
        self._channel = _channel 

        return self
        

    async def fetch_message(self) -> Message:
        """Freshly fetches the discord message for this manager"""
        msg = await self._channel.fetch_message(self.bot.config["main_message"], force=True)
        if msg == None: #make sure message could be fetched
            raise RuntimeError("Couldn't fetch the main message for TimerManager")
        
        return msg
    
    async def update_message(self):
        """Updates the discord message for this manager with new information."""
        pass #must be defined in child classes
    
    async def add(self, system: System, log: bool = True):
        """
        Adds the specified system to the manager. 
        Implicitly updates the manager's message and logs the addition, as well.
        """
        self._systems[system.name] = system
        await self.collection.replace_one(
            filter={"name": system.name},
            replacement=system.__dict__,
            upsert=True
        )

        await self.update_message()

        #log the addition as an embed
        if not log: return #make sure we actually want to
        capturable_message = "*Immediately*" if system.capturable == system.added else system.get_capture_data()
        embed = Embed(
            title="System added:", color=KAVANI_COLOR,
            description=system.get_system_data()
        )\
            .add_field("Capturable", capturable_message, True)\
            .add_field("Added by", system.get_added_data(), True)
        await self.bot.logging.log(embeds=[embed])

    async def remove(self, name: str):
        """
        Removes a system from the manager, searching by name
        Automatically updates the associated discord message
        """
        del self._systems[name]
        await self.collection.delete_one({"name": name})

        await self.update_message()

    def get(self, name: str) -> Optional[System]:
        """Gets a system from the manager by name"""
        if name not in self._systems: return None
        return self._systems[name]
    
    def has(self, name: str) -> bool:
        """Checks (by name) if a system exists in the maanger"""
        return name in self._systems

class CapturableManager(BaseManager):
    """Manager respresenting currently capturable FW systems"""

    async def update_message(self):
        """
        Updates this manager's message embed with fresh information.
        """
        #get the message
        message = await self.fetch_message()
        
        #if there are no capturable systems, exit early
        if not self._systems:
            #if the message has a "capturable" embed, remove it, but keep the "timers" one
            if len(message.embeds) == 2:
                await message.edit(embeds=message.embeds[0])
            return

        #create the new embed
        embed = Embed(title="Capturable:", color=KAVANI_COLOR)
        embed.description = "\n".join(map(lambda s: s.get_system_data(), self._systems.values()))
        embed.description = bold(embed.description)

        #update the existing message with the new embed, keeping the other embed from the TimerManager
        await message.edit(embeds=[message.embeds[0], embed])

class TimerManager(BaseManager):
    """Manager respresenting soon-to-be capturable FW systems."""

    async def update_message(self):
        #get the message
        message = await self.fetch_message()

        #get existing embeds, and begin to create a new one
        other_embeds = message.embeds[1:]
        embed = Embed(title="Timers:", color=KAVANI_COLOR)

        #if there are no timers, note that in the embed, and exit early
        if not self._systems:
            timer_id = self.bot.interactions_by_scope[0]["timer"].cmd_id[0]
            embed.description = f"There are currently no timers set!\nYou can set one with </timer:{timer_id}>"
            await message.edit(embeds=[embed, *other_embeds])
            return
        
        #add the timers to the embed
        for timer in self._systems.values():
            embed.add_field(timer.get_system_data(), timer.get_capture_data())

        #edit the message with the new embed
        await message.edit(embeds=[embed, *other_embeds])