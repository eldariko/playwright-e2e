import argparse
import json
import os
import sys

from ollama import Client

# Path to the Playwright JSON report generated in Step 1
REPORT_PATH = "test-results/playwright-results.json"
# The Ollama model to use. You can change this to 'llama3' or 'qwen2.5-coder'
AI_MODEL = "llama3"
# Default Ollama URL (localhost)
DEFAULT_OLLAMA_URL = "http://localhost:11434"


def extract_failed_tests(suites):
    """
    Recursively search through the Playwright JSON suites to find failed tests.
    Returns a list of dictionaries containing test details and error messages.
    """
    failures = []
    for suite in suites:
        # Check for nested suites
        if 'suites' in suite:
            failures.extend(extract_failed_tests(suite['suites']))

        # Check for specs (individual tests)
        if 'specs' in suite:
            for spec in suite['specs']:
                test_name = spec.get('title', 'Unknown Test')
                file_name = spec.get('file', 'Unknown File')

                for test in spec.get('tests', []):
                    for result in test.get('results', []):
                        # Playwright marks failed tests as 'unexpected'
                        if result.get('status') in ['unexpected', 'failed']:
                            errors = result.get('errors', [])
                            error_messages = [err.get('message', '') for err in errors if 'message' in err]

                            failures.append({
                                "file": file_name,
                                "test_name": test_name,
                                "error": "\n".join(error_messages)
                            })
    return failures


def analyze_failures_with_ai(failures, ai_model, ollama_url):
    """
    Send the extracted failures to Ollama for Root Cause Analysis using a custom host.
    """
    # Create a system prompt based on the PRD requirements
    system_prompt = (
        "You are an expert QA Automation Engineer and AI. "
        "Analyze the following Playwright End-to-End test failures for a WooCommerce website. "
        "For each failure, provide a structured Root Cause Analysis (RCA) containing: "
        "1. Description: A readable summary of why the test failed. "
        "2. Classification: Categorize as 'System Bug', 'Environment/Network Issue', or 'Flaky Test'. "
        "3. Suggested Fix: Provide a code snippet or actionable advice to fix the issue. "
        "Format the output cleanly using Markdown."
    )

    # Convert the failures list to a formatted JSON string for the AI
    failures_text = json.dumps(failures, indent=2)
    user_prompt = f"Here are the failed tests:\n{failures_text}"

    print(f"Connecting to Ollama at {ollama_url}...")
    print(f"Sending {len(failures)} failed tests to {ai_model} for analysis...\n")

    try:
        # Initialize the Ollama client with the provided URL
        client = Client(host=ollama_url)

        # Call the Ollama model
        response = client.chat(model=ai_model, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ])

        # Print the AI response
        print("### AI Root Cause Analysis ###\n")
        print(response['message']['content'])

    except Exception as e:
        print(f"Failed to communicate with Ollama: {e}")
        print(f"Make sure Ollama is installed, running, and accessible at {ollama_url}")


def main():
    # Set up an argument parser to make the script standalone and configurable
    parser = argparse.ArgumentParser(description="Analyze Playwright test failures using AI.")
    parser.add_argument("-r", "--report", default=REPORT_PATH, help="Path to the Playwright JSON report")
    parser.add_argument("-m", "--model", default=AI_MODEL, help="Ollama model to use")
    parser.add_argument("-u", "--url", default=DEFAULT_OLLAMA_URL, help="URL of the Ollama instance")
    args = parser.parse_args()

    report_path = args.report
    ai_model = args.model
    ollama_url = args.url

    # Check if the report file exists
    if not os.path.exists(report_path):
        print(f"Error: Report file not found at {report_path}")
        print("Please provide the correct path using -r.")
        sys.exit(1)

    # Read the JSON report
    with open(report_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            print("Error: Failed to parse the JSON report.")
            sys.exit(1)

    # Start extracting failures
    suites = data.get('suites', [])
    failures = extract_failed_tests(suites)

    if not failures:
        print("Great news! All tests passed successfully. No RCA needed.")
        sys.exit(0)

    # Send to AI
    analyze_failures_with_ai(failures, ai_model, ollama_url)


if __name__ == "__main__":
    main()