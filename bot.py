# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import openai
import dotenv
import json

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount

dotenv.load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_ID")

# print(endpoint)

client = openai.AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version="2024-02-01",
)


class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        completion = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": turn_context.activity.text,
                },
            ],
            extra_body={
                "data_sources":[
                    {
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
                            "index_name": os.getenv("AZURE_AI_SEARCH_INDEX"),
                            "authentication": {
                                "type": "api_key",
                                "key": os.getenv("AZURE_AI_SEARCH_API_KEY"),
                            }
                        }
                    }
                ],
            }
        )
        await turn_context.send_activity(json.loads(completion.model_dump_json(indent=2))["choices"][0]["message"]["content"])

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")
