import os
import subprocess

from pypdf import PdfMerger


async def mergeTwoPDF(input_item1, input_item2, output_path):
    merger = PdfMerger()

    input_filename = os.path.basename(input_item1)
    output_item = os.path.join(output_path, input_filename)

    merger.append(input_item1)
    merger.append(input_item2)

    merger.write(output_item)

    return output_item
