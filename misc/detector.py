"""
NOTE: This file kinda sucks!
This file handles multiprocessing for OpenCV image detection. 
It's imports are scattered all over the place in different functions, to limit imports to only sub-processes
There is also usage of globals, to prevent multiple initializations of OCR reader objects and the systems list
Sorry!
"""

import asyncio, io
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

@dataclass
class Result():
    name: str
    tier: int
    capturable: Optional[int]

def _detect(url) -> Optional[tuple[Result, io.BytesIO]]:
    """
    Detects system information from an image at a given web URL
    """
    try:
        #get the globals for OCR usage and name correction
        global reader, systems

        #import libraries for this process
        import re, time
        from urllib import request

        import cv2 as cv
        import numpy as np
        from Levenshtein import distance

        def load_image_from_url(url) -> cv.typing.MatLike:
            """Loads an image from a URL to a OpenCV image"""

            #add a user-agent to the request, to prevent getting 403'ed
            opener = request.build_opener()
            opener.addheaders = [(
                "User-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )]
            request.install_opener(opener)

            #make the actual request
            req = request.urlopen(url)

            #parse it into a OpenCV image
            #from https://stackoverflow.com/a/21062034
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            decoded = cv.imdecode(arr, -1)

            #convert it to 3-length, incase there's an alpha channel
            return decoded[:, :, :3] # :3

        def pick_closest(item, options):
            """Returns the closest option and its index to a string `item`, from a list of supplied options"""
            dists = [distance(item, o) for o in options]
            idx = int(np.argmin(dists))
            return (options[idx], idx)

        def find_structuring_lines(lines):
            """
            Filters through a list of lines, picking out a pair with roughly the same length
            Used for detecting structuring lines that the rest of the detection is based on 
            """
            for line1 in lines:
                len_line1 = np.hypot(*(line1[0] - line1[1]))
                for line2 in lines:
                    if np.array_equal(line1, line2): continue
                    len_line2 = np.hypot(*(line2[0] - line2[1]))
                    len_diffs = abs(len_line1 - len_line2)
                    if len_diffs < 3: return line1, line2
                    
            return None, None
        
        #read in the image
        img = load_image_from_url(url)

        #get the "edges" of the image, really just color-filtered to the little 3-part box on a system info screen
        edges = cv.inRange(img, (55, 55, 55), (65, 65, 65)) #type:ignore

        #detect the lines from the edges, and restructure the result into a nicer data format
        lines = cv.HoughLinesP(edges, 1, np.pi / 180, 100, None, 1, 0)
        lines = [(l[0][:2], l[0][2:]) for l in lines]

        #get the structuring lines from the list of all of them, exit early if they couldn't be found
        line1, line2 = find_structuring_lines(lines)
        if not line1 or not line2: return None

        #SECTION: cropping down the image
        #get the maximum x of any of the line vertices, which will be the right-most crop value
        max_x = max((line1[0][0], line1[1][0], line2[0][0], line2[1][0]))

        #get the height of the bar, adding 1 to account for off-by-one error
        bar_height = abs(line1[0][1] - line2[0][1])+1

        #get the height of the "bottom" and "top" portions of the crop
        #these are based on their ratios to the bar height (7px) on my 1080p monitor
        bottom_height = round((34/7) * bar_height)
        top_height    = round((51/7) * bar_height)

        #determine the top/bottom y coordinates, by adding the heights from the extremeties of the bar positions
        bottom_y = max((line1[0][1], line2[0][1])) + bottom_height
        top_y    = min((line1[0][1], line2[0][1])) - top_height

        #perform the crop, cropping from the bottom_y to top_y, and from 0 to the max x
        img = img[top_y:bottom_y, :max_x]
        #END SECTION: cropping down the image

        #SECTION: Getting the system name
        #get the top subsection of the crop, which contains the System name, as well as the [Contested] marker and Planet info
        top_subsection = img[:top_height]

        #filter out the orange in the box surrounding the Contested text
        orange = cv.inRange(top_subsection, (0, 60, 123), (5, 70, 133)) #type:ignore

        #get a list of vertical bars (the vertical lines in the Contested rectangle)
        #by filtering by the percentage of orange pixels in each column
        percentages = cv.reduce(orange, 0, cv.REDUCE_AVG)[0]/255
        vertical_bars = [i for i, p in enumerate(percentages) if p>0.2]

        #get the subsection just containing the system name and planet info, 
        #by cropping to the first orange vertical_bar found. if none is found, don't crop
        sys_name_subsection = top_subsection[:, :min(vertical_bars)] if vertical_bars else top_subsection
        

        #perform OCR reading on the subsection, sorting the results by their Y position
        results = reader.readtext(sys_name_subsection, width_ths=1) #type:ignore
        results.sort(key=lambda r:np.average(np.array(r[0])[:,1])) #sort by avg y

        #determine the system name by:
        #   1. Picking out the highest text region found (which is why we sorted)
        #   2. Choosing the closest match out of the Systems list
        print(results[0][1])
        name = pick_closest(results[0][1].split("[")[0].strip(), systems)[0]
        #END SECTION: Getting the system name

        #SECTION: Getting the system tier & capturable status
        #get the bottom subsection
        bottom_subsection = img[top_height+bar_height:]

        #perform OCR on it, sorting by the Y
        results = reader.readtext(bottom_subsection, width_ths=1) #type:ignore
        results.sort(key=lambda r:np.average(np.array(r[0])[:,1])) #sort by avg y

        #get the tier by a similar process to system name
        #splitting and joining to hopefully increase accuracy, by removing the first word: the Faction identifier (we dont need it)
        tier = pick_closest(" ".join(results[0][1].split()[1:]), [
            "New Claim",
            "Outpost",
            "Garrison",
            "Stronghold"
        ])[1]

        #pick out the line describing capturability
        capturable_line = results[1][1]

        #if the system says it's not capturable, exit early
        not_capturable = distance(capturable_line, "Cannot be captured") < 5 #account for slignt innaccuracies in the OCR
        if not_capturable: return None
        
        #if it is capturable/soon-to-be:
        capturable = None

        #if the system still has a timer:
        if not (distance(capturable_line, "Capturable") < 3):
            #replace any spaces surroudning colons with some regex
            capturable_line = re.sub(r" *: *", r":", capturable_line.replace(";", ":"))

            #match out the timestamp string, returning early if it couldn't be found
            match = re.search(r"(?:\d:)?\d{1,2}:\d{1,2}", capturable_line)
            if not match: 
                print(capturable_line)
                return None

            #get the match string, adding a "0:" to the start if it's in mm:ss to make further processing simpler
            time_str = match.group(0)
            if time_str.count(":") == 1:
                time_str = "0:"+time_str
            
            #extract out the seconds, minutes, and hours from the "h:mm:ss" format
            hours, mins, secs = map(int, time_str.split(":"))
            #add the timer time to the current timestamp
            capturable = (((hours * 60) + mins) * 60) + secs + round(time.time())

        #we're finally done, so return the result!
        #also return the cropped image, as a buffer, tod isplay to the user
        img_png_encoded = cv.imencode(".png", img)[1]
        img_buffer = io.BytesIO(img_png_encoded.tobytes())

        return Result(name, tier, capturable), img_buffer
    except Exception as e:
        print("Detector errored with this message:")
        print(e)
        return None

#all of this here exists for initializing the globals needed by sub-processes
reader = None
systems = None
def init_executor():
    from easyocr import Reader
    import json
    global reader, systems
    #initialize the ocr reader
    reader = Reader(["en"], gpu=True, verbose=False)

    #initialize the systems
    #ik we already do this in the main.py for the bot, but it seemed inneficient to pass the entire systems array into the subprocess
    systems = []
    with open("contested_systems.json", "r") as f:
        data = json.loads(f.read())
        systems.extend(data["Lycentian"])
        systems.extend(data["Foralkan"])

#create the executor, with 1 CPU core
executor = ProcessPoolExecutor(1)


initialized = False
async def initialize():
    """
    Runs the initialization inside the executor
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, init_executor)
    
    global initialized
    initialized = True

#the actual detection function, relatively simple compared to the rest of this lol
async def detect(url) -> Optional[tuple[Result, io.BytesIO]]:
    """
    Detects info from contested system info screens, at the provided web URL
    Returns None if the detection has failed
    """
    global initialized
    if not initialized:
        print("Detect was called without the detector being initialized!")
        return None

    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(executor, _detect, url)
    return res