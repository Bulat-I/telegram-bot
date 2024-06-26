# v_PDF (translated as to_PDF)

Features
========
**v_PDF** is a Telegram bot for managing your PDF documents: 
* Convert multiple file types to PDF (images, MS Office and LibreOffice documents and others)
* Compress PDF files to reduce their size
* Rotate PDFs (left 90°, right 90°, flip)
* Merge two PDF files into one file

Files can be loaded before selecting a command or pre-selecting an operation using on-screen instructions.

The bot is available in English and Russian. Languages ​​can be changed using the Menu button in the lower left corner.

Under the hood
========
**v_PDF** is written on Python and utilizes the following: 
* Aiogram 3 library as a base
* Aiogram_i18n library for processing localizations
* GNU GetText library as a localization core
* PyPDF library for functions for rotating, merging and compressing PDF files
* LibreOffice converter with a simple REST API for converting files to PDF format

Limitations
========
* The bot can only process Telegram documents (files). This means that any input documents, including images, must be uploaded as files.
* Documents' size is limited to 20MB. This limitation comes from Telegram.

Usage
========
Docker run command: docker run -d --name v-pdf -v /var/lib/telegram-bot/:/var/lib/telegram-bot/ telegram-bot
