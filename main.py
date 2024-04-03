import os, json, time, asyncio
import dotenv; dotenv.load_dotenv()
import motor.motor_asyncio
from interactions import Client, Intents, IntervalTrigger, SlashContext, Task, listen

from structures.systems import CapturableManager, TimerManager
from structures.logger  import Logger

bot = Client(intents=Intents.DEFAULT)

#load config file
with open(os.path.join(os.getcwd(), "config.json"), "r") as config_file:
    bot.config = json.loads(config_file.read())

#initialize list of contested systems for autocomplete  
data_path = os.path.join(os.getcwd(), "contested_systems.json")
with open(data_path, "r") as data_file:
    contents = data_file.read()
    bot.SYSTEMS = json.loads(contents)
    bot.SYSTEMS["All"] = [*bot.SYSTEMS["Foralkan"], *bot.SYSTEMS["Lycentian"]]

@listen()
async def on_ready():
    #set up the managers for timers and capturable systems
    bot.timers = await TimerManager.new(bot, bot.db["timers"])
    bot.capturables = await CapturableManager.new(bot, bot.db["capturable"])

    #set up the logger
    bot.logging = await Logger.new(bot)
    
    #get interval checking going
    async def interval():
        timestamp = int(time.time())
        to_remove = list(filter(lambda t: t.capturable <= timestamp, bot.timers._systems.values()))
        for timer in to_remove:
            await bot.timers.remove(timer.name)
            await bot.capturables.add(timer, log=False)
            await bot.logging.log_capturable(timer)
    await interval() #run initial checks immediately
    Task(interval, IntervalTrigger(seconds=10)).start()

    #update the messages initially
    await bot.timers.update_message()
    await bot.capturables.update_message()

    print("Bot started!")

async def main():
    #initialize the DB
    db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
    bot.db = db_client[bot.config["database_name"]]

    #load all the commands
    bot.load_extensions("commands")
    #load other misc things like the error handler and message deleter
    bot.load_extension("misc.handle_errors")
    bot.load_extension("misc.delete_messages")


    #globally add a check for role denylist
    async def check(ctx: SlashContext) -> bool:
        return not ctx.member.has_role(bot.config["deny_role"])#type:ignore
    
    for extension in bot.ext.values():
        extension.add_ext_check(check) #type:ignore

    #start the bot
    await bot.astart(os.getenv("DISCORD_TOKEN"))

#run main
asyncio.run(main())

