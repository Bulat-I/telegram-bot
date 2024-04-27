import os
import pycurl
from io import BytesIO
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

CONVERTER_URL = os.getenv("CONVERTER_URL")

async def convertToPDF(input_item, output_path) -> int:
    input_filename = os.path.basename(input_item)

    response_buffer = BytesIO()

    c = pycurl.Curl()
    c.setopt(c.URL, CONVERTER_URL)
    c.setopt(c.WRITEDATA, response_buffer)
    c.setopt(c.HTTPPOST, [('filename', input_filename)])
    c.perform()
    http_status_code = c.getinfo(pycurl.HTTP_CODE)
    c.close()

    if http_status_code == 200:
        return 0
    else:
        return -1


#The below code was in use in all-in-one setup when the bot was running in the same container with LibreOffice instance
#The new approach uses a dedicated container running LibreOffice intance with REST API. The bot communicates to it over HTTP.
""" 
import os
import subprocess


async def convertToPDF(input_item, output_path) -> int:
    input_filename = os.path.basename(input_item)

    exitCode = subprocess.call(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_path,
            input_item,
        ]
    )

    return exitCode
 """