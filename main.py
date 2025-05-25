from crewai import Agent, Task, Crew
from tools.news_fetcher_tool import RSSNewsFetcherTool
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger
from check_ollama import check_ollama
from custom_ollama import CustomOllamaLLM
import os
import sys
import time
from dotenv import load_dotenv

logger = setup_logger()

def verify_environment():
    """Verify environment variables are set"""
    required_vars = ['WORDPRESS_URL', 'WORDPRESS_USER', 'WORDPRESS_PASS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        sys.exit(1)

def create_agents(llm):
    """Create and return all agents with their tools"""
    logger.info("Initializing tools...")
    news_tool = RSSNewsFetcherTool()
    wordpress_tool = WordPressPosterTool()
    
    logger.info("Creating agents...")
    fetcher = Agent(
        role="News Researcher",
        goal="Find the most recent and relevant IT news from trusted sources",
        backstory="An expert researcher in the field of software and hardware innovation.",
        tools=[news_tool],
        verbose=True,
        llm=llm
    )

    summarizer = Agent(
        role="Article Summarizer",
        goal="Summarize fetched news into digestible highlights",
        backstory="A skilled writer who transforms raw information into sharp summaries.",
        verbose=True,
        llm=llm
    )

    writer = Agent(
        role="Blog Writer",
        goal="Write a full blog post from summarized news",
        backstory="A tech blogger who crafts engaging and informative blog articles.",
        verbose=True,
        llm=llm
    )

    poster = Agent(
        role="Blog Poster",
        goal="Publish the post to WordPress using REST API",
        backstory="Handles blog publishing duties with attention to SEO and proper formatting.",
        tools=[wordpress_tool],
        verbose=True,
        llm=llm
    )
    
    return fetcher, summarizer, writer, poster

def create_tasks(fetcher, summarizer, writer, poster):
    """Create and return all tasks with dependencies"""
    logger.info("Creating tasks with dependencies...")
    
    # First task - fetch news
    fetch_task = Task(
        description="""Use the rss_news_fetcher tool to gather and present top IT news from today.
        Focus on:
        - Major tech announcements
        - Software industry updates
        - AI and ML developments
        - Cybersecurity news""",
        expected_output="A list of current tech news articles with titles and summaries",
        agent=fetcher
    )

    # Second task - summarize news (depends on fetch_task)
    summarize_task = Task(
        description="""Create bullet-point summaries for each news article. Focus on:
        - Key technological advancements
        - Industry impacts
        - Main announcements
        - Critical insights""",
        expected_output="A well-organized list of bullet-point summaries for each news article",
        agent=summarizer,
        context=[fetch_task]  # Pass the fetch task as context
    )

    # Third task - write blog post (depends on summarize_task)
    write_task = Task(
        description="""Create an engaging blog post that synthesizes the summarized news items.
        Include:
        - A compelling introduction
        - Organized content by themes
        - Technological implications
        - Industry analysis
        - Future predictions""",
        expected_output="A complete blog post ready for publishing",
        agent=writer,
        context=[summarize_task]  # Pass the summarize task as context
    )

    # Fourth task - post to WordPress (depends on write_task)
    post_task = Task(
        description="""Publish the blog post to WordPress:
        - Create SEO-friendly title
        - Add proper formatting
        - Include relevant tags and categories
        - Set featured image if available
        - Verify successful publication""",
        expected_output="The URL of the published blog post",
        agent=poster,
        context=[write_task]  # Pass the write task as context
    )
    
    return [fetch_task, summarize_task, write_task, post_task]

def main():
    start_time = time.time()
    logger.info("Starting CrewAI Blog Generation System")
    
    # Load environment variables
    load_dotenv()
    
    # Verify environment variables
    verify_environment()
    
    # Check Ollama availability
    if not check_ollama():
        logger.error("Ollama service is not available")
        sys.exit(1)
    
    try:
        # Initialize LLM
        logger.info("Initializing Ollama LLM...")
        llm = CustomOllamaLLM(
            model="ollama/mistral:7b",
            base_url="http://localhost:11434",
            temperature=0.7,
            verbose=True
        )
        
        # Create agents and tasks
        fetcher, summarizer, writer, poster = create_agents(llm)
        tasks = create_tasks(fetcher, summarizer, writer, poster)
        
        # Create and run the crew
        crew = Crew(
            agents=[fetcher, summarizer, writer, poster],
            tasks=tasks,
            verbose=True
        )
        
        # Execute the workflow
        logger.info("Starting the blog creation workflow...")
        result = crew.kickoff()
        
        # Process completed successfully
        execution_time = time.time() - start_time
        logger.info(f"Process completed successfully in {execution_time:.2f} seconds")
        logger.info(f"Final result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
