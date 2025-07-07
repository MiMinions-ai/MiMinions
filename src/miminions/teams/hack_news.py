from typing import List
from dotenv import load_dotenv
import argparse

load_dotenv()

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.file import FileTools
from pydantic import BaseModel


class Article(BaseModel):
    title: str
    summary: str
    reference_links: List[str]


hn_researcher = Agent(
    name="HackerNews Researcher",
    model=OpenAIChat("gpt-4o"),
    role="Gets top stories from hackernews.",
    tools=[HackerNewsTools()],
)

web_searcher = Agent(
    name="Web Searcher",
    model=OpenAIChat("gpt-4o"),
    role="Searches the web for information on a topic",
    tools=[DuckDuckGoTools()],
    add_datetime_to_instructions=True,
)

article_reader = Agent(
    name="Article Reader",
    role="Reads articles from URLs.",
    tools=[Newspaper4kTools()],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='HackerNews Team CLI')
    parser.add_argument('--show-tool-calls', action='store_true', help='Show tool calls in output')
    parser.add_argument('--no-markdown', action='store_true', help='Disable markdown formatting')
    parser.add_argument('--debug-mode', action='store_true', help='Enable debug mode')
    parser.add_argument('--show-members-responses', action='store_true', help='Show responses from team members')
    parser.add_argument('--save-to-file', action='store_true', help='Save the output to a file')
    parser.add_argument('query', nargs='?', default="Write an article about the top 2 stories on hackernews",
                      help='Query to process (default: " Write an article about the top 2 stories on hackernews")')
    
    args = parser.parse_args()
    
    # Update team settings based on CLI arguments
    hn_team = Team(
        name="HackerNews Team",
        mode="coordinate",
        model=OpenAIChat("gpt-4o"),
        members=[hn_researcher, web_searcher, article_reader],
        instructions=[
            "First, search hackernews for what the user is asking about.",
            "Then, ask the article reader to read the links for the stories to get more information.",
            "Important: you must provide the article reader with the links to read.",
            "Then, ask the web searcher to search for each story to get more information.",
            "After that, provide a thoughtful and engaging summary.",
            "Finally, save it to a file in .outputs and name it with the current date, time, hackernews_team with .md extension."
        ],
        tools=[FileTools()] if args.save_to_file else [],
        response_model=Article,
        show_tool_calls=args.show_tool_calls if args.show_tool_calls else False,
        markdown=False if args.no_markdown else True,
        debug_mode=args.debug_mode if args.debug_mode else False,
        show_members_responses=args.show_members_responses if args.show_members_responses else False,
    )
    hn_team.print_response(args.query)