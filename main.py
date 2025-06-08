from crewai import Agent, Task, Crew, LLM
from tools.news_fetcher_tool import RSSNewsFetcherTool
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger
from check_ollama import check_ollama
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
    wordpress_poster = WordPressPosterTool()
    
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
        tools=[wordpress_poster],
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
        - Cybersecurity news
        
        Format your output as a clear list of news items with titles and summaries.
        Ensure your output is properly formatted and complete before finishing.""",
        expected_output="A list of current tech news articles with titles and summaries",
        agent=fetcher,
        context=[],  # Empty context for first task
        output_format="The output should be well-structured text with news items"
    )

    # Second task - summarize news (depends on fetch_task)
    summarize_task = Task(
        description="""Take the news articles from the previous task and create bullet-point summaries.

        Previous task output format:
        A list of news items with Title, Link, and Summary sections.

        Your task:
        Create bullet-point summaries for each news article focusing on:
        - Key technological advancements
        - Industry impacts
        - Main announcements
        - Critical insights
        
        Format each summary as clear bullet points for easy reading.""",
        expected_output="A well-organized list of bullet-point summaries for each news article",
        agent=summarizer,
        context=[fetch_task]  # Pass the fetch task as context
    )

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
        description="""MANDATORY: You MUST call the 'wordpress_poster' tool. No exceptions.

        Step 1: Extract the Python dictionary from the previous task output (remove any code block markers)
        Step 2: Call the wordpress_poster tool with the individual parameters from the dictionary
        Step 3: Return the actual URL that the tool provides

        REQUIRED TOOL CALL FORMAT:
        wordpress_poster(title="...", content="...", tags=[...], categories=[...])

        Extract the title, content, tags, and categories from the dictionary and pass them as separate parameters.
        You cannot complete this task without actually calling the wordpress_poster tool.
        Do NOT provide placeholder text or descriptions - execute the tool call.""",
        expected_output="The actual WordPress URL returned by calling the wordpress_poster tool",
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
        
        # Initialize LLM with llama3.2 (more stable for sequential tasks)
        logger.info("Initializing Ollama LLM with llama3.2...")
        llm = LLM(
            model="ollama/mistral:7b",
            base_url="http://localhost:11434",
            temperature=0.1,  # Lower temperature for more focused outputs
            timeout=300,
            request_timeout=300,
            context_window=4096  # Standard context window
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
