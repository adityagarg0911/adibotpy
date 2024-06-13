#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import dotenv

dotenv.load_dotenv()

class DefaultConfig:
    """ Bot Configuration """

    PORT = 8000
    APP_ID = os.getenv("MicrosoftAppId")
    APP_PASSWORD = os.getenv("MicrosoftAppPassword")
