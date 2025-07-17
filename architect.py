#!/usr/bin/env python3
"""
Architect CLI Tool - Generate technical design documents using Anthropic API
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List
import re
import anthropic


def main():
    """Main entry point for the architect CLI tool"""
    parser = argparse.ArgumentParser(
        description="Generate technical design documents using Anthropic API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  architect -f "user authentication-dashboard design"
  architect -f features.md -c context.md
  architect -f features.md -c context.md -e existing1.md existing2.md
  architect -f "user auth" -k "sk-..."
        """
    )
    
    parser.add_argument(
        "-f", "--features",
        required=True,
        help="Feature descriptions (string or path to .md file)"
    )
    
    parser.add_argument(
        "-c", "--context",
        help="Technical context (multiline string or path to .md file)"
    )
    
    parser.add_argument(
        "-e", "--existing",
        nargs="+",
        help="Existing markdown files to include (multiple file paths)"
    )
    
    parser.add_argument(
        "-k", "--api-key",
        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    try:
        # Resolve API key
        api_key = resolve_api_key(args.api_key)
        
        # Process inputs
        features = process_input(args.features, "features")
        context = process_input(args.context, "context") if args.context else ""
        existing_content = process_existing_files(args.existing) if args.existing else ""
        
        # Generate slug
        print("Generating system slug...")
        slug = generate_slug(api_key, features)
        print(f"Generated slug: {slug}")
        
        # Generate technical design
        print("Generating technical design document...")
        response = generate_technical_design(api_key, features, context, existing_content)
        
        # Parse and save outputs
        parse_and_save_outputs(response, slug, args.existing)
        
        print(f"✅ Generated files in specs/ directory:")
        print(f"  - specs/{slug}_architecture_planning.md")
        print(f"  - specs/{slug}_technical_design.md")
        
        if args.existing:
            for existing_file in args.existing:
                filename = Path(existing_file).name
                print(f"  - specs/updated_{filename}")
                
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_api_key(cli_key: Optional[str]) -> str:
    """Resolve API key from CLI option or environment variable"""
    if cli_key:
        return cli_key
    
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    
    raise ValueError(
        "No API key provided. Use --api-key option or set ANTHROPIC_API_KEY environment variable"
    )


def process_input(input_value: str, input_type: str) -> str:
    """Process input value - either direct string or file path"""
    if input_value.endswith('.md') and Path(input_value).exists():
        try:
            return Path(input_value).read_text(encoding='utf-8')
        except Exception as e:
            raise ValueError(f"Error reading {input_type} file '{input_value}': {e}")
    else:
        return input_value


def process_existing_files(existing_files: List[str]) -> str:
    """Process existing markdown files and combine their content"""
    if not existing_files:
        return ""
    
    combined_content = []
    for file_path in existing_files:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Existing file not found: {file_path}")
        
        if not file_path.endswith('.md'):
            raise ValueError(f"Existing file must be a .md file: {file_path}")
        
        try:
            content = path.read_text(encoding='utf-8')
            combined_content.append(f"File: {file_path}\n{content}")
        except Exception as e:
            raise ValueError(f"Error reading existing file '{file_path}': {e}")
    
    return "\n\n".join(combined_content)


def generate_slug(api_key: str, features: str) -> str:
    """Generate a slug using Anthropic API"""
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        message = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=50,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a 1-3 word slug (underscore_separated) for this system: {features[:500]} \n Remember to only return the slug without any additional text."
                }
            ]
        )
        
        slug = message.content[0].text.strip()
        # Clean up slug to ensure it's valid for filenames
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug.lower()
        
    except Exception as e:
        raise ValueError(f"Error generating slug: {e}")


def generate_technical_design(api_key: str, features: str, context: str, existing_content: str) -> str:
    """Generate technical design document using Anthropic API"""
    client = anthropic.Anthropic(api_key=api_key)
    
    system_prompt = """You are a Sr. Software Architect. Your role is to ensure a complete, thorough, simple and elegant design is captured before implementation begins."""
    
    user_prompt = f"""As a Sr. Software Architect, your task is to create a comprehensive technical design document for a software system. This document should describe the architecture, technical requirements, implementation considerations, and other relevant details for implementing the system.

Before we begin, here is the necessary information for your task:

1. Feature Descriptions:
<feature_descriptions>
{features}
</feature_descriptions>

2. Technical Context:
<technical_context>
{context}
</technical_context>

3. Existing Markdown (if available):
<existing_markdown>
{existing_content}
</existing_markdown>

Please follow these steps to create the technical design document:

1. Analyze the provided information:
   - Study the feature descriptions to understand core functionality, requirements, and goals.
   - Review the technical context for constraints, existing technologies, and integration points.
   - If existing markdown files are provided, determine necessary updates.

2. Evaluate each feature:
   - Consider its technical requirements and how the technical context applies to its design.
   - Assess how each sub-system might change to enable this feature or if additional systems are required.
   - If a requirement could be met by multiple sub-systems, choose the best fit while keeping implementation simple.

3. Identify critical missing details:
   - Focus on major architectural and project-level elements.
   - Ignore minor implementation details unless they significantly impact feasibility or success.

4. Address gaps with best practices:
   - For each critical missing detail, recommend solutions based on industry best practices.

5. Note assumptions:
   - Document any assumptions you make about the project or its requirements.

6. Create the technical design document with the following sections:
   a. Executive Summary
   b. System Architecture
   c. Technical Requirements
   d. Data Model
   e. API Design (if applicable)
   f. Security Considerations
   g. Scalability and Performance
   h. Integration Points
   i. Development and Deployment
   j. Monitoring and Logging
   k. Future Considerations

7. Writing guidelines:
   - Use clear, concise language suitable for a technical audience.
   - Include diagrams or flowcharts where appropriate.
   - Justify design decisions and explain trade-offs.
   - Address specific concerns from the feature descriptions or technical context.
   - Incorporate relevant information from existing markdown files, updating as necessary.
   - FULLY integrate the information from the <technical_context> into your document. DO NOT reference its source. For example, if a data structure or format is specified repeat it here. DO NOT say "as specified in..." or something similar. Do not assume the <technical_context> will be available to the consumer of this doc.

Before providing your final output, conduct your architecture planning inside <architecture_planning> tags within your thinking block. This should include:

1. Extracting key points from the feature descriptions and technical context.
2. Listing and prioritizing features based on their complexity and impact.
3. Creating a high-level system diagram.
4. Identifying major components of the system.
5. Listing potential challenges or areas requiring special attention.
6. Identifying potential risks and mitigation strategies.
7. For each major design decision:
   - List pros and cons
   - Justify your final choice
8. Outline any assumptions you're making about the project or requirements.

After completing your architecture planning, present your final document in the following format:

<technical_design_document>
# Executive Summary
[Brief overview]

# System Architecture
[High-level architecture description]

# Technical Requirements
[List and explanation of requirements]

# Data Model
[Description of data structures and relationships]

# API Design
[If applicable: API endpoints, request/response formats, authentication methods]

# Security Considerations
[Security measures and best practices]

# Scalability and Performance
[Strategies for growth and performance maintenance]

# Integration Points
[Description of system integrations]

# Development and Deployment
[Guidelines for development, testing, and deployment]

# Monitoring and Logging
[Monitoring and logging mechanisms]

# Future Considerations
[Potential areas for expansion or improvement]
</technical_design_document>

If you've updated any existing markdown content, include it here:

<updated_markdown>
[Updated markdown content, if applicable]
</updated_markdown>

Remember to focus on major architectural and project-level design decisions. Your final output should include the content within the <architecture_planning> thinking block, <technical_design_document> and <updated_markdown> tags."""
    
    try:
        # Use streaming for long-running requests
        print("🔄 Generating technical design (streaming)...")
        
        with client.messages.stream(
            model="claude-opus-4-20250514",
            max_tokens=20000,
            temperature=0.2,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        ) as stream:
            response_text = ""
            chunk_count = 0
            
            for text in stream.text_stream:
                response_text += text
                chunk_count += 1
                
                # Show progress every 100 chunks for less spam
                if chunk_count % 100 == 0:
                    print(f"📝 Processing... ({chunk_count} chunks received)")
                    sys.stdout.flush()  # Force output to appear immediately
        
        print(f"✅ Streaming complete ({chunk_count} chunks received)")
        
        # Log the entire response
        print(f"📝 Full LLM Response:")
        print("=" * 80)
        print(response_text)
        print("=" * 80)
        
        return response_text
        
    except Exception as e:
        if "stream" in str(e).lower():
            raise ValueError(f"Error in streaming response: {e}")
        else:
            raise ValueError(f"Error generating technical design: {e}")


def parse_and_save_outputs(response: str, slug: str, existing_files: Optional[List[str]]):
    """Parse API response and save outputs to files"""
    
    # Create specs directory if it doesn't exist
    specs_dir = Path("specs")
    specs_dir.mkdir(exist_ok=True)
    
    # Extract architecture planning
    planning_match = re.search(r'<architecture_planning>(.*?)</architecture_planning>', response, re.DOTALL)
    if planning_match:
        planning_content = planning_match.group(1).strip()
        (specs_dir / f"{slug}_architecture_planning.md").write_text(planning_content, encoding='utf-8')
    else:
        print("⚠️  Warning: No architecture planning section found in response")
    
    # Extract technical design document
    design_match = re.search(r'<technical_design_document>(.*?)</technical_design_document>', response, re.DOTALL)
    if design_match:
        design_content = design_match.group(1).strip()
        (specs_dir / f"{slug}_technical_design.md").write_text(design_content, encoding='utf-8')
    else:
        print("⚠️  Warning: No technical design document section found in response")
    
    # Extract updated markdown (if any)
    updated_match = re.search(r'<updated_markdown>(.*?)</updated_markdown>', response, re.DOTALL)
    if updated_match and existing_files:
        updated_content = updated_match.group(1).strip()
        
        # For simplicity, save all updated content to each existing file
        # In a more sophisticated implementation, you'd parse individual file updates
        for existing_file in existing_files:
            filename = Path(existing_file).name
            (specs_dir / f"updated_{filename}").write_text(updated_content, encoding='utf-8')


if __name__ == "__main__":
    main()