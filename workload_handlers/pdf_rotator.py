import os
import subprocess

from pypdf import PdfReader, PdfWriter


async def rotatePDF(input_item, output_path, rotateAngle):
    reader = PdfReader(input_item)

    input_filename = os.path.basename(input_item)
    output_item = os.path.join(output_path, input_filename)

    with open(output_item, "wb") as file:
        writer = PdfWriter(file)

        for page in reader.pages:
            page.rotate(rotateAngle)
            writer.add_page(page)

        writer.write(file)

    return output_item
