# SystemTracker V2
A (somewhat scuffed) discord bot for tracking faction warfare timers in the Roblox game [Starscape](https://www.roblox.com/games/679715583/Starscape-Beta).   
Written in Python with the [interactions.py library](https://interactions-py.github.io/interactions.py/), and [OpenCV](https://opencv.org/) with [EasyOCR](https://github.com/JaidedAI/EasyOCR) for image recognition.  
Originally made for the joint SB-S & H.J.S. Kavani Mandate server.  

## Setup Instructions
- Clone this repository locally/on your server, and activate the [python virtual environment](https://docs.python.org/3/library/venv.html)
- Create a MongoDB instance (I use their web platform [Atlas](https://www.mongodb.com/atlas))
   - Create a database in the instance, with two collections: `capturable` and `timers`
   - If using Atlas, it should look something like:  
![image](https://github.com/JoRyJuKy/SystemTrackerV2/assets/56680281/ef85e717-c2af-4eb5-811a-b9854548aebd)
- Create a `.env` file, with the following contents:
  - Your bot token is the Bot token you get from the [Discord Developers](https://discord.com/developers/) page (See [the discord.js guide](https://discordjs.guide/preparations/setting-up-a-bot-application.html#your-bot-s-token))
  - Your MongoDB connection URI is the [URI](https://stackoverflow.com/a/4239952) to connect to your Mongo Database (See [the Mongo docs](https://www.mongodb.com/docs/manual/reference/connection-string/))
```env
DISCORD_TOKEN="your-bot-token"
MONGO_URI="your-mongodb-connection-URI"
```
- Edit [`config.json`](https://github.com/JoRyJuKy/SystemTrackerV2/blob/298458945492fa9c7a55f93ba092e3aab0364b82/config.json) (All IDs should be numbers, not strings):
```js
{
    "main_guild": ID of the main server (guild),
    "main_channel": ID of the channel designated for the bot,
    "database_name": "Name of the database for the bot in your MongoDB instance",
    "logging_thread": ID of the thread for the bot to log actions,
    "alerts_thread": ID of the thread for the bot to send notification alerts,
    "notify_role": ID of the role the bot should ping for notifications,
    "deny_role": ID of the role to deny access to the entirety of the bot,
}
(help_message and main_message get automatically set later)
```
- Update the Discord emoji IDs in [`structures/systems.py`](https://github.com/JoRyJuKy/SystemTrackerV2/blob/298458945492fa9c7a55f93ba092e3aab0364b82/structures/systems.py#L39)
- If your server has a GPU available, you may want to enable GPU usage for EasyOCR by setting `gpu=True` in [`misc/detector.py`](https://github.com/JoRyJuKy/SystemTrackerV2/blob/298458945492fa9c7a55f93ba092e3aab0364b82/misc/detector.py#L205)
- Run [`run_setup.py`](https://github.com/JoRyJuKy/SystemTrackerV2/blob/298458945492fa9c7a55f93ba092e3aab0364b82/run_setup.py), which will send the main and help messages in `main_channel`, and update the config file accordingly
  - Note: The commands in the help message will not update until the next step. This is intentional.
- You're ready to go! Run [`main.py`](https://github.com/JoRyJuKy/SystemTrackerV2/blob/298458945492fa9c7a55f93ba092e3aab0364b82/main.py) to start the bot. You may have to refresh discord for the slash commands to update!
