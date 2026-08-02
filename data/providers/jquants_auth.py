from jquantsapi import ClientV2

from config.settings import (
    JQUANTS_MAIL,
    JQUANTS_PASSWORD
)


class JQuantsAuth:

    def __init__(self):

        self.client = ClientV2(
            mail_address=JQUANTS_MAIL,
            password=JQUANTS_PASSWORD
        )

    def login(self):

        try:

            self.client.get_id_token()

            return True

        except Exception as e:

            print(e)

            return False

    def get_client(self):

        return self.client