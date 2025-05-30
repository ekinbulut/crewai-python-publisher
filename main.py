from crewai import Agent, Task, Crew, LLM
from tools.news_fetcher_tool import RSSNewsFetcherTool
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger
from check_ollama import check_ollama
from custom_ollama import CustomOllamaLLM
import os
import sys
import time
from dotenv import load_dotenv
import gc

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
        role="Blog Publisher",
        goal="Publish pre-formatted blog posts to WordPress while maintaining data structure integrity",
        backstory="""A technical publisher who specializes in WordPress REST API integration. 
        Experienced in handling structured data and ensuring it's properly transmitted to WordPress 
        without modifying the original format.""",
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
        agent=fetcher,
        context=[]  # Explicitly set empty context
    )
    
    # Validate fetch task result before proceeding
    if not fetch_task.context:
        fetch_task.context = []  # Ensure context is never None

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
    
    # Validate summarize task context
    if not summarize_task.context:
        logger.warning("Summarize task missing context from fetch task")
        summarize_task.context = [fetch_task]

    # Third task - write blog post (depends on summarize_task)
    write_task = Task(
        description="""Create an engaging blog post that synthesizes the summarized news items.
        Format your output as a dictionary that MUST contain these exact fields:
        {
            "title": "{{Your SEO-friendly title as a plain string}}",
            "content": "{{Your full blog post content with proper formatting}}",
            "tags": ["technology", "ai", "space", "tech-news", "innovation"],  # Example tags - customize based on content
            "categories": [5]  # Technology category ID
        }
        
        In the blog post content, include:
        - A compelling introduction
        - Organized content by themes
        - Technological implications
        - Industry analysis
        - Future predictions
        
        Important: 
        1. The title must be a plain string, not a JSON object or dictionary
        2. All four dictionary fields (title, content, tags, categories) must be present
        3. The tags list should be relevant to your content
        4. The categories list must contain [5] for the technology category""",
        expected_output="A dictionary containing the blog post title, content, tags, and categories",
        agent=writer,
        context=[summarize_task]  # Pass the summarize task as context
    )

    # Fourth task - post to WordPress (depends on write_task)
    post_task = Task(
        description="""EXACTLY follow these steps to post to WordPress:

        1. Get the dictionary from the previous task (write_task) output
        2. Execute this EXACT code (copy it exactly):
           ```python
           link = wordpress_poster_tool.run(write_task.output.raw)
           return link['link']
           ```
        3. Return ONLY the URL from the response

        The input dictionary MUST have these fields:
        - title (string)
        - content (string)
        - tags (list)
        - categories (list)

        DO NOT:
        - Modify the dictionary structure
        - Add any extra text or formatting
        - Return anything except the URL

        Example good output:
        https://example.com/?p=123

        Example bad output:
        "Here's the link: https://example.com/?p=123"
        {"url": "https://example.com/?p=123"}""",
        expected_output="The WordPress post URL (example: https://example.com/?p=123)",
        agent=poster,
        context=[write_task]  # Pass the write task as context
    )
    
    return [fetch_task, summarize_task, write_task, post_task]

def run_with_retry(crew, max_retries=3):
    """Run the crew workflow with retry logic"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting workflow attempt {attempt + 1}/{max_retries}")
            result = crew.kickoff()
            logger.info("Workflow completed successfully")
            return result
        except Exception as e:
            last_error = e
            logger.error(f"Error in workflow attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            logger.error(f"Workflow failed after {max_retries} attempts")
            raise RuntimeError(f"Workflow failed: {str(last_error)}")

def clear_agent_memory(agent):
    """Clear an agent's memory to prevent memory leaks"""
    if hasattr(agent, 'memory'):
        agent.memory.clear()
    if hasattr(agent, 'conversation_memory'):
        agent.conversation_memory.clear()

def cleanup_resources(agents):
    """Cleanup resources after workflow completion"""
    logger.info("Cleaning up resources...")
    for agent in agents:
        clear_agent_memory(agent)
    gc.collect()

def main():
    start_time = time.time()
    logger.info("Starting CrewAI Blog Generation System")
    agents = []
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Verify environment variables
        verify_environment()
        
        # Check Ollama availability with retries
        if not check_ollama(max_retries=3, retry_delay=5):
            logger.error("Ollama service is not available after retries")
            sys.exit(1)
        
        # Initialize LLM with more conservative settings
        logger.info("Initializing Ollama LLM...")
        llm = LLM(
            model="ollama/mistral:7b",
            base_url="http://localhost:11434",
            temperature=0.2,
            timeout=300,
            request_timeout=300
        )
        
        # Create agents and tasks
        agents = create_agents(llm)
        fetcher, summarizer, writer, poster = agents
        tasks = create_tasks(fetcher, summarizer, writer, poster)
        
        # Create crew with sequential processing
        crew = Crew(
            agents=[fetcher, summarizer, writer, poster],
            tasks=tasks,
            verbose=True,
            process="sequential"
        )
        
        # Execute the workflow with retry logic
        logger.info("Starting the blog creation workflow...")
        result = run_with_retry(crew, max_retries=3)
        
        # Process completed successfully
        execution_time = time.time() - start_time
        logger.info(f"Process completed successfully in {execution_time:.2f} seconds")
        logger.info(f"Final result: {result}")
        
        # Cleanup
        cleanup_resources(agents)
        return result
        
    except Exception as e:
        logger.error(f"Critical error in main process: {str(e)}")
        if agents:
            cleanup_resources(agents)
        sys.exit(1)

if __name__ == "__main__":
    main()
