import os, json
import dotenv; dotenv.load_dotenv()

from misc.colors import KAVANI_COLOR
from interactions import Client, Embed, EmbedFooter, Intents, listen

input("Please ensure config.json is pre-updated with thread, channel, and role IDs. Press enter to continue.")

bot = Client(intents=Intents.DEFAULT)

#load config file
with open(os.path.join(os.getcwd(), "config.json"), "r") as config_file:
    bot.config = json.loads(config_file.read())

notif_role = bot.config["notify_role"]
notif_thread = bot.config["alerts_thread"]
logs_thread = bot.config["logging_thread"]
role_get_channel = int(input("Input reactions role channel id: "))

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
    help_msg = await channel.send(embed=embed) #type:ignore
    embed = Embed(title="Setup...")
    main_msg = await channel.send(embed=embed) #type:ignore
    await bot.stop()

    bot.config["help_message"] = help_msg.id
    bot.config["main_message"] = main_msg.id

    with open(os.path.join(os.getcwd(), "config.json"), "w") as config_file:
        config_file.write(json.dumps(bot.config, indent=4))

bot.start(os.getenv("DISCORD_TOKEN"))