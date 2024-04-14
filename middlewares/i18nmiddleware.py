import os
from aiogram_i18n.managers import BaseManager
from aiogram.types.user import User
import logging

logger = logging.getLogger(__name__)

userLang: dict[int, str] = {}

class UserManager(BaseManager):
    async def get_locale(self, event_from_user: User) -> str:
        default = self.default_locale
        if event_from_user.id is not None:
            if event_from_user.id in userLang:
                logger.debug("There is a saved user locale " + str(userLang[event_from_user.id]) + " for the user " + str(event_from_user.id))
                return userLang[event_from_user.id]
            logger.debug("There is no saved user locale for the user " + str(event_from_user.id))
        return default


    async def set_locale(self, locale: str, event_from_user: User) -> None:
        userID = event_from_user.id 
        userLang[userID] = locale
        logger.debug("Added new locale " + locale + " for the user" + str(userID))
        return

