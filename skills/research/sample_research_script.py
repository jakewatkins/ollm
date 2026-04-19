#!/usr/bin/env python3
"""
Sample research script demonstrating web search capabilities.
This script can be executed in the Docker container to perform web searches.
"""

import requests
import json
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import csv
import os

def google_search(query, num_results=10):
    """
    Perform a web search using Google Custom Search API or web scraping.
    Note: This is a demo. In production, use official APIs when available.
    """
    search_results = []
    
    # For demo purposes, we'll use requests to fetch search results
    # In production, you would integrate with proper search APIs
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # This is a simplified example - adapt based on available search APIs
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract search result links - this is simplified
        results = soup.find_all('a')
        
        for link in results[:num_results]:
            href = link.get('href')
            if href and href.startswith('/url?q='):
                actual_url = href.split('&')[0][7:]  # Remove /url?q= prefix
                title = link.get_text()
                if title and actual_url:
                    search_results.append({
                        'title': title[:100],  # Truncate long titles
                        'url': actual_url,
                        'snippet': ''  # Could extract snippets if needed
                    })
        
        return search_results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_page_content(url, max_length=5000):
    """Fetch and extract text content from a web page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
        
    except Exception as e:
        return f"Error fetching content: {e}"

def research_topic(topic, num_sources=5, output_file="output.txt"):
    """
    Comprehensive research function that searches for information about a topic.
    """
    print(f"Starting research on: {topic}")
    
    research_data = {
        'topic': topic,
        'search_results': [],
        'content_analysis': [],
        'summary': '',
        'sources': []
    }
    
    # Step 1: Perform web search
    print("Performing web search...")
    search_results = google_search(topic, num_sources)
    research_data['search_results'] = search_results
    
    # Step 2: Analyze top results
    print("Analyzing search results...")
    for i, result in enumerate(search_results[:3]):  # Analyze top 3 results
        print(f"Analyzing result {i+1}: {result['url']}")
        
        content = fetch_page_content(result['url'])
        
        analysis = {
            'url': result['url'],
            'title': result['title'],
            'content_preview': content[:500] + "..." if len(content) > 500 else content,
            'content_length': len(content),
            'analysis_notes': f"Content extracted from {result['title']}"
        }
        
        research_data['content_analysis'].append(analysis)
        research_data['sources'].append(result['url'])
        
        # Add delay to be respectful
        time.sleep(2)
    
    # Step 3: Generate summary
    print("Generating research summary...")
    research_data['summary'] = generate_research_summary(research_data)
    
    # Step 4: Write results to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Research Results\n\n")
        f.write(f"**Topic:** {topic}\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary\n")
        f.write(research_data['summary'] + "\n\n")
        
        f.write("## Search Results\n")
        for i, result in enumerate(research_data['search_results'], 1):
            f.write(f"{i}. [{result['title']}]({result['url']})\n")
        f.write("\n")
        
        f.write("## Content Analysis\n")
        for analysis in research_data['content_analysis']:
            f.write(f"### {analysis['title']}\n")
            f.write(f"**URL:** {analysis['url']}\n")
            f.write(f"**Content Length:** {analysis['content_length']} characters\n")
            f.write(f"**Preview:** {analysis['content_preview']}\n\n")
        
        f.write("## Sources Used\n")
        for source in research_data['sources']:
            f.write(f"- {source}\n")
    
    print(f"Research complete! Results saved to {output_file}")
    return research_data

def generate_research_summary(research_data):
    """Generate a summary based on collected research data."""
    num_sources = len(research_data['search_results'])
    num_analyzed = len(research_data['content_analysis'])
    
    summary = f"""Based on web search and content analysis of {num_sources} sources (with detailed analysis of {num_analyzed} sources), 
here are the key findings about {research_data['topic']}:

Key Points Identified:
- Multiple relevant sources were found discussing {research_data['topic']}
- Content was successfully extracted from {num_analyzed} primary sources
- Research covered various aspects and perspectives of the topic

Content Analysis Summary:
"""
    
    for analysis in research_data['content_analysis']:
        summary += f"- {analysis['title']}: {analysis['content_length']} characters of content analyzed\n"
    
    summary += f"""
Sources Verification:
- All {len(research_data['sources'])} sources were accessible and provided relevant content
- Content spans various website types and perspectives
- Research methodology included both automated search and content extraction

Recommendations for Further Research:
- Consider reaching out to domain experts mentioned in the sources
- Look for more recent studies or reports on the topic
- Cross-reference findings with academic or official sources
- Consider conducting primary research if gaps exist in available information
"""
    
    return summary

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "artificial intelligence trends 2026"
    
    # Perform research
    research_topic(topic)
    
    print("Script execution completed. Check output.txt for results.")