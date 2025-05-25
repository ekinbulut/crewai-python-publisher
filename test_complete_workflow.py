import unittest
from unittest.mock import patch, MagicMock
from tools.news_fetcher_tool import RSSNewsFetcherTool
from tools.wordpress_poster_tool import WordPressPosterTool
from crewai import Agent, Task, Crew, Process
from custom_ollama import CustomOllamaLLM
from dotenv import load_dotenv
import os

class TestCompleteBlogWorkflow(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        self.ollama = CustomOllamaLLM(model="ollama/mistral:7b", base_url="http://localhost:11434")
        
        # Create agents
        self.researcher = Agent(
            role='Tech News Researcher',
            goal='Find and analyze the latest tech news',
            backstory='Expert at finding and analyzing technology news',
            tools=[RSSNewsFetcherTool()],
            llm=self.ollama
        )
        
        self.writer = Agent(
            role='Tech Blog Writer',
            goal='Create engaging blog posts from tech news',
            backstory='''Experienced tech writer who creates compelling blog posts.
            Always puts the title on the first line followed by the content on subsequent lines.
            Makes sure content is well-formatted and easy to read.''',
            llm=self.ollama,
            verbose=True
        )
        
        self.publisher = Agent(
            role='Content Publisher',
            goal='Publish blog posts to WordPress',
            backstory='''Expert at publishing content to WordPress through the REST API.
            Takes blog posts with a title and content and publishes them using the wordpress_poster tool.
            The tool expects input in the format: "Title\\nContent" (title on first line, content after).''',
            tools=[WordPressPosterTool()],
            llm=self.ollama,
            verbose=True
        )

    @patch('tools.wordpress_poster_tool.requests.post')
    def test_complete_workflow(self, mock_wp_post):
        # Mock WordPress environment variables
        os.environ["WORDPRESS_URL"] = "https://example.com/wp-json/wp/v2/posts"
        os.environ["WORDPRESS_USER"] = "testuser"
        os.environ["WORDPRESS_PASS"] = "testpass"
        
        # Mock WordPress API response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 123,
            "link": "https://example.com/test-post",
            "status": "publish"
        }
        mock_wp_post.return_value = mock_response

        # Create tasks
        research_task = Task(
            description='Find the latest tech news from our RSS feeds using the rss_news_fetcher tool',
            expected_output='A list of recent tech news articles with titles, links, and summaries',
            agent=self.researcher
        )

        writing_task = Task(
            description='''Using the research from the previous task, create a blog post that:
            1. Has a clear, engaging title on the first line
            2. Contains well-organized content starting from the second line
            3. Incorporates key information from the news articles
            4. Uses proper formatting and structure''',
            expected_output='A complete blog post with title on first line and content below',
            agent=self.writer,
            context=[research_task]
        )

        publishing_task = Task(
            description='''Take the blog post from the previous task and publish it to WordPress.
            The input should be formatted exactly as:
            - First line: The post title
            - Remaining lines: The post content
            
            For example:
            Why AI is Changing Everything
            Artificial Intelligence has become...
            
            The title and content must come directly from the previous task's output.
            Do not add any formatting, JSON, or extra content - just copy the title and content exactly as they are.''',
            expected_output='WordPress post URL',
            agent=self.publisher,
            context=[writing_task]
        )

        # Create and run the crew
        crew = Crew(
            agents=[self.researcher, self.writer, self.publisher],
            tasks=[research_task, writing_task, publishing_task],
            process=Process.sequential  # Ensure tasks run in sequence
        )

        with patch.dict('os.environ', {
            'WORDPRESS_URL': 'https://example.com/wp-json/wp/v2/posts',
            'WORDPRESS_USER': 'testuser',
            'WORDPRESS_PASS': 'testpass'
        }):
            result = crew.kickoff()
            
            # Print intermediate results for debugging
            print(f"\nResearch task output: {research_task.output.raw}\n")
            print(f"\nWriting task output: {writing_task.output.raw}\n")
            print(f"\nPublishing task output: {publishing_task.output.raw}\n")
            
            # Verify results
            self.assertIsNotNone(result)
            self.assertIsNotNone(research_task.output.raw, "Research task produced no output")
            self.assertIn("Title:", research_task.output.raw, "Research task output missing news titles")
            
            # Verify writing task produced valid blog post
            self.assertIsNotNone(writing_task.output.raw, "Writing task produced no output")
            self.assertTrue(len(writing_task.output.raw) > 100, "Blog post content too short")
            
            # Verify WordPress posting was attempted
            mock_wp_post.assert_called_once()
            call_kwargs = mock_wp_post.call_args.kwargs
            self.assertEqual(call_kwargs['auth'].username, 'testuser')
            self.assertEqual(call_kwargs['auth'].password, 'testpass')
            
            # Verify the post data
            self.assertIn('json', call_kwargs)
            post_data = call_kwargs['json']
            self.assertIn('title', post_data)
            self.assertIn('content', post_data)
            self.assertGreater(len(post_data['content']), 100)
            
            # We expect the WordPress poster to be called
            mock_wp_post.assert_called_once()
            # Verify WordPress API was called with correct credentials
            auth = mock_wp_post.call_args.kwargs.get('auth')
            self.assertEqual(auth.username, 'testuser')
            self.assertEqual(auth.password, 'testpass')

if __name__ == '__main__':
    unittest.main()
