# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# General imports
import os
import openai
import dotenv
import json
import copy
import datetime

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

    source = ''
    index = 1
    for result in results:
        content = f'File {index}.\n'
        content += 'Content:\n'
        content += f'{result["content"]}\n\n'
        file = result["filepath"]
        search_score = result["@search.score"]
        updated_file = ''
        if file.startswith("EngMS_"):
            if file.find("Releases") != -1:
                updated_file = "https://eng.ms/docs/products/azure-linux/downloads"
            elif file.find("Overview") != -1:
                updated_file = "https://eng.ms/docs/products/azure-linux/overview/overview"
            elif file.find("Onboarding") != -1:
                updated_file = "https://eng.ms/docs/products/azure-linux/onboarding/onboardingoverview"
            elif file.find("ResourcesandHelp") != -1:
                updated_file = "https://eng.ms/docs/products/azure-linux/resourcesandhelp/resourcesandhelp"
            elif file.find("Features") != -1: 
                updated_file = "https://eng.ms/docs/products/azure-linux/features/supportandservicing"
            elif file.find("GettingStarted") != -1:
                updated_file = "https://eng.ms/docs/products/azure-linux/gettingstarted/aks/overview"
            else:
                updated_file = "https://eng.ms/docs/products/azure-linux/overview/overview"
        elif file.startswith("PMC_"):
            updated_file = 'https://packages.microsoft.com/'
        elif file.startswith("CVE"):
            updated_file = 'https://cvedashboard.azurewebsites.net/#/packages'
        else:   
            file = file.replace("__alqb__", "/")
            file = file[:-4]
            if file.startswith("github_"):
                file = file[7:]
                updated_file = file
            elif file.startswith("mslearn_"):
                file = file[8:]
                updated_file = file
            elif file.startswith("GH_releases_"):
                file = file[12:]
                updated_file = file
        content += 'Citation:\n'
        content += f'{updated_file}\n'
        content += f"Search Score: {search_score}\n"
        content += f'Time Stamp: {datetime.datetime.now()}\n\n\n'
        index += 1

        source += content
    return source

messages_master = []
search_results_master = []
timestamps_master = []

def invoke_llm(query, source):

    messages = copy.deepcopy(messages_master)
    message_system = {
        "role": "system",
        "content": f'''You are an AI assistant specializing in Azure Linux. Use the following search results from the Azure Search index to answer the user's question accurately and comprehensively. 
            Please ensure to:

            1. Extract and use relevant information from the provided search results to form your answer, giving more priority to the latest search results.
            2. Only provide citation links at the end of your response under the heading "Citations" if they are HTTPS links.
            3. Do not include any citations within the main body of your answer unless absolutely necessary.
            4. If multiple sources are used, ensure each citation is clearly numbered and corresponds to the referenced information in your answer.
            5. Answer concisely and ensure the information is relevant to the user's query.

            Here are the search results to use: {source}
            Note: The chat context includes the last hour's chat history and search results history, which are timestamped for reference.
        '''
    }
    
    message_user = {
        'role': 'user',
        'content': query
    }
    messages.append(message_system)
    messages.append(message_user)
    output = model.invoke(messages)
    message_assistant = {
        "role": "assistant",
        "content": output.content
    }

    timestamps_master.append(datetime.datetime.now())
    messages_master.append(message_user)
    messages_master.append(message_assistant)
    search_results_master.append(source)

    return output.content

def generate_response(query):
    del_idx = 0
    curr_timestamp = datetime.datetime.now()
    for ts in timestamps_master:
        time_diff = curr_timestamp - ts
        if time_diff.total_seconds() > 216000:
            del_idx += 1
        else:
            break
    
    if del_idx > 0:
        del messages_master[:2*del_idx]
        del search_results_master[:del_idx]
        del timestamps_master[:del_idx]

    contents = invoke_azure_ai_search(query, 10)
    output = invoke_llm(query, contents)
    return output


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
