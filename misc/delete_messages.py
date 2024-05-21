from interactions import Extension, listen
from interactions.api.events import MessageCreate

class DeleteMessages(Extension):
    @listen(MessageCreate)
    async def delete_messages(self, message_event: MessageCreate):
        message = message_event.message
        #don't delete yourself stupid
        if message.author.id == self.bot.user.id: return
        #don't delete command stuffs
        if message.interaction: return
        #dont delete me :( 
        if message.author.id == self.bot.owner.id: return

        #ok its fine to delete now
        if message.channel.id == self.bot.config["main_channel"]:
            await message.delete()