import os, json, asyncio
import dotenv

from misc.colors import KAVANI_COLOR; dotenv.load_dotenv()

from interactions import Client, Embed, EmbedFooter, Intents, listen

input("Please make sure to edit this file with correct role, channel, and command IDs! Press enter to continue.")

bot = Client(intents=Intents.DEFAULT)

#load config file
with open(os.path.join(os.getcwd(), "config.json"), "r") as config_file:
    bot.config = json.loads(config_file.read())

notif_role = 856889574638616587
notif_thread = 1223631958953689160
role_get_channel = 1221830865928323092
logs_thread = 1223294878440493096

timer_id = 0
capturable_id = 0
capture_id = 0

description = f"""Welcome to the Kavani Mandate SystemTracker v2!
This bot helps track timers and capturable systems for faction warfare.
- Notifications (<@&{notif_role}>) for capturable systems are posted in <#{notif_thread}>
    - You can get the role from <#{role_get_channel}>
- Timers & capturable systems can be found below, and all actions are logged in <#{logs_thread}>
- Contact a moderator to report any errors or abuse"""
cmd_description = f"""- </timer:0> - Adds a system timer to the bot
- </capturable:0> - Adds a capturable system to the bot
- </capture:0> - Marks a capturable system as captured
    - You can also use the buttons in <#{notif_thread}> for this!
Try each command for further help and a more detailed description!
"""

@listen()
async def on_ready():
    channel = await bot.fetch_channel(bot.config["main_channel"])
    embed = Embed(
        title="SystemTracker", color=KAVANI_COLOR,
        description=description,
        footer=EmbedFooter("Tip: All timestamps are automatically converted to your local timezone")
    )
    embed.add_field("Commands", value=cmd_description)
    await channel.send(embed=embed) #type:ignore
    embed = Embed(title="Setup...")
    await channel.send(embed=embed) #type:ignore

    print("Setup finished! Make sure to update config.json with new message IDs.")
    print("In particular, the `help_` and `main_message` will need changing.")
    await bot.stop()
bot.start(os.getenv("DISCORD_TOKEN"))