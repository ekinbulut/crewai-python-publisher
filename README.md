# CrewAI Blog Generation System

An automated blog content generation and publishing system using CrewAI, RSS feeds, and WordPress integration.

## Overview

This project implements an automated blog content pipeline that:
1. Fetches latest tech news from RSS feeds
2. Analyzes and summarizes the content
3. Generates well-structured blog posts
4. Publishes content directly to WordPress

## Features

- 🤖 Automated content generation using CrewAI agents
- 📰 RSS feed integration for real-time news fetching
- ✍️ AI-powered content writing and summarization
- 🌐 WordPress integration via REST API
- 📊 Logging and performance monitoring

## Prerequisites

- Python 3.12+
- Ollama running locally
- WordPress site with REST API access
- Environment variables configured

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd crewai
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your WordPress credentials
```

## Configuration

Create a `.env` file with the following variables:
```
WORDPRESS_URL=your-wordpress-site/wp-json/wp/v2/posts
WORDPRESS_USER=your-username
WORDPRESS_PASS=your-password
```

## Usage

Run the main script:
```bash
python main.py
```

Run tests:
```bash
python -m pytest
```

## Project Structure

- `main.py` - Main application script
- `custom_ollama.py` - Ollama LLM integration
- `tools/` - CrewAI tools implementation
  - `news_fetcher_tool.py` - RSS feed integration
  - `wordpress_poster_tool.py` - WordPress API integration
- `tests/` - Test files

## Testing

The project includes comprehensive tests:
- Unit tests for individual components
- Integration tests for the complete workflow
- Mock tests for WordPress integration

Run tests with:
```bash
python -m pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
