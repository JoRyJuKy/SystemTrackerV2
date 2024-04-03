#NOTE:
"""
This file is for categorizing systems into lycentian/foralkan fronts based on their positions
It needs a mapdata.json file
This probably won't ever be needed again, but I'm leaving it here incase some value was wrong and the systems need updating.
"""

import json
sys_data = None
with open("./mapdata.json") as f:
    sys_data = json.loads(f.read())

lycentian = []
foralkan = []
other = []

for system, data in sys_data.items():
    if data["SecurityLevel"] != "Contested": continue

    y, x, z = map(float, data["Location"].split(", "))
    if x > 100 and y < 30:
        lycentian.append(system)
    elif x > -346 and y > 670:
        foralkan.append(system)
    else:
        other.append(system)

new = {
    "Lycentian": lycentian,
    "Foralkan": foralkan
}
with open("./contested_systems.json", "w") as f:
    f.write(json.dumps(new))