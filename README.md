# Playlab Python Client

A Python client for interacting with the Playlab API, enabling you to create interactive AI tutoring experiences.

## Requirements

- Python 3.7 or later

## Installation

```bash
pip install playlab-api
```

### Getting an API Key

To use the Playlab API, you'll need to obtain an API key. 

1. Log in to your account: Once your account is set up, log in at https://playlab.ai/login.
2. Create and publish an app:
    - Navigate to a workspace within your organization or create a new one.
    - Create a new app within a workspace.
    - Develop your app using Playlab's tools.
    - Once ready, publish your app to your desired visibility.
    - Note down the project ID (also known as the app ID) - you'll need this for API calls.
      - The project ID can be found in the URL when you are on the project page as the group of characters after the last `/` .
      - For example, for: `https://www.playlab.ai/build/clzni6ang00112by7c4vwbabc` the project ID is: `clzni6ang00112by7c4vwbabc`
3. Create an API Keys: In your organization's menu bar, look for the "API Keys" link in the upper-right side of the page.

## Quick Start

```python
from playlab_api import PlaylabApp

# Initialize the app with your API key and project ID
app = PlaylabApp(
    api_key="your_api_key_here",
    project_id="your_project_id_here"
)

# Send a message and get the response
response = app.send_message("Hello, AI!")
```

## Environment Variables

You can set your API key and project ID using environment variables:

```bash
export PLAYLAB_API_KEY="your_api_key_here"
export PLAYLAB_PROJECT_ID="your_project_id_here"
```

Then initialize the app without parameters:

```python
app = PlaylabApp()
```

## Detailed Usage

Please refer to the [usage.ipynb](./usage.ipynb) notebook for more detailed examples, including:
- File attachments
- Conversation management
- History access
- System prompts
- Interactive chat