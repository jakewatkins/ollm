# Research Skill

A comprehensive research capability for ollm that combines MCP-based web automation with script-based data collection and analysis.

## Features

- **Intelligent Research Planning**: Automatically creates structured research plans based on user requests
- **Multi-Source Data Collection**: Uses both Playwright MCP for complex web interactions and Python scripts for bulk data processing
- **Content Analysis**: Extracts, processes, and synthesizes information from multiple sources
- **Quality Assurance**: Cross-references findings and validates sources for credibility
- **Flexible Output**: Generates reports in various formats based on research objectives

## How It Works

### 1. Automatic Skill Detection
The skill is automatically triggered when users request:
- "Research [topic]"
- "Investigate [subject]"
- "Find information about [topic]"
- "Analyze the market for [product/service]"
- "What are the latest trends in [field]?"

### 2. Research Process
1. **Planning Phase**: Creates a structured research plan using the built-in template
2. **Data Collection**: Uses appropriate tools based on the research requirements:
   - **Playwright MCP**: For complex websites requiring JavaScript interaction
   - **Script Execution**: For bulk data collection, API integration, and analysis
3. **Analysis Phase**: Processes collected information and identifies key insights
4. **Synthesis Phase**: Generates comprehensive reports with findings and recommendations

### 3. Available Tools

#### MCP Tools (Playwright)
- Navigate complex websites
- Handle forms and authentication
- Extract content from dynamic pages
- Take screenshots for verification
- Manage sessions and cookies

#### Script Execution
- Web search via multiple engines
- API integration for data sources
- Content extraction and processing
- Data analysis and visualization
- Bulk data collection and storage

## Usage Examples

### Basic Research Request
```
ollm -p "Research the current trends in sustainable packaging for e-commerce"
```

### Competitive Analysis
```
ollm -p "Analyze the competitive landscape for project management software, focusing on features and pricing"
```

### Technical Investigation
```
ollm -p "Investigate best practices for implementing microservices architecture in cloud environments"
```

### Market Research
```
ollm -p "Research the market potential for AI-powered customer service solutions in retail"
```

## Output Formats

The research skill can generate various types of outputs:

### Executive Summary
- Key findings overview
- Main insights and trends
- Recommendations
- Next steps

### Detailed Research Report
- Comprehensive methodology
- Source analysis and validation
- Detailed findings with evidence
- Supporting data and charts
- Complete bibliography

### Competitive Analysis
- Company/product comparisons
- Feature matrices
- Pricing analysis
- Strengths and weaknesses
- Market positioning

### Technical Analysis
- Best practices compilation
- Implementation guidelines
- Tool and technology comparisons
- Code examples and documentation
- Architecture recommendations

## Quality Standards

The research skill maintains high quality through:

1. **Source Diversity**: Multiple, independent sources for validation
2. **Credibility Assessment**: Evaluation of source authority and expertise
3. **Fact Verification**: Cross-referencing claims across sources
4. **Bias Recognition**: Identification and mitigation of potential bias
5. **Currency Validation**: Prioritization of recent and relevant information
6. **Comprehensive Coverage**: Balance of breadth and depth in research

## Dependencies

### Required MCP Servers
- **playwright**: For advanced web automation and content extraction

### Required Python Libraries (in Docker container)
- **requests**: HTTP requests and API calls
- **beautifulsoup4**: HTML parsing and content extraction
- **pandas**: Data processing and analysis
- **matplotlib**: Data visualization
- **selenium**: Additional web automation if needed

## Configuration

The research skill can be customized through:

1. **Search Engine Preferences**: Configure which search engines to use
2. **Source Prioritization**: Weight academic vs. commercial vs. news sources
3. **Content Depth**: Adjust between broad overview vs. deep analysis
4. **Output Format**: Specify preferred report structure and length
5. **Quality Thresholds**: Set minimum standards for source credibility

## Troubleshooting

### Common Issues

1. **Rate Limiting**: Some websites may limit automated requests
   - **Solution**: The skill includes built-in delays and retry logic

2. **Access Restrictions**: Some sites may block automated access
   - **Solution**: Uses multiple approaches and fallback strategies

3. **Content Extraction Failures**: Complex sites may not extract properly
   - **Solution**: Falls back to alternative extraction methods

4. **Source Quality Concerns**: Questionable sources in search results
   - **Solution**: Built-in quality assessment and filtering

### Performance Tips

1. **Specific Queries**: More specific research requests yield better results
2. **Source Guidance**: Suggest preferred sources if you have them
3. **Scope Definition**: Clearly define research boundaries and limitations
4. **Time Constraints**: Specify urgency to balance thoroughness vs. speed

## Best Practices

1. **Clear Objectives**: Start with specific research questions
2. **Scope Management**: Define what's included and excluded
3. **Source Validation**: Always verify critical information
4. **Iterative Refinement**: Use initial findings to guide deeper research
5. **Documentation**: Keep track of methodology and limitations

## Security and Ethics

The research skill follows responsible research practices:

- Respects robots.txt and site policies
- Includes appropriate delays to avoid overwhelming servers
- Does not attempt to bypass paywalls or access restrictions
- Properly attributes all sources and information
- Maintains user privacy during research activities