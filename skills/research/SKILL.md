---
name: research
description: Conduct comprehensive research on topics using web search, content analysis, and information synthesis. Use when user requests research, investigation, fact-finding, market analysis, competitive analysis, or information gathering.
requiredMcpServers:
  - playwright
preferredTools:
  - playwright.goto
  - playwright.fill
  - playwright.click
  - playwright.get_content
  - playwright.screenshot
scriptExecution: true
resources:
  - research-plan-template.md
  - search-strategies.md
---

# Research Skill

This skill provides comprehensive research capabilities including:

- Research planning and strategy development
- Web search and content analysis
- Information synthesis and summarization
- Competitive analysis and market research
- Fact verification and source validation
- Multi-source information gathering

## Capabilities

### 1. MCP-Based Web Automation
- Uses Playwright for advanced web interactions
- Can navigate complex sites requiring JavaScript
- Handles forms, authentication, and dynamic content
- Takes screenshots for visual verification
- Extracts structured data from web pages

### 2. Script-Based Research
- Executes Python scripts for web scraping
- Performs API-based searches when available
- Processes and analyzes large datasets
- Generates reports and visualizations
- Handles bulk data collection tasks

## Research Workflow

### Phase 1: Planning
1. **Analyze the research request** - Understand scope, objectives, and constraints
2. **Create research plan** - Define search strategies, sources, and methodology
3. **Identify information gaps** - Determine what specific information is needed
4. **Select appropriate tools** - Choose between MCP automation and script execution

### Phase 2: Information Gathering
1. **Execute search strategy** - Use multiple search approaches and sources
2. **Navigate target websites** - Use Playwright for complex site interactions
3. **Extract relevant content** - Gather information from identified sources
4. **Validate information** - Cross-reference findings across multiple sources

### Phase 3: Analysis & Synthesis
1. **Process collected data** - Organize and structure the information
2. **Identify patterns and insights** - Analyze findings for key themes
3. **Synthesize findings** - Create comprehensive summary of research
4. **Generate final report** - Present findings in requested format

## Available Research Tools

### Web Search Tools
- Google Search (via script execution)
- Bing Search (via script execution)
- Specialized search engines (academic, news, etc.)
- Direct site navigation (via Playwright)

### Content Analysis Tools
- Text extraction and processing
- Content summarization
- Sentiment analysis
- Link analysis and validation
- Image and document analysis

### Data Collection Tools
- Web scraping with beautifulsoup
- API integration for data sources
- CSV/JSON data processing
- Database query capabilities
- File download and processing

## Research Types

### Market Research
- Competitor analysis
- Industry trends and reports
- Market sizing and opportunity assessment
- Pricing analysis
- Customer sentiment analysis

### Technical Research
- Technology comparisons
- Best practices investigation
- Documentation and specification research
- Code and implementation examples
- Technical trend analysis

### Academic Research
- Literature reviews
- Citation analysis
- Research methodology investigation
- Data collection and analysis
- Peer-reviewed source validation

### News and Current Events
- Breaking news monitoring
- Trend analysis
- Social media sentiment
- Event timeline construction
- Source credibility assessment

## Output Formats

### Research Reports
- Executive summary with key findings
- Detailed methodology and sources
- Supporting evidence and citations
- Recommendations and next steps
- Appendices with raw data

### Comparative Analysis
- Side-by-side comparisons
- Strengths and weaknesses analysis
- Decision matrices and scoring
- Visual charts and graphs
- Summary recommendations

### Data Synthesis
- Aggregated findings from multiple sources
- Cross-referenced validation
- Trend identification and analysis
- Gap analysis and recommendations
- Action items and follow-ups

## Usage Examples

- "Research the current state of AI in healthcare and provide a comprehensive report"
- "Analyze the competitive landscape for project management software"
- "Find the latest best practices for cloud security"
- "Investigate the market potential for sustainable packaging solutions"
- "Research and compare different approaches to microservices architecture"
- "Gather information about recent developments in quantum computing"

## Quality Guidelines

1. **Source Diversity** - Use multiple, credible sources for validation
2. **Fact Verification** - Cross-reference claims across sources
3. **Bias Awareness** - Consider potential bias in sources and methodology
4. **Timeliness** - Prioritize recent and up-to-date information
5. **Depth vs Breadth** - Balance comprehensive coverage with focused analysis
6. **Citation Standards** - Properly attribute all sources and claims
7. **Actionability** - Provide clear, actionable insights and recommendations