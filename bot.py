# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# General imports
import os
import openai
import dotenv
import json

# Imports needed for Azure AI Search
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Imports needed for AzureChatOpenAI from Langchain
from langchain_openai import AzureChatOpenAI

# Imports needed for creating a bot
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount

dotenv.load_dotenv()

# endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
# api_key = os.getenv("AZURE_OPENAI_API_KEY")
# deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_ID")

# # print(endpoint)

# client = openai.AzureOpenAI(
#     azure_endpoint=endpoint,
#     api_key=api_key,
#     api_version="2024-02-01",
# )


search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
search_api_key = os.getenv("AZURE_AI_SEARCH_API_KEY")
index_name = os.getenv("AZURE_AI_SEARCH_INDEX")
search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_api_key))

model = AzureChatOpenAI(
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_ID"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)


def invoke_azure_ai_search(query, top_n_searches):
    results = search_client.search(search_text=query, top=top_n_searches)
    results = results
    file_paths = [result["filepath"] for result in results]

    updated_file_paths = []
    for file in file_paths:
        file = file.replace("__alqb__", "/")
        file = file[:-4]

        if file.startswith("github_"):
            file = file[7:]
            updated_file_paths.append(file)
        elif file.startswith("mslearn_"):
            file = file[8:]
            updated_file_paths.append(file)
        elif file.startswith("GH_releases_"):
            file = file[12:]
            updated_file_paths.append(file)

    citations = set(updated_file_paths)
    
    contents = '\n\n\n'.join([result['content'] for result in results])
    return contents, citations

def invoke_llm(query, source):
    messages = []
    messages.append(
        {
            'role': 'system',
            'content': f'''
            'Answer the next query based on following 2 sources of information:
            Source: {source}
            '''
        }
    )
    messages.append({
        'role': 'user',
        'content': query
    })
    output = model.invoke(messages)
    return output.content

def generate_response(query):
    contents, citations = invoke_azure_ai_search(query, 5)
    output = invoke_llm(query, contents)

    response = output
    if citations.__len__() > 0:
        response += '\n\nCitations:\n'
        for citation in citations:
            response += citation + '\n'
    return response


class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        query = turn_context.activity.text
        # completion = client.chat.completions.create(
        #     model=deployment,
        #     messages=[
        #         {
        #             "role": "user",
        #             "content": turn_context.activity.text,
        #         },
        #     ],
        #     extra_body={
        #         "data_sources":[
        #             {
        #                 "type": "azure_search",
        #                 "parameters": {
        #                     "endpoint": os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
        #                     "index_name": os.getenv("AZURE_AI_SEARCH_INDEX"),
        #                     "authentication": {
        #                         "type": "api_key",
        #                         "key": os.getenv("AZURE_AI_SEARCH_API_KEY"),
        #                     }
        #                 }
        #             }
        #         ],
        #     }
        # )
        # response = json.loads(completion.model_dump_json(indent=2))["choices"][0]["message"]["content"]

        response = generate_response(query)
        await turn_context.send_activity(response)

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")
