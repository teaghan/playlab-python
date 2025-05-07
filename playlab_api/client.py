import os
import json
import requests
from IPython.display import Markdown, display
from IPython import get_ipython
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin, urlencode

class PlaylabError(Exception):
    """Base exception for all Playlab API errors."""
    pass

class PlaylabAuthenticationError(PlaylabError):
    """Raised when there are authentication issues."""
    pass

class PlaylabValidationError(PlaylabError):
    """Raised when there are validation issues with the request."""
    pass

class PlaylabAPIError(PlaylabError):
    """Raised for general API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)

# Jupyter notebook print function
def printmd(string: str) -> None:
    display(Markdown(string))

class PlaylabApp:
    """A client for interacting with the Playlab API."""
    
    BASE_URL = "https://www.playlab.ai/api/v1"
    
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None, verbose: bool = True):
        """
        Initialize the Playlab client and start a new conversation.
        
        Args:
            api_key: Your Playlab API key. If not provided, will look for PLAYLAB_API_KEY env var.
            project_id: Your Playlab project ID. If not provided, will look for PLAYLAB_PROJECT_ID env var.
            verbose: Whether to print responses to console
        """
        self.api_key = api_key or os.getenv("PLAYLAB_API_KEY")
        self.project_id = project_id or os.getenv("PLAYLAB_PROJECT_ID")
        self.verbose = verbose
        
        if not self.api_key:
            raise PlaylabAuthenticationError("API key must be provided either as an argument or through PLAYLAB_API_KEY environment variable")
        if not self.project_id:
            raise PlaylabValidationError("Project ID must be provided either as through PLAYLAB_PROJECT_ID environment variable")
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Check if user is in a Jupyter notebook
        self.is_notebook = False
        try:
            if get_ipython() is not None:
                self.is_notebook = True
        except NameError:
            pass
        
        # Start a new conversation on initialization
        self.conversation_id = self.create_conversation()["conversation"]["id"]
        
        # Get and display the initial messages
        messages = self.list_messages()
        if messages and self.verbose:
            # Display the AI's introduction (second message)
            if len(messages) >= 2 and messages[1]['source'] == 'provider':
                self._display_message(messages[1]['content'])
    
    def _display_message(self, content: str) -> None:
        """
        Display a message in the appropriate format based on the environment.
        
        Args:
            content: The message content to display
        """
        if self.is_notebook:
            printmd(content.replace("\\[", "$").replace("\\]", "$"))
        else:
            print(content)
    
    def _handle_api_error(self, response: requests.Response) -> None:
        """Handle API errors and raise appropriate exceptions."""
        try:
            error_data = response.json()
        except json.JSONDecodeError:
            error_data = {"error": response.text}

        status_code = response.status_code
        error_message = error_data.get("error", "Unknown error")

        if status_code == 401:
            raise PlaylabAuthenticationError(f"Authentication error: {error_message}")
        elif status_code == 400:
            raise PlaylabValidationError(f"Validation error: {error_message}")
        else:
            raise PlaylabAPIError(
                f"API error: {error_message}",
                status_code=status_code,
                response=error_data
            )

    def _make_request(self, method: str, endpoint: str, use_form: bool = False, **kwargs) -> requests.Response:
        """
        Make a request to the Playlab API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            use_form: Whether to use form-urlencoded instead of JSON
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
            
        Raises:
            PlaylabError: If there's an error with the API request
        """
        # Remove leading slash if present to avoid double slashes
        endpoint = endpoint.lstrip('/')
        url = f"{self.BASE_URL}/{endpoint}"
        
        if use_form:
            # Remove Content-Type from headers if it exists
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            
            # Convert JSON data to form data if present
            if 'json' in kwargs:
                data = kwargs.pop('json')
                kwargs['data'] = urlencode(data)
        else:
            headers = self.headers
            
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                self._handle_api_error(e.response)
            raise PlaylabAPIError(f"Request failed: {str(e)}")
    
    def create_conversation(self, instruction_variables: Optional[Dict[str, Union[str, int, float, bool]]] = None, 
                          use_form: bool = False) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            instruction_variables: Optional dictionary of instruction variables for the conversation.
                Values can be strings, numbers, or booleans.
            use_form: Whether to use form-urlencoded instead of JSON
            
        Returns:
            Dictionary containing the conversation details.
            
        Raises:
            PlaylabValidationError: If instruction variables are invalid
        """
        endpoint = f"/projects/{self.project_id}/conversations"
        data = {}
        
        if instruction_variables:
            # Validate instruction variables
            for key, value in instruction_variables.items():
                if not isinstance(value, (str, int, float, bool)):
                    raise PlaylabValidationError(
                        f"Invalid instruction variable value for '{key}': {value}. "
                        "Values must be strings, numbers, or booleans."
                    )
            data["instructionVariables"] = instruction_variables
            
        response = self._make_request("POST", endpoint, use_form=use_form, json=data)
        return response.json()
    
    def load_conversation(self, conversation_id: str) -> None:
        """
        Load an existing conversation by its ID and display its history.
        
        Args:
            conversation_id: The ID of the conversation to load.
            
        Raises:
            PlaylabValidationError: If conversation_id is invalid
            PlaylabAPIError: If there's an error loading the conversation
        """
        if not conversation_id:
            raise PlaylabValidationError("Invalid conversation ID")
            
        try:
            self.conversation_id = conversation_id
            if self.verbose:
                messages = self.list_messages()
                if messages:
                    # Display all messages starting from the second one (AI's introduction)
                    for message in messages[1:]:
                        if message['source'] == 'provider':
                            print("\nAI:", end=" ")
                        else:
                            print("\nYou:", end=" ")
                        self._display_message(message['content'])
                        print()
        except PlaylabAPIError as e:
            raise PlaylabAPIError(f"Failed to load conversation: {str(e)}")
    
    def send_message(self, message: str, file_path: Optional[str] = None,
                    use_form: bool = False, stream: bool = False) -> Dict[str, Any]:
        """
        Send a message in the current conversation.
        
        Args:
            message: The message to send.
            file_path: Optional path to a file to attach to the message.
            use_form: Whether to use form-urlencoded instead of JSON (ignored if file_path is provided)
            stream: Whether to stream the response (if False, will use simple display)
            
        Returns:
            Dictionary containing the message details.
            
        Raises:
            PlaylabValidationError: If no conversation is loaded or file_path is invalid
            PlaylabAPIError: If there's an error sending the message
        """
        if not self.conversation_id:
            raise PlaylabValidationError("No conversation loaded. Please create a new conversation or load an existing one.")
            
        if file_path and not os.path.exists(file_path):
            raise PlaylabValidationError(f"File not found: {file_path}")
            
        if self.verbose:
            print(f"\nYou: {message}")
            
        endpoint = f"/projects/{self.project_id}/conversations/{self.conversation_id}/messages"
        
        if file_path:
            # Handle file upload with multipart/form-data
            with open(file_path, 'rb') as f:
                # Get the file's MIME type
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                files = {
                    'file': (os.path.basename(file_path), f, mime_type)
                }
                
                data = {
                    'input.message': message,
                    'originalFileName': os.path.basename(file_path)
                }
                
                # Remove Content-Type from headers for multipart/form-data
                headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                
                try:
                    response = requests.post(
                        f"{self.BASE_URL}/{endpoint.lstrip('/')}",
                        headers=headers,
                        files=files,
                        data=data,
                        stream=True  # Always stream for file uploads since API requires it
                    )
                    response.raise_for_status()
                    
                    # Process the streamed response
                    full_content = ""
                    
                    if stream:
                        # Stream the response in real-time
                        if self.verbose:
                            print("\nAI: ", end="", flush=True)
                            
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith("data:"):
                                    try:
                                        data = json.loads(line[5:])
                                        if data.get("delta"):
                                            chunk = data["delta"]
                                            full_content += chunk
                                            if self.verbose:
                                                print(chunk, end="", flush=True)
                                    except json.JSONDecodeError:
                                        continue
                        
                        if self.verbose:
                            print("\n")
                    else:
                        # Collect the full response before displaying
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith("data:"):
                                    try:
                                        data = json.loads(line[5:])
                                        if data.get("delta"):
                                            full_content += data["delta"]
                                    except json.JSONDecodeError:
                                        continue
                        
                        if self.verbose:
                            print("\nAI:", end=" ")
                            self._display_message(full_content)
                            print()
                    
                    return {"content": full_content}
                except requests.exceptions.RequestException as e:
                    if isinstance(e, requests.exceptions.HTTPError):
                        self._handle_api_error(e.response)
                    raise PlaylabAPIError(f"Failed to send message with file: {str(e)}")
        else:
            # Handle text-only message
            data = {"input": {"message": message}}
            
            if stream:
                # Use streaming response
                headers = self.headers.copy()
                try:
                    response = requests.post(
                        f"{self.BASE_URL}/{endpoint.lstrip('/')}",
                        headers=headers,
                        json=data,
                        stream=True
                    )
                    response.raise_for_status()
                    
                    # Process the streamed response
                    full_content = ""
                    if self.verbose:
                        print("\nAI: ", end="", flush=True)
                        
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith("data:"):
                                try:
                                    data = json.loads(line[5:])
                                    if data.get("delta"):
                                        chunk = data["delta"]
                                        full_content += chunk
                                        if self.verbose:
                                            print(chunk, end="", flush=True)
                                except json.JSONDecodeError:
                                    continue
                    
                    if self.verbose:
                        print("\n")
                    
                    return {"content": full_content}
                except requests.exceptions.RequestException as e:
                    if isinstance(e, requests.exceptions.HTTPError):
                        self._handle_api_error(e.response)
                    raise PlaylabAPIError(f"Failed to send message: {str(e)}")
            else:
                # Use simple response with streaming (but collect all content before displaying)
                headers = self.headers.copy()
                try:
                    response = requests.post(
                        f"{self.BASE_URL}/{endpoint.lstrip('/')}",
                        headers=headers,
                        json=data,
                        stream=True
                    )
                    response.raise_for_status()
                    
                    # Collect the full response
                    full_content = ""
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith("data:"):
                                try:
                                    data = json.loads(line[5:])
                                    if data.get("delta"):
                                        full_content += data["delta"]
                                except json.JSONDecodeError:
                                    continue
                    
                    if self.verbose:
                        print("\nAI:", end=" ")
                        self._display_message(full_content)
                        print()
                    
                    return {"content": full_content}
                except requests.exceptions.RequestException as e:
                    if isinstance(e, requests.exceptions.HTTPError):
                        self._handle_api_error(e.response)
                    raise PlaylabAPIError(f"Failed to send message: {str(e)}")
    
    def list_messages(self) -> List[Dict[str, Any]]:
        """
        List all messages in the current conversation.
        
        Returns:
            List of message dictionaries.
        """
        if not self.conversation_id:
            raise ValueError("No conversation loaded. Please create a new conversation or load an existing one.")
            
        endpoint = f"/projects/{self.project_id}/conversations/{self.conversation_id}/messages"
        response = self._make_request("GET", endpoint)
        return response.json()["messages"]
    
    def stream_message(self, message: str, 
                      on_chunk: Optional[callable] = None,
                      use_form: bool = False) -> str:
        """
        Send a message and stream the response in the current conversation.
        This is a convenience method that calls send_message with stream=True.
        
        Args:
            message: The message to send.
            on_chunk: Optional callback function that will be called with each chunk of the response.
                The callback should accept a single string parameter containing the chunk.
            use_form: Whether to use form-urlencoded instead of JSON
            
        Returns:
            The complete response as a string.
            
        Raises:
            PlaylabValidationError: If no conversation is loaded
            PlaylabAPIError: If there's an error sending the message or processing the stream
            
        Example:
            >>> def print_chunk(chunk):
            ...     print(chunk, end="", flush=True)
            >>> response = client.stream_message("Hello!", on_chunk=print_chunk)
        """
        if not self.conversation_id:
            raise PlaylabValidationError("No conversation loaded. Please create a new conversation or load an existing one.")
            
        endpoint = f"/projects/{self.project_id}/conversations/{self.conversation_id}/messages"
        data = {"input": {"message": message}}
        
        if use_form:
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            data = urlencode(data)
        else:
            headers = self.headers
            
        try:
            response = requests.post(
                urljoin(self.BASE_URL, endpoint),
                headers=headers,
                json=data if not use_form else None,
                data=data if use_form else None,
                stream=True
            )
            response.raise_for_status()
            
            full_content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:])
                            if data.get("delta"):
                                chunk = data["delta"]
                                full_content += chunk
                                if on_chunk:
                                    on_chunk(chunk)
                        except json.JSONDecodeError:
                            continue
                            
            return full_content
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                self._handle_api_error(e.response)
            raise PlaylabAPIError(f"Failed to stream message: {str(e)}")

    def reset_chat(self) -> None:
        """
        Reset the conversation by creating a new one and displaying the AI's introduction.
        
        Raises:
            PlaylabAPIError: If there's an error creating the new conversation
        """
        try:
            # Create a new conversation
            self.conversation_id = self.create_conversation()["conversation"]["id"]
            
            # Get and display the initial messages
            messages = self.list_messages()
            if messages and self.verbose:
                # Display the AI's introduction (second message)
                if len(messages) >= 2 and messages[1]['source'] == 'provider':
                    self._display_message(messages[1]['content'])
                    print()  # Add a newline after the introduction
        except PlaylabAPIError as e:
            raise PlaylabAPIError(f"Failed to reset chat: {str(e)}")

    def display_system_prompt(self) -> None:
        """
        Display the system prompt (first message) from the current conversation.
        This is typically the AI's initial instructions or context.
        
        Raises:
            PlaylabValidationError: If no conversation is loaded
            PlaylabAPIError: If there's an error retrieving messages
        """
        if not self.conversation_id:
            raise PlaylabValidationError("No conversation loaded. Please create a new conversation or load an existing one.")
            
        try:
            messages = self.list_messages()
            if messages:
                # Display the first message (system prompt)
                if messages[0]['source'] == 'system-start':
                    self._display_message(messages[0]['content'].split("### System Rules")[0])
                    print()
        except PlaylabAPIError as e:
            raise PlaylabAPIError(f"Failed to display system prompt: {str(e)}")